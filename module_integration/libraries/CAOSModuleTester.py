"""Simple tool to test submitting a task to a CAOS module

This module has a dependency on:
- requests

You can easily install the dependencies via pip.
"""

import os
import sys
import optparse
import requests
import json
import time
from os import path
import subprocess
import CAOSjsonTester


def test(jsonPayload, module_path=None, handle_implementation=True,
         work_dir=None, implementation_path=None, port=5000,
         hostname="localhost", files={}, resultFolder=None,
         test_callback=None, wait_s_start=1):
    """ Test a given module implementation to check if the output interface is
    of the requested form. Can perform additional testing via a user-defined
    callback function.
    Parameters:
    -----------
    'jsonPayload' is the input json
    'module_path' is the path of the given module, it is required to identify
        the default responseJson of such module (e.g. '*/m_1_1_ir_generation')
    'handle_implementation' is true if the life cycle of the implementation
        under test must be managed by this function (could be that the
        implementation is written in another language. In such case the life
        cycle must be managed explicitly in the test unit and cannot be handled
        by this function)
    'work_dir' defines where the implementation (if handled) will produce its
        output. Default is the location where pytest is invoked
    'implementation_path' is the path where the 'module.py' is located (it must
        include the python file in the path)
    'resultFolder' is the path where produced output files are stored
    'wait_s_start' is the number of seconds to wait for the implementation to
        start (if handled)
    'test_callback' is a function that has the following signature
        test_callback(jsonPayload, blobNames, blobDir)
        and is a function that can be specified to perform additional tests on
        the response of the implementation. Follow pytest conventions on how to
        write the logic inside the test_callback function.
        The function arguments have the following semantics:
        - jsonPayload: a dictionary containing the response json
        - blobNames: the list of blob names downloaded as of the response
        - blobDir: the path where the blobs have been downloaded
    """
    mod = None
    try:
        if handle_implementation:
            # launch module
            mod = _start_module(implementation_path, hostname, port, work_dir)
            # sleep to allow module to start
            time.sleep(wait_s_start)
        # submit task
        files["jsonPayload"] = json.dumps(jsonPayload)
        response = requests.post('http://' + hostname + ":" + str(port) +
                                 '/submit', files=files)
        if not response.status_code == 200:
            raise Exception("Failed to submit request.")

        jsonResponse = json.loads(response.text)
        taskId = jsonResponse["taskId"]

        # start polling on task state until running
        state = "RUNNING"
        while state == "RUNNING":
            # get state
            response = requests.get('http://' + hostname + ':' + str(port) +
                                    '/state/' + taskId)
            if not response.status_code == 200:
                raise Exception("Failed to get task state.")
            jsonResponse = json.loads(response.text)
            state = jsonResponse["state"]

            # sleep a while before next request
            time.sleep(1)

        if not state == "COMPLETED":
            stackTrace = ""
            if 'stackTrace' in jsonResponse:
                stackTrace = ". \nModule stackTrace:\n\n" + jsonResponse['stackTrace']

            raise Exception("Task not completed succesfully. State: " + state + stackTrace)

        # download resulting blobs if needed
        if resultFolder is not None:
            if not path.isdir(resultFolder):
                os.makedirs(resultFolder)
            blobs = jsonResponse["blobs"]
            for blob in blobs:
                response = response.get('http://' + hostname + ':' +
                                        str(port) + '/result/' + taskId + "/" +
                                        blob)
                if not response.status_code == 200:
                    raise Exception("failed to download blob: " + blob)
                blobPath = path.join(resultFolder, blob)
                with open(blobPath, "wb") as blobFile:
                    blobFile.write(response.content)
        if handle_implementation:
            # terminate module
            mod.terminate()
        blobs = jsonResponse["blobs"]
        json_response = jsonResponse['response']
        # check json
        jsonValidator_path = os.path.join(module_path, "test_resources/response.json")
        jsonValidator = {}
        with open(jsonValidator_path) as json_file:
            jsonValidator = json.load(json_file)
        assert CAOSjsonTester.validate_json(json_response, jsonValidator), \
            "Failed json response validation. Module output is:\n\n" + \
            json.dumps(json_response, sort_keys=True, indent=4) + \
            "\n\nExpected output format is:\n\n" + \
            json.dumps(jsonValidator, sort_keys=True, indent=4)

        # test_callback
        if test_callback:
            test_callback(json_response, blobs, resultFolder)

        print("\n\nTEST PASSED!\n")

    except:
        if handle_implementation and mod:
            # terminate module
            mod.terminate()
        raise


