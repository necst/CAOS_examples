"""Defines a basic http endpoint of a CAOS module via flask

modules based on this interface should initialize and start the http server 
using the "start" method. This module has a dependency on: 
- flask

The module leverages a local file system storage and each compute task
can be in a RUNNING or COMPLETED state. (we use the atomic file system 
move to change the task state).

TODO: we still need a background thread in order to remove old files
from completed tasks.
"""

import flask
import optparse
import json
import os
import uuid
import shutil
import multiprocessing
import threading
import traceback
import signal

from flask import request
from os import path

class Error(Exception):
    """Exception that can be thrown by the runCallback

    Attributes
    ----------
    message : string
        The message of the error
    errorData : dict
        Extra information about the error
    """
    def __init__(self, message, errorData):
        super(Error, self).__init__(message)
        self.errorData = errorData

class KillTask(Exception):
    """Exception that can be thrown inside a task thread to stop it

    """
    pass

def start(runCallback, apiVersion, moduleName, implementationName, \
    storagePath="./data", threaded=False, maxTasks=0, defaultHost="0.0.0.0", \
    defaultPort=5000):
    """Starts the http server and listen for requests from the CAOS framework.

    This method also parses parameters passed via the command line when 
    launching the python script. The supported command line parameters are:
    -H (--host): the hostname for the http server
    -P (--port): the post for the http server
    -D (--debug): if debugging should be enabled

    Parameters
    ----------
    runCallback : def runCallback(jsonPayload, workDir, blobNames, outLogPath, outBlobDir) -> jsonPayload
        A callback function called when a request to the module is made. 
        The function arguments have the following semantics:
        - jsonPayload: a dictionary containing the request data
        - workDir: the directory in which all the additional files for the 
            request (blobs) have been stored
        - blobNames: the list of blob names uploaded as part of the request
        - outLogPath: a string that specifies the filename were we should 
            output the logs
        - oubBlobDir: a string that specifies the folder where we should store
            optional files that are part of the response
        The method should return the jsonPayload formatted as a dictionary.
        In case of error the function may throw an Exception or a ModuleError
        exception with extra error data.
    apiVersion : string
        API version supported by the module
    moduleName : string
        Name of the module
    implementationName : string
        The name of the specific implementation of this module
    storagePath : string
        The path to the local storage for the module
    threaded : bool
        Whether http requests should be handled in separated threads. If true 
        the server can handle multiple http requests concurrently. 
        (default False)
    maxTasks : int
        Maximum number of concurrent tasks that the module can handle, note 
        that each task is executed within its own thread or process.
        (default 0: no limits)
    defaultHost : string, optional (default is 0.0.0.0)
        The default host to use if not specified in the command line argument
    defaultPort : int
        The default port to use if not specified in the command line argument
    """

    # get absolute path
    storagePath = path.abspath(storagePath)
    # Set up the command-line options
    parser = optparse.OptionParser()
    parser.add_option("-H", "--host", help="Hostname of the module [default %s]" % defaultHost, default=defaultHost)
    parser.add_option("-P", "--port", help="Port for the module [default %s]" % defaultPort, default=defaultPort)
    parser.add_option("-D", "--debug", dest="debug", help="Enable debugging with -D=true")
    options, _ = parser.parse_args()

    app = flask.Flask(moduleName + ': ' + implementationName)

    app.config['runCallback'] = runCallback
    app.config['apiVersion'] = apiVersion
    app.config['moduleName'] = moduleName
    app.config['storagePath'] = storagePath
    app.config['implementationName'] = implementationName
    app.config['maxTasks'] = maxTasks

    capacityLock = threading.Lock()
    processesMapLock = threading.Lock()
    processesMap = {}


    _initLocalStorage(storagePath, app)

    # ---- http APIs ----

    @app.route('/info', methods=['GET'])
    def getInfo():
        return flask.jsonify(
            {
                'apiVersion' : app.config['apiVersion'],
                'moduleName' : app.config['moduleName'],
                'implementationName' : app.config['implementationName'],
                'runningTasks' : _getNumRunningTasks(app.config["RUNNING_DIR"]),
                'maxTasks' : app.config['maxTasks']
            }
        )

    @app.route('/submit', methods=['POST'])
    def postSubmit():

        # get list of files send by the client
        uploadedFiles = request.files

        # check and parse json_payload file
        if "jsonPayload" not in uploadedFiles:
            return _sendErrorData("'jsonPayload' file not found within the POST request", 400)
        try:
            data = uploadedFiles['jsonPayload'].read()
            jsonPayload = json.loads(data.decode("utf-8"))

        except Exception as e:
            return _sendErrorData("Unable to parse JSON from request field. Error: " + str(e), 400)

        # generate task id
        guid = _genNewGuid()
        taskDir = _getRunningTaskDir(guid, app)

        # check if we have enough capacity to handle the request
        if app.config['maxTasks'] > 0:
            try:
                capacityLock.acquire()
                running = _getNumRunningTasks(app.config["RUNNING_DIR"])
                if running >= app.config['maxTasks']:
                    return _sendErrorData("Capacity limit exceeded: " + str(running) + "/" + \
                        str(app.config['maxTasks']) + " running tasks, retry later.", 503)
                # create task folder (after this the task is considered to be running)
                os.mkdir(taskDir)
            finally:
                capacityLock.release()

        blobs = {name : uploadedFiles[name].stream for name in uploadedFiles if name != "jsonPayload" }

        # store task data
        try:
            resultFolder = path.join(taskDir, "result")
            os.mkdir(resultFolder)
            workDir = path.join(taskDir, "wd")
            os.mkdir(workDir)

            # store blobs
            for blobName in blobs:
                with open(path.join(workDir, blobName), "wb") as blobFile:
                    shutil.copyfileobj(blobs[blobName], blobFile)

            # store json payload for debugging purposes
            with open(path.join(taskDir, "requestJsonPayload"), "wt") as jsonPayloadFile:
                jsonPayloadFile.write(json.dumps(jsonPayload))

        except Exception as e:
            if path.is_dir(taskDir):
                _removePath(taskDir)
            return _sendErrorData("Failed to store request data. Error: " + str(e), 500)

        # run module
        # TODO: make this call async
        logPath = _getLogTaskPath(guid, app)
        with open(logPath, "wt") as logFile:
            pass

        # run the task in a new thread
        completedTaskDir = _getCompletedTaskDir(guid, app)
        process = multiprocessing.Process(target=_runWrapper, args=(jsonPayload, workDir, list(blobs.keys()), logPath, \
            resultFolder, taskDir, completedTaskDir, app.config["runCallback"], guid))

        processesMapLock.acquire()
        processesMap[guid] = process
        processesMapLock.release()

        process.start()

        # return ID for further reference
        return _sendJson({"taskId" : guid})

    @app.route('/state/<taskId>', methods=['GET'])
    def getState(taskId):
        
        runningTaskDir = _getRunningTaskDir(taskId, app)
        if path.isdir(runningTaskDir):
            return _sendJson({"state" : "RUNNING"})

        completedTaskDir = _getCompletedTaskDir(taskId, app)
        jsonResponsePath = path.join(completedTaskDir, "responseJsonPayload")
        if path.isfile(jsonResponsePath):

            # decode returned json payload
            with open(jsonResponsePath, "rt") as jsonResponseFile:
                jsonResponseRaw = jsonResponseFile.read()
            try:
                jsonResponse = json.loads(jsonResponseRaw)
            except Exception as e:
                return _sendJson(
                    {
                        "state" : "SERVER_ERROR",
                        "message" : "Failed to decode json response: " + str(e)
                    }
                )

            # check for error file
            errorFilePath = path.join(completedTaskDir, "error")
            if path.isfile(errorFilePath):
                with open(errorFilePath, "rt") as errorFile:
                    stackTrace = errorFile.read()
                jsonResponse["state"] = "FAILED"
                jsonResponse["stackTrace"] = stackTrace
                
                return _sendJson(jsonResponse)

            # get generated list of files
            resultDir = path.join(completedTaskDir, "result")
            blobs = os.listdir(resultDir)

            return _sendJson(
                {
                    "state" : "COMPLETED",
                    "blobs" : blobs,
                    "response" : jsonResponse
                }
            )

        return _sendErrorData("task with ID: '" + taskId + "' not found.", 404)

    @app.route('/kill/<taskId>', methods=['GET'])
    def killTask(taskId):
        
        process = None
        processesMapLock.acquire()
        if taskId in processesMap:
            process = processesMap[taskId]
        processesMapLock.release()

        if process == None:
            return _sendErrorData("task with ID: '" + taskId + "' not found or already completed", 404) 

        # kill the process
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except:
            return _sendErrorData("unable to find the process for ID: '" + taskId + "'", 404) 

        processesMapLock.acquire()
        if taskId in processesMap:
            del processesMap[taskId]
        processesMapLock.release()

        # wait for process to exit
        process.join()

        taskDir = _getRunningTaskDir(taskId, app)

        if path.isdir(taskDir):
            with open(path.join(taskDir, "error"), "wt") as errorFile:
                errorFile.write("Task cancelled by user")

            result = {}
            with open(path.join(taskDir, "responseJsonPayload"), "wt") as resultJsonFile:
                resultJsonFile.write(json.dumps(result))

            completedTaskDir = _getCompletedTaskDir(taskId, app)

            # move task to completed
            shutil.move(taskDir, completedTaskDir)

        return _sendJson({})

    @app.route('/log/<taskId>', methods=['GET'])
    def getLog(taskId):
        offset = request.args.get('offset')
        logPath = _getLogTaskPath(taskId, app)
        if not path.isfile(logPath):
            return _sendErrorData("logs for task with ID: '" + taskId + "' not found", 404)

        with open(logPath, "rb") as logFile:
            if(offset != None):
                logFile.seek(int(offset))
            data = logFile.read()

        return flask.make_response(data)

    @app.route('/result/<taskId>/<filename>', methods=['GET'])
    def getResult(taskId, filename):
        taskDir = _getCompletedTaskDir(taskId, app)
        if not path.isdir(taskDir):
            return _sendErrorData("task with ID: '" + taskId + "' not found or not completed.", 404)
        resultDir = path.join(taskDir, "result")
        filePath = path.join(resultDir, filename)
        if not path.isfile(filePath):
            return _sendErrorData("unable to find result file: '" + filename + "' for task with ID: '" + taskId + "'", 404)

        return flask.send_from_directory(resultDir, filename)

    # ---- END http APIs ----

    app.run(debug=options.debug, host=options.host, port=int(options.port), threaded=threaded)


