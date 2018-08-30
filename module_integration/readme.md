# CAOS Module Integration

In this folder it is possible to find information and examples on how to integrate a custom module within the CAOS Framework.
Folder **m\_2.2\_hw\_resource\_estimation** provides an example on how to modify the module that is specialized in estimating the resources of the functions that CAOS identifies as candidates for hardware acceleration.

## Module Integration Flow
A CAOS module simply needs to listen to a specific port and support the CAOS http requests sent from the CAOS flow manager.

Nevertheless, in order to simplify the development of CAOS modules and minimize the development time, we provide a CAOS module wrapper named *CAOSFlaskModule* that is written in Python and leverages [Flask](http://flask.pocoo.org/) to process http requests.

Using CAOSFlaskModule is the recommended solution to create a new CAOS module. Notice that, this does not imply that the module's core logic has to be written in Python, indeed the CAOSFlaskModule can be used to wrap a system call to any process that can be implemented in the desired programming language. CAOSFlaskModule handles all the http requests to and from the CAOS flow manager, the user is only responsible for implementing the *runModule* callback function that receives all the needed input files and JSON metadata and has to produce the output JSON response and, optionally, a set of output files.

Here is the basic flow to implement a custom module and integrate it into the CAOS Framework using the CAOSFlaskModule. This document focuses on creating a custom version of module 2.2 which is in charge of performing hardware resource estimation.

### 0. Dependencies

The CAOSFlaskModule requires either **Python2 (version 2.7.9 or higher)** or **Python3 (version 3.4 or higher)**.
Once Python is properly setup in your system, you also need to install the *Flask* python module and the *requests* python module (the latter is only required for local testing). For Python2, run:

```
python -m ensurepip
pip install Flask requests
```

if you are using Python3, run:

```
python3 -m ensurepip
pip3 install Flask requests
```


### 1. Module inputs and outputs
The input and output data exchanged by a generic CAOS module can be represented as follows:
![Input Output](https://raw.githubusercontent.com/necst/CAOS_examples/master/module_integration/imgs/CAOS_modules_custom_sketch.jpg)

The module receives as input a JSON file containing data at different levels regarding the application that is being analyzed, and the source code of the application. As an example, we can analyze an instance of a JSON input file for module 2.2, regarding hardware resource estimation.

```json
{
    "architecture": {
        "nodeDefinition": {
            "connectionTypes": {
                "pcie_gen3": {
                    "standard": "PCIe",
                    "duplex": "full",
                    "version": "3.0",
                    "bandwidth": "15.75 GB/s"
                }
            },
            "devices": {
                "cpu": {
                    "host": true,
                    "type": "intel-vcore"
                },
                "f1-fpga-instance": {
                    "type": "f1-fpga"
                }
            },
            "deviceTypes": {
                "f1-fpga": {
                    "vendor": "Xilinx",
                    "partNumber": "XCVU9P-FLGB2104-2-I",
                    "type": "board"
                },
                "intel-vcore": {
                    "vendor": "intel",
                    "partNumber": "-",
                    "type": "cpu"
                }
            },
            "connections": [
                {
                    "source": "f1-fpga_instance",
                    "target": "cpu",
                    "type": "pcie_gen3"
                }
            ]
        },
        "system": {
            "connections": [],
            "connectionTypes": [],
            "nodes": [
                "f1-fpga_node"
            ]
        }
    },


    "language": "c++",
    "supportedCompilers": [
        {
            "compiler": "g++",
            "arguments": ""
        },
        {
            "compiler": "llvm",
            "arguments": ""
        }
    ],
    "codeArchive": "code.tar.gz",


    "functions": {
        "vector_add(int*, int*, int*)": {
            "clangFilename": "1.ll",
            "returnType": "void",
            "name": "vector_add",
            "parameters": [
                {
                    "name": "c[81920]",
                    "type": "int"
                },
                {
                    "name": "a[81920]",
                    "type": "int"
                },
                {
                    "name": "b[81920]",
                    "type": "int"
                }
            ],
            "clangName": "_Z10vector_addPiS_S_",
            "startLine": 84,
            "endLine": 90,
            "language": "c++",
            "filePath": "code/vector_add.cpp"
        },
        "main": {
            "clangFilename": "1.ll",
            "returnType": "int",
            "name": "main",
            "parameters": [
                {
                    "name": "argc",
                    "type": "int"
                },
                {
                    "name": "argv[]",
                    "type": "char *"
                }
            ],
            "clangName": "main",
            "startLine": 51,
            "endLine": 82,
            "language": "c++",
            "filePath": "code/vector_add.cpp"
        }
    },
    "callgraph": {
        "vector_add(int*, int*, int*)": [],
        "main": [
            "malloc",
            "printf",
            "vector_add(int*, int*, int*)"
        ]
    },


    "architecturalTemplate": {
        "targetConfiguration": {
            "devices": [
                "f1-fpga-instance"
            ]
        },
        "supportedDevices": [
            "f1-fpga-instance"
        ],
        "id": "MasterSalve",
        "functions": {
            "vector_add(int*, int*, int*)": {
                "hardwareAcceleration": true
            },
            "main": {
                "hardwareAcceleration": false
            }
        },
        "type": "MasterSlave"
    }
}
```

The input JSON file provides multiple information regarding the definition of the target architecture, as well as information on the functions present into the source code.

As the resource hardware estimation step's task is to estimate how much resources are taken by each hardware function, a very interesting part of the file is represented by this part:

```json
{
    ...

    "architecturalTemplate": {
        "targetConfiguration": {
            "devices": [
                "f1-fpga-instance"
            ]
        },
        "supportedDevices": [
            "f1-fpga-instance"
        ],
        "id": "MasterSalve",
        "functions": {
            "vector_add(int*, int*, int*)": {
                "hardwareAcceleration": true
            },
            "main": {
                "hardwareAcceleration": false
            }
        },
        "type": "MasterSlave"
    }
}

```

In the **architecturalTemplate** section in fact, we can find multiple information regarding the device supported and all the functions that have been previously identified by CAOS to be candidate for hardware acceleration. 
Thanks to these information, our module can easily focus on estimating hardware resources for just the functions with the field **"hardwareAcceleration"** set to true, and thanks to the information available in the previous part of the file we can easily understand where these functions are implemented in the source file, as well as the location of the files.

The output of the custom module has to be compliant with the CAOS interface. An example of a valid output JSON file for module 2.2 is the following:

```json
{
    "vector_add(int*, int*, int*)" : {
        "resourceEstimation" : {
            "f1-fpga" : {
                "DSP48E":10,
                "BRAM_18K":34,
                "LUT":90,
                "FF":7,
                "URAM":0
            }
        }
    }
}

```

In this output file, it can be noticed that for each function identified as candidate for hardware acceleration, and for each deviceType indicated in the input JSON file, we need to provide CAOS the estimated resource utilization for each resource type.

### 2. Implement your own resource estimation CAOS module

Every CAOS module based on the CAOSFlaskModule, is implemented starting from the following template:

```python
import sys
from os import path

sys.path.append(path.join(path.dirname(path.abspath(__file__)), '..', '..', 'libraries'))
import CAOSFlaskModule

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
    
    # Implement module here and populate response data properly
    responseData = {}
        
    return responseData

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
```

The file begins with the inclusion of basic python modules as well as CAOSFlaskModule. The core of the module is specified within the **runModule** function which returns a python dictionary that will be automatically translated by the CAOSFlaskModule into the CAOS JSON response. The module can optionally store files within the **outBlobDir** that will be sent to CAOS together with the JSON response.

The last part of the template, consists in the CAOS module configuration and module's execution. The **CAOSFlaskModule.start** function is in charge of running the http interface and allows to specify a number of options, such as: the callback function (**runModule**) to execute upon a CAOS request, the name of the module being implemented together with its specific implementation name, whether parallel tasks can be run in separate threads (threaded), the default port at which the http server will listen to and the maximum number of tasks that can be processed in parallel. 

In order to create your own hardware estimation module, please consider starting from: **m\_2.2\_hw\_resource\_estimation/demo_fpl/module.py**. This template, already perform several initial checks, such as validating that the architectural template is supported by the module and unzipping the code archive  into the working folder.

The module can be started simply running the command:

```python
python module.py
```

or, if using Python3:

```python
python3 module.py
```

Once the module is started, it is ready to receive http requests at the port 5022.

To validate this, simply open a web browser and access the URL: [http://localhost:5022/info](http://localhost:5022/info)

You should see an output similar to the following:

```
{
    "apiVersion": "1.0",
    "implementationName": "fpl",
    "maxTasks": 2,
    "moduleName": "hw-estimation",
    "runningTasks": 0
}
```

The template module implements a dummy function **computeResourceEstimation** which you can replace with your own logic, leveraging the input data provided by CAOS.

### 3. Test your module locally

In order to test your logic, the module needs to receive http requests from CAOS that trigger the execution of the **runModule** method.

Since you might not have CAOS available, in order to simplify testing, we provide the **CAOSModuleTester** module which can be used to send dummy request to a CAOS module locally.

The Python script **m\_2.2\_hw\_resource\_estimation/demo_fpl/test\_module.py** provides an example of how to test your module. It sends the caos\_request.json as JSON input data and the code.tar.gz code archive (from **m\_2.2\_hw\_resource\_estimation/demo_fpl/test\_resources/**) to the module.

In order to run the test\_module.py script, make sure that your CAOS module is not running (the module will be automatically started by the testing script), and then run:

```python
python test_module.py
```

or, if using Python3:

```python
python3 test_module.py
```

you should see on the console, the log messages sent by the module as well as the validation message:

```bash
OUTPUT VALIDATION PASSED!
```

In case the response is malformed, or if an exception is thrown by your module, it will be reported to the console while executing the test\_module.py script.

Notice that, once the module start to process requests, a temporary output folder named **data** will contain all the working directories and files of the running and completed tasks. The content of this folder is also useful for debugging purposes.

### 4. Run your module on a public server

To allow CAOS to use access your custom module, it is necessary to deploy it on a public server and retrieve the **IP Address** and the ***port number***.
To deploy the application on your own server it is just necessary to execute:

```python
python module.py
```

To validate that your server is running and it can be publicly access. Open a web browser and access the link: **http://[IP ADDRESS]:[PORT NUMBER]/info**

### 5. Test your module within CAOS

Once the code has been deployed on a public server, the last step that is necessary to perform is to specify the Hostname and the port number of the public server inside CAOS at [http://app.caos.necst.it](http://app.caos.necst.it) and click update to check whether the connection works properly.

![CAOS IP specification](https://raw.githubusercontent.com/necst/CAOS_examples/master/module_integration/imgs/CAOS_ip.png)

Notice that the hostname and port information must be specified within the tab related to the HARDWARE ESTIMATION module, otherwise an error will be returned.

If everything has been setup correctly, CAOS will display that the status of the module is online, and it will be possible to send data to the custom module from the CAOS UI.