def send(jsonPayload, hostname="localhost", port=5000, files = {}, resultFolder=None):
    parser = optparse.OptionParser()
    parser.add_option("-H", "--host", help="Hostname of the module [default %s]" % hostname, default=hostname)
    parser.add_option("-P", "--port", help="Port for the test [default %s]" % port, default=port)
    options, _ = parser.parse_args()

    # check that the module is reachable
    response = _doGet('http://' + options.host + ':' + str(options.port) + '/info')
    if response.status_code != 200:
        print("ERROR: Unexpected status code: " + str(response.status_code))
        return

    # submit task
    files["jsonPayload"] = json.dumps(jsonPayload)
    response = _doPost('http://' + options.host + ":" + str(options.port) + '/submit', files=files)
    if response.status_code != 200:
        print("ERROR: Failed to submit request.")
        return

    jsonResponse = json.loads(response.text)
    taskId = jsonResponse["taskId"]

    # start polling on task state and logs
    state = "RUNNING"
    logsOffset = 0
    while state == "RUNNING":
        # get state
        response = _doGet('http://' + options.host + ':' + str(options.port) + '/state/' + taskId)
        if response.status_code != 200:
            print("ERROR: Failed to get task state.")
            return
        jsonResponse = json.loads(response.text)
        state = jsonResponse["state"]

        # get logs
        response = _doGet('http://' + options.host + ':' + str(options.port) + '/log/' + taskId + "?offset=" + str(logsOffset))
        if response.status_code != 200:
            print("ERROR: Failed to get task logs.")
            return
        logsOffset += int(response.headers["Content-Length"])

        # sleep a while before next request
        time.sleep(1)

    # download resulting blobs if needed
    if state == "COMPLETED" and resultFolder != None:
        print("# Downlading result blobs to: " + resultFolder)
        if not path.isdir(resultFolder):
            os.makedirs(resultFolder)

        blobs = jsonResponse["blobs"]
        
        for blob in blobs:
            response = _doGet('http://' + options.host + ':' + str(options.port) + '/result/' + taskId + "/" + blob, False)
            if response.status_code != 200:
                print("ERROR: failed to download blob: " + blob + " got response:")
                print(response.text)
            else:
                blobPath = path.join(resultFolder, blob)
                print("# INFO: Saving blob content to: " + blobPath)
                with open(blobPath, "wb") as blobFile:
                    blobFile.write(response.content)

def _doGet(url, printResponse = True):
    print("\n#### GET " + url)
    response = requests.get(url)
    print("status_code: " + str(response.status_code))
    if printResponse:
        print("response: ")
        print(response.text)

    return response

def _doPost(url, files={}, printResponse = True):
    print("\n#### POST " + url)
    response = requests.post(url, files=files)
    print("status_code: " + str(response.status_code))
    if printResponse:
        print("response: ")
        print(response.text)

    return response


def _start_module(implementation_path, hostname="localhost", port=5000,
                  work_dir=None):

    pythonCmd = "python"
    if sys.version_info[0] >= 3:
        pythonCmd = "python3"

    cmd = [pythonCmd, implementation_path, "-H", hostname, "-P", str(port)]
    return subprocess.Popen(cmd, cwd=work_dir)
