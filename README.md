# DroneWQ: A Python library for measuring water quality with a multispectral drone sensor


____ is a Python package that can be used to analyze multispectral data collected from a UAS. These scripts are specific for the MicaSense RedEdge cameras. 

[[I think we need a figure here that shows the workflow even something simple]]

## Installation
To install you will need to clone this repo to your local machine: `git clone https://github.com/aewindle110/DroneWQ.git`. We recommend you run all this via Docker so you have the exact same environment that it was developed and tested in. This can be done by going to the terminal (OSX or Linux) or Powershell (Windows) and running:

`docker run -it -v <local directory>:/home/jovyan --rm -p 8888:8888 clifgray/drone_wq:v1`

This will launch the Docker container and then you need to activate the conda environment via:

`conda activate micasense`

Then run jupyter via:

`jupyter notebook --allow-root --ip 0.0.0.0 /home/jovyan`

Then just navigate to the URL that is generated and pointed to in the terminal. This should take the form of roughly `http://127.0.0.1:8888/?token=<auto generated token>`

This series of commands will pull this Docker image if you don't already have it, then run it, then mount your local directory, then expose the jupyter lab to your local IP address. You can then run this in Jupyter as if it were local on your hardware but in the exact same environment it was developed with all the necessary packages installed and configured. 

You can also build the environment yourself by following the instructions from the micasense repo here https://micasense.github.io/imageprocessing/MicaSense%20Image%20Processing%20Setup.html

Though it is likely quicker and more reproducible to just pull it from Dockerhub with the first command.

You will need to also download the MicaSense imageprocessing scripts that can be found [here](https://github.com/micasense/imageprocessing). The entire imageprocessing repo will need to be downloaded locally in the same directory as this package. 

## ***Data Setup*** 
Once all MicaSense images have been downloaded into a local directory (e.g. `\data`), separate images into 3 sub-directories as below:
```
\data
    \panel
    \sky
    \flight
```

## **Descriptions of functions:**
* `store_metadata()`: Store metadata from all flight captures to use for plotting and georeferencing

* `align_stack_flight_DN()`, `align_stack_sky_DN()`: Convert raw (DN) individual flight images to aliged, stacked tiffs with units of DN. 

* `align_stack_Lt()`, `align_stack_Lsky()`: Convert raw (DN) individual flight images to aliged, stacked tiffs with units of radiance (L<sub>t</sub>, W m<sup>-2</sup> nm<sup>-1</sup> sr<sup>-1</sup>)

* `align_stack_Ruas()`: Calculate Ruas by reading in Lt images and dividing by Ed calcualted three different methods (1: DLS, 2: panel, 3: DLS_corr) and save as aligned, stacked tifs with units of reflectance (sr<sup>-1</sup>??)

*  `align_stack_Rrs_blackpixel()`: Calculate Rrs when Ruas(NIR) = 0 (black pixel asumption). Saves aligned, stacked tiffs with units of remote sensing reflectance (Rrs, sr<sup>-1</sup>)

*  `align_stack_Rrs_deglinting()`: Calculate Rrs using a deglinting procdure from Hochberg et al. 2003 

*  `filter_pixels()`: Mask out erronous pixels (e.g. specular sun glint, land, or instances of a boat)

*  `georeference_mosaic()`: Use MicaSense GPS and IMU to georegister and reproject images to how it would appear on Earth. Mosaic images together to create an orthomosaic. 
