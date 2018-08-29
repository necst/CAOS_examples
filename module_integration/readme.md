# Module Integration

In this folder it is possible to find information and examples on how to integrate a custom module within the CAOS Framework.
Folder **m_2.2_hw_resource_estimation** provides an example on how to modify the module that is specialized in estimating the resources of the functions that CAOS identifes as candidates for hardware acceleration.

## Module Integration Flow
Here's the basic flow to implement a custom module and integrate it into the CAOS Framework.

### 0. Dependencies
The custom module has to be specified using Python.

### 1. Application Flow
The flow of the application can be represented as follows:
![Application Flow](https://raw.githubusercontent.com/necst/CAOS_examples/master/module_integration/imgs/CAOS_modules_custom_sketch.jpg)

The module receives a Json file containing data at different levels regardig the application that is being analyzed, and the source codes of the application. As an example, we can analyze the template json input file for the module 2.2, regarding hardware resource estimation.

```json
{
    "architecture" : {

        "nodeDefinition" : {                

            "deviceTypes" : {
                "fpga_xv7" : {
                    "type" : "fpga",
                    "vendor" : "Xilinx",
                    "partNumber" : "XC7VX415T-1FFG1157I-1"
                },
                "cpu_1" : {
                    "type" : "cpu",
                    "vendor" : "intel",
                    "partNumber" : "E5-2670"
                },
                "board_1" : {
                    "type" : "board",
                    "vendor" : "Xilinx",
                    "partNumber" : "EK-V7-VC707-G"
                }
            },

            "devices" : {
                "deviceID1" : {
                    "type" : "cpu_1",
                    "host" : true
                },
                "deviceID2" : {
                    "type" : "fpga_xv7"
                }
            },
            "connectionTypes" : {
                "conn1" : {
                    "standard" : "PCIe",
                    "bandwidth":"8GB/s",
                    "duplex" : "full",
                    "version" : "2.0"
                }
            },
            "connections" : [
                {
                    "source" : "deviceID1",
                    "target" : "deviceID2",
                    "type" : "conn1"
                }
            ]
        },

        "system" : {
            "nodes" : [
                "nodeId1",
                "nodeId2"
            ],
            "connectionTypes" : {
                "ethernet_100" : {
                    "standard" : "ethernet",
                    "bandwidth" : "100Mbit/s",
                    "duplex" : "full",
                    "version" : "100BASE-TX"
                }
            },
            "connections" : [
                {
                    "source" : "nodeId1",
                    "target" : "nodeId2",
                    "type" : "ethernet_100"
                }
            ]
        }
    },

    "language" : "C",
    "codeArchive" : "archive_name.tar.gz",
    "functions" : {
        "function_symbol_1" : {
            "name" : "function-name",
            "returnType" : "int",
            "parameters" : [
                {
                    "name" : "a",
                    "type" : "int"
                }
            ],
            "startLine" : 98,
            "endLine" : 103,
            "filePath" : "folder/file.c",
            "language" : "c"
        },
        "function_symbol_2" : {
            "name" : "function-name",
            "returnType" : "int",
            "parameters" : [
                {
                    "name" : "b",
                    "type" : "int"
                },
                {
                    "name" : "c",
                    "type" : "char"
                }
            ],
            "startLine" : 23,
            "endLine" : 34,
            "filePath" : "folder/file2.c",
            "language" : "c"
        }
    },
    "callgraph" : {
        "function_symbol_1" : [
            "function_symbol_2",
            "malloc",
            "printf"
        ]
    },

    "architecturalTemplate" : {
        "id" : "SST_1.0",
        "type" : "SST",
        "version" : "1.0",
        "supportedDevices":["deviceID1"],
        "targetConfiguration": {
            "devices" : ["deviceID1"]
        },
        "functions" : {
            "function_identifier_1" : {
                "hardwareAcceleration" : true
            },
            "function_identifier_2" : {
                "hardwareAcceleration" : false
            }
        }
    }
}

```

The input Json file provides multiple information regarding the definition of a node, as well as various data concerning the functions present into the source code.

As the resource hardware estimation step's task is to estimate of much resources are taken by each function, a very interesting part of the file is represented by this part:

```json
{
    "other_stuff": {"..."},


    "architecturalTemplate" : {
        "id" : "SST_1.0",
        "type" : "SST",
        "version" : "1.0",
        "supportedDevices":["deviceID1"],
        "targetConfiguration": {
            "devices" : ["deviceID1"]
        },
        "functions" : {
            "function_identifier_1" : {
                "hardwareAcceleration" : true
            },
            "function_identifier_2" : {
                "hardwareAcceleration" : false
            }
        }
    }
}

```

In the **architecturalTemplate** section in fact, we can find multiple information regarding the device supported and all the functions that have been previously identified by CAOS to be candidate for hardware acceleration. 
Thanks to these information, our module can easily focus on estimating hardware resources for just the functions with the field ** "hardwareAcceleration" ** to true, and thanks to the information available in the previous part of the file we can easily understand where these functions are implemented in the source file, as well as the location of the files.

The output of the custom module, has to be compliant with the interfaces available within CAOS. An example output json file for this step is the following:

```json
{
    "function_identifier_1" : {
        "resourceEstimation" : {
            "deviceType1" : {
                "DSP48E":10,
                "BRAM_18K":34,
                "LUT":90,
                "FF":7
            },
            "deviceType2": {
                "DSP48E":3,
                "BRAM_18K":90,
                "LUT":91,
                "FF":4
            }
        }
    }
}

```

In this output file, it is observable as for each deviceType indicated in the input json file, and for each function identified as candidate for hardware acceleration, we need to provide CAOS the estimate for each resource.

### 2. Module Implementation

Use the template file to start implementing your own module. The file begins with the inclusion of all the libraries necessary to CAOS to call the custom module.
The implement the custom module, it is necessary to modify the module.py file. In particular, inside this module it is necessary to implement the **runModule** function:

```python
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

    #implement Module here

    return responseData
```
Where **responseData** needs to be compliant with the Json file described in the previous section.
 

### 3. Test the new Module

### 4. Run your module on a public server

To allow CAOS to use the custom module, it is necessary to deploy it on a public server and retrieve the **IP Address** and the ***port number***.
To deploy the application on your own server it is just necessary to execute:

```python
python3 module.py
```


### 5. Change Module within CAOS

Once the code has been deployed on a public server, the last step that it is necessary to perform is to specify the Hostname and the port number of the public server inside CAOS and click update to check wether the connection works.

![CAOS IP specification](https://raw.githubusercontent.com/necst/CAOS_examples/master/module_integration/imgs/CAOS_ip.png)

If everything has been done correctly, CAOS will display that the status of the module in online, and it will be possible to use the custom module.