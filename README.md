# UAS_WQ

UAS multispectral remote sensing
____ is a Python package that can be used to analyze multispectral data collected from a UAS. These scripts are specific for the MicaSense RedEdge-MX camera. 

## ***Important*** 
Once all MicaSense images have been downloaded into a local directory, please seperate images into 3 sub-directories labeled:

* 'panel'

* 'sky'

* 'flight'



## **Descriptions of functions:**
* store_metadata: Store metadata from all flight captures to use for plotting and georeferencing

* align_stack_Lt: Convert raw (DN) individual images to aliged, stacked tiffs with units of radiance (L<sub>t</sub>, W m<sup>-2</sup> nm<sup>-1</sup> sr<sup>-1</sup>)

* align_stack_R: Convert raw (DN) individual images to aliged, stacked tiffs with units of reflectance (*add here*)

*  align_stack_Rrs: Convert raw (DN) individual images to aliged, stacked tiffs with units of remote sensing reflectance (Rrs, sr<sup>-1</sup>)

*  Pre_process_filter: Mask out erronous pixels (e.g. specular sun glint, land, or instances of a boat)

*  georeference_mosaic: Use MicaSense GPS and IMU to georegister and reproject images to how it would appear on Earth. Mosaic images together to create an orthomosaic. 
