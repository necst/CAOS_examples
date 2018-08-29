# Smith-Waterman
Basic implementation of the [Smith-Waterman Algorithm](https://en.wikipedia.org/wiki/Smith%E2%80%93Waterman_algorithm "Smith-Waterman Algorithm").

### Code Structure
Files that need to be provided to CAOS:
 1. architecture-description-aws-f1.json: Json file containing the description of the architecture for an AWS F1 instance. (In the CAOS implementation stage, make sure to specify 'm_3_sdaccel' as the module's hostname)
 2. program-description.json: Json file containing the description of the program.
 3. code.zip: Archive containing the source code. Do not unzip the archive, CAOS requires to be compressed.

For profiling the application it is not necessary to provide to CAOS any dataset archive or command line argument.