# Variational Monte Carlo
Variational Monte Carlo simulation application developed by Alex Thom and Salvatore Cardamone - Cambridge University - for the CAOS framework.

### Code Structure
Files that need to be provided to CAOS:
 1. architecture-description-aws-f1.json: Json file containing the description of the architecture for an AWS F1 instance. (In the CAOS implementation stage, make sure to specify 'm_3_sdaccel' as the module's hostname)
 2. program-description.json: Json file containing the description of the program.
 3. code.zip: Archive containing the source code. Do not unzip the archive, CAOS requires to be compressed.

For testing the application it is not necessary to provide to CAOS any dataset archive. As a command line argument, you can test the application using: 100 0.8. The first number represents the number of iteration the application will perform, while the second one is the amplitude of the random number generator.
