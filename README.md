# UAS_WQ


____ is a Python package that can be used to analyze multispectral data collected from a UAS. These scripts are specific for the MicaSense RedEdge cameras. You will need to also download the MicaSense imageprocessing scripts that can be found [here](https://github.com/micasense/imageprocessing). The entire imageprocessing repo will need to be downloaded locally in the same directory as this package. 

## ***Important*** 
Once all MicaSense images have been downloaded into a local directory, please seperate images into 3 sub-directories labeled:

* 'panel'

* 'sky'

* 'flight'



## **Descriptions of functions:**
* store_metadata: Store metadata from all flight captures to use for plotting and georeferencing

* align_stack_flight_DN, align_stack_sky_DN: Convert raw (DN) individual flight images to aliged, stacked tiffs with units of DN. 

* align_stack_Lt, align_stack_Lsky: Convert raw (DN) individual flight images to aliged, stacked tiffs with units of radiance (L<sub>t</sub>, W m<sup>-2</sup> nm<sup>-1</sup> sr<sup>-1</sup>)

* align_stack_Ruas: Calculate Ruas by reading in Lt images and dividing by Ed calcualted three different methods (1: DLS, 2: panel, 3: DLS_corr) and save as aligned, stacked tifs with units of reflectance (sr<sup>-1</sup>??)

*  align_stack_Rrs_blackpixel: Calculate Rrs when Ruas(NIR) = 0 (black pixel asumption). Saves aligned, stacked tiffs with units of remote sensing reflectance (Rrs, sr<sup>-1</sup>)

*  align_stack_Rrs_deglinting: Calculate Rrs using a deglinting procdure from Hochberg et al. 2003 

*  filter_pixels: Mask out erronous pixels (e.g. specular sun glint, land, or instances of a boat)

*  georeference_mosaic: Use MicaSense GPS and IMU to georegister and reproject images to how it would appear on Earth. Mosaic images together to create an orthomosaic. 
