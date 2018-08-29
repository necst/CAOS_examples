# Retinal Vessel Segmentation
Retinal Image Segmentation Application developed by Andreas Brokalakis and Antonis Nikitakis - Synelixis Solutions Ltd. - for the CAOS framework.

### Code Structure
Files that need to be provided to CAOS:
 1. architecture-description.json : Json file containing the description of the architecture.
 2. program-description.json: Json file containing the description of the program.
 3. code.zip: Archive containig the source code. Do not unzip the archive, CAOS requires to be compressed.
 4. dataset.zip: Archive containing the necessary files for testing the application.

For testing the application after providing caos the dataset.zip file, it is necessary to specify 
 %%DATASET_DIR%%/input_orig.ppm
as command line argument.