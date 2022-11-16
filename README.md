# DroneWQ: A Python library for measuring water quality with a multispectral drone sensor


DroneWQ is a Python package that can be used to analyze multispectral data collected from a drone to derive ocean color radiometry and water quality properties. These scripts are specific for the MicaSense RedEdge and Altum cameras. 

The main processing script converts raw multispectral imagery to total radiance (Lt) with units of W/m2/nm/sr, removes sun glint and surface reflected light (Lsr) to calculate water leaving radiance (Lw), measures downwelling irradiance (Ed) from either the calibrated reflectance panel or downwelling light sensor, and calculates remote sensing reflectance (Rrs) by dividing Ed by Lw. Rrs can be used as input into various bio-optical algorithms to derive chlorophyll a and total suspended sediment concentrations. Images can also be georeferenced using image metadata to orient and map to a known coordinate system. 


More information on the methods found in this package can be found in:

Gray, P.C., Windle, A.E., Dale, J., Savelyev, I.B., Johnson, Z.I., Silsbe, G.M., Larsen, G.D. and Johnston, D.W., 2022. Robust ocean color from drones: Viewing geometry, sky reflection removal, uncertainty analysis, and a survey of the Gulf Stream front. Limnology and Oceanography: Methods. doi:10.1002/lom3.10511

Windle, A.E. and Silsbe, G.M., 2021. Evaluation of unoccupied aircraft system (UAS) remote sensing reflectance retrievals for water quality monitoring in coastal waters. Frontiers in Environmental Science, p.182. doi:10.3389/fenvs.2021.674247


[[I think we need a figure here that shows the workflow even something simple]]

## Installation

### Requirements

We recommend running this package in a Docker container, which is the environment that it was developed and tested in. See https://docs.docker.com/ for installation files. You also need to install git (https://github.com/git-guides/install-git).

### Initial Setup

Once Docker and git are installed, setup a <local directory>, and navigate to this directory through terminal (OSX or Linux) or Powershell (Windows). The first step is cloning the repo to your local machine: 

`git clone https://github.com/aewindle110/DroneWQ.git`.  

`docker run -it -v <local directory>:/home/jovyan --rm -p 8888:8888 clifgray/drone_wq:v1`

## Launching code
This will launch the Docker container and then you need to activate the conda environment via:

`conda activate micasense`

Then run jupyter via:

`jupyter notebook --allow-root --ip 0.0.0.0 /home/jovyan`

Then just navigate to the URL that is generated and pointed to in the terminal. This should take the form of roughly `http://127.0.0.1:8888/?token=<auto generated token>`

This series of commands will pull this Docker image if you don't already have it, run it, mount your local directory, then expose the jupyter lab to your local IP address. You can then run this in Jupyter as if it were local on your hardware but in the exact same environment it was developed with all the necessary packages installed and configured. 

You can also build the environment yourself by following the instructions from the micasense repo here https://micasense.github.io/imageprocessing/MicaSense%20Image%20Processing%20Setup.html

Though it is likely quicker and more reproducible to just pull it from Dockerhub with the first command.

We have included a lightweight version of the MicaSense imageprocessing scripts in this repo (they can be found [here](https://github.com/micasense/imageprocessing), but our version is slightly modified to put out radiance in Float32 format instead of Uint16. Future versions of the Micasense package are planned to make this an option and at that point we will remove it from our library and simply import the up to date maintained version.

## ***Data Setup*** 
Once all MicaSense images have been downloaded into a local directory (e.g. `\data`), separate images into 4 sub-directories as below:
```
\data
    \panel
    \raw_sky_imgs
    \raw_water_imgs
    \align_img
```
* The panel directory should contain all image captures of the Micasense calibrated reflectance panel taken either before or after the flight 
* The raw_sky_imgs directory should contain all image captures taken of the sky at a 40 deg angle from zenith and an apprximate 135 deg azimuthal viewing direction
* The raw_water_imgs directory should contain all image captures of water taken during flight 
* The align_img directory should contain one image capture (5 .tifs) from the raw_water_imgs directory. The warp_matrix derived from this image capture is used to align all image captures in raw_water_imgs. 

