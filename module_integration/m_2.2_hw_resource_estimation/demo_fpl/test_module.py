import sys
import os
import json
from os import path

current_directory = path.dirname(os.path.abspath(__file__))

sys.path.append(path.join(current_directory, '..', '..', 'libraries'))
import CAOSModuleTester

# path to json input and code archive input
code_archive_path = path.join(current_directory, 'test_resources', 'code.tar.gz')
json_input_path = path.join(current_directory, 'test_resources', 'caos_request.json')

# open the input files
with open(code_archive_path) as code_archive_file, open(json_input_path) as json_input_file:

    # parse the json input file
    json_payload = json.load(json_input_file)

    # run the module tester
    CAOSModuleTester.test(
        jsonPayload = json_payload,
        files = {
            'code.tar.gz': code_archive_file
        },
        port = 5022,
        hostname = 'localhost',
        handle_implementation = True, # let the tester start and stop the module by its own
        implementation_path = path.join(current_directory, 'module.py'),
        module_path = current_directory,
        work_dir = current_directory
    )