# ---- private methods ----

def _sendJson(responseData, code=200):
    headers = {}
    headers["Content-Type"] = ["application/json; charset=utf-8"]
    response = flask.jsonify(responseData)
    response.headers = headers
    response.status_code = code
    return response

def _sendErrorData(message, code):
    responseData = { 'message' : message }
    return _sendJson(responseData, code)

def _runWrapper(jsonPayload, workDir, blobNames, outLogPath, outBlobDir, taskDir, completedTaskDir, callback, guid):
    success = True
    errorMsg = ""

    # set new session id for the process, this is useful when we need
    # to kill the task and all the childreen processes spawn by the task
    os.setsid()

    try:
        result = callback(jsonPayload, workDir, blobNames, outLogPath, outBlobDir)
    except Error as e:
        success = False
        errorMsg = traceback.format_exc()
        result = {'message' : str(e), 'errorData' : e.errorData}
    except Exception as e:
        success = False
        errorMsg = traceback.format_exc()
        result = {'message' : str(e)}
    
    if not success:
        with open(path.join(taskDir, "error"), "wt") as errorFile:
            errorFile.write(errorMsg)

    with open(path.join(taskDir, "responseJsonPayload"), "wt") as resultJsonFile:
        resultJsonFile.write(json.dumps(result))

    # move task to completed
    shutil.move(taskDir, completedTaskDir)

