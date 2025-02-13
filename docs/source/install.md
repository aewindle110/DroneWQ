## Installation

### Requirements

We recommend running this package in a Docker container, which is the environment that it was developed and tested in. See https://docs.docker.com/ for installation files. You will also need to install git (https://github.com/git-guides/install-git). Total file size is ~ 1.6 GB.

### Initial Setup

Once Docker and git are installed, setup a local directory. Navigate to the directory through terminal (OSX or Linux) or Powershell (Windows). Clone the repo to your local machine: 

`git clone https://github.com/aewindle110/DroneWQ.git`.  

### Launching code
    
With the Docker app running on your desktop, you need to launch the Docker container. Note that the first execution of this line of code will install the Docker image and setup and configure all required software (python, jupyter notebooks) and packages. This could take several minutes, depending on computer speed.
    
`docker run -it -v <local directory>:/home/jovyan --rm -p 8888:8888 clifgray/dronewq:v3`

where `<local directory>` is where you want data to be saved. 

It should already be activated but if you need to activate the dronewq conda environment: 

`conda activate dronewq`

And then launch a jupyter lab or notebook from the home directory on the docker container:

`jupyter lab --allow-root --ip 0.0.0.0 /home/jovyan`

Copy the generated URL in the terminal (e.g. `http://127.0.0.1:8888/?token=<auto generated token>`) into a web browser.

### Alternative Installation (conda) 

You can also build the environment yourself by following the instructions from the micasense repo here https://micasense.github.io/imageprocessing/MicaSense%20Image%20Processing%20Setup.html which includes instructions on how to download exiftool. We have included a lightweight version of the MicaSense imageprocessing scripts in this repo (they can be found [here](https://github.com/micasense/imageprocessing). Note that our `micasense` scripts are slightly modified in that radiance data type is expressed as Float32 instead of Uint16 and we change the output of image.radiance() to output milliwatts (mW) instead of watts (W). This impacts the panel_ed calculation which relies on image.radiance(). We also modified capture.save_capture_as_stack() accordingly to not scale and filter the data. MicaSense is planning on a future package with user specified radiance data types, at which point we will revert to their package version.

After you have cloned the DroneWQ repo to your local machine and installed exiftool, `cd` to the directory you cloned this repository to.

Create a virtual conda env by running `conda env create -f environment.yml`. This will configure an anaconda environment with all of the required tools and libraries. 
When it's done, run `conda activate dronewq` to activate the environment configured.
Each time you start a new anaconda prompt, you'll need to run `conda activate dronewq`.

To access jupyter notebook or lab, run `jupyter lab` or `jupyter notebook`

### MicaSense Folder Structure
Once all MicaSense images have been downloaded into a local directory (e.g. `\data`), you will need to manually separate images into 4 sub-directories as below:
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