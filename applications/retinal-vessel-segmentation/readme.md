# Retinal Vessel Segmentation
Retinal Image Segmentation Application developed by Andreas Brokalakis and Antonis Nikitakis - Synelixis Solutions Ltd. - for the CAOS framework.

### Code Structure
Files that need to be provided to CAOS:
 1. architecture-description-aws-f1.json: Json file containing the description of the architecture for an AWS F1 instance. (In the CAOS implementation stage, make sure to specify 'm_3_sdaccel' as the module's hostname)
 2. architecture-description-aws-zcu102.json: Json file containing the architecture description of a Xilinx Zynq UltraScale+ ZCU102 board (In the CAOS implementation stage, make sure to specify 'm_3_default' as the module's hostname)
 3. program-description.json: Json file containing the description of the program.
 4. code.zip: Archive containing the source code. Do not unzip the archive, CAOS requires to be compressed.
 5. dataset.zip: Archive containing the necessary files for testing the application.

For profiling the application, after providing caos the dataset.zip file, it is necessary to specify: %%DATASET_DIR%%/input_orig.ppm
as command line argument.