def _initLocalStorage(storagePath, app):
    # remove previous storage path
    if(path.isdir(storagePath)):
        _removePath(storagePath, True)

    # create storage
    os.mkdir(storagePath)

    logDir = path.join(storagePath, "logs")
    os.mkdir(logDir)
    app.config["LOG_DIR"] = logDir
    runningDir = path.join(storagePath, "running")
    os.mkdir(runningDir)
    app.config["RUNNING_DIR"] = runningDir
    completedDir = path.join(storagePath, "completed")
    os.mkdir(completedDir)
    app.config["COMPLETED_DIR"] = completedDir

def _getNumRunningTasks(runningDir):
    dirs = os.listdir(runningDir)
    tasksDirs = [d for d in dirs if d.startswith("t_")]
    return len(tasksDirs)

def _getRunningTaskDir(guid, app):
    return path.join(app.config["RUNNING_DIR"], guid)
            
def _getCompletedTaskDir(guid, app):
    return path.join(app.config["COMPLETED_DIR"], guid)

def _getLogTaskPath(guid, app):
    return path.join(app.config["LOG_DIR"], guid + ".txt")

def _genNewGuid():
    return "t_" + str(uuid.uuid4())

def _removePath(dirPath, log=False):
    if not path.isdir(dirPath):
        raise Exception(dirPath + " is not a directory")
    #childreen = os.listdir(dirPath)
    #for child in childreen:
    #    if(path.isdir(child)):
    #        _removePath(child)
    #    else:
    #        if log:
    #            print("removing file: " + child)
    #        os.unlink(child)
    #if log:
    #    print("removing dir: " + dirPath)
    #os.rmdir(dirPath)
    shutil.rmtree(dirPath, ignore_errors=True)
    if log:
        print("deleting " + dirPath)

