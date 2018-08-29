"""CAOS module that implements the HW resource estimation

This module relies on CAOSFlaskModule that have the following dependencies:
- flask
- requests

You can easily install the dependencies via pip.

To start the CAOS module run the following command in the command prompt:
python module.py

To see the available command line options run:
python module.py --help

Once the module is started (say on localhost:5000), you can check that the
module is up and running by opening a browser and opening the page:
localhost:5000/info
"""

import sys
import os
import tarfile

import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)) +
                "/../libraries")
import CAOSFlaskModule

codeArchive_PATH = "codeArchive"
__supported_templates__ = ['sst', 'masterslave']

def runModule(jsonPayload, workDir, blobNames, outLogPath, outBlobDir):
    """Parameters
    -------------
    jsonPayload: dict
        contains the request data in json format
    workDir: string
        the directory in which all the additional files for the requests
        (blobs) are already stored for us
    blobNames: list
        the list of blob names uploaded as part of the request
    outLogPath: string
        a string that specifies the filename were we should output the logs
    outBlobDir: string
        a string that specifies the folder where we should store optional
        files that are part of the response
    """
    
    with open(outLogPath, "wt", buffering=1) as logFile:

        # check if the architectural template is supported by this module

        template_specs = jsonPayload["architecturalTemplate"]
        template_name = template_specs["id"]
        log("Checking template '" + template_name + "'\n", logFile)
        if template_specs["type"].lower() not in __supported_templates__:
          raise Exception("Template '" + template_name + \
              "' appears to be not supported by this implementation of the module\n")

        # --- untar code blob into workdir
        codeArchive = jsonPayload["codeArchive"]
        
        srcPath = os.path.join(workDir, codeArchive_PATH)
        log("\nCreate temporary code directory in " + srcPath + "\n", logFile)
        os.mkdir(srcPath)
        srcTar = tarfile.open(os.path.join(workDir, codeArchive))

        # inspect members
        invalid_member = False
        for member in srcTar.getmembers():
            if os.path.isabs(member.name) or member.name.startswith('..'):
                invalid_member = True
                log(member.name + " is absolute or upper path (..), which is not allowed\n", logFile)
        if invalid_member:
            log("source archive is invalid, exiting...\n", logFile)
            return json_response

        log("Extracting sources to " + srcPath + "\n", logFile)
        srcTar.extractall(path=srcPath)
        srcTar.close()

        #implement your custom module HERE
        

        return responseData

#---------------------------------------------------------------------------------------------------------------------

def log(text, logFile):
    # print needed only for debugging purposes
    print(text)
    sys.stdout.flush()

    # write text on the log file that is visible to the CAOS gui
    logFile.write(text + "\n")


# Take a look at CAOSFlaskModule for more info on the parameters
CAOSFlaskModule.start(
    runCallback=runModule,
    apiVersion="1.0",
    moduleName="hw-estimation",
    implementationName="fpl",
    threaded=True,
    defaultPort=5022,
    maxTasks=2
)
