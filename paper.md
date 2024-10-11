---
title: 'DroneWQ: A Python package for processing MicaSense multispectral drone imagery for aquatic remote sensing'
tags:
  - Python
  - UAS
  - drone
  - remote sensing
  - water quality
authors:
  - name: Anna E. Windle
    orcid: 0000-0002-4852-5848
    affiliation: "1, 2"
    equal-contrib: true
    corresponding: true
  - name: Patrick Gray 
    orcid: 0000-0002-8997-5255
    affiliation: "3, 4"
    equal_contrib: true
  - name: Alejandro Román
    orcid: 0000-0002-8868-9302
    affiliation: 5
  - name: Sergio Heredia
    orcid: 0009-0003-9495-9625
    affiliation: 5
  - name: Gabriel Navarro
    orcid: 0000-0002-8919-0060
    affiliation: 5
  - name: Greg M. Silsbe
    orcid: 0000-0003-2673-1162
    affiliation: 6
affiliations:
 - name: NASA Goddard Space Flight Center, Greenbelt, MD, United States
   index: 1
 - name: Science Systems and Applications, Inc., Lanham, MD, United States
   index: 2
 - name: School of Marine Sciences, University of Maine, Orono, ME, United States
   index: 3
 - name: Department of Marine Geosciences, Charney School of Marine Sciences, University of Haifa, Haifa, Israel
   index: 4
 - name: Department of Ecology and Coastal Management, Institute of Marine Sciences of Andalusia (ICMAN-CSIC), Spanish National Research Council (CSIC), 11519 Puerto Real, Spain
   index: 5
 - name: Horn Point Laboratory, University of Maryland Center for Environmental Science, Cambridge, MD, United States
   index: 6
 
date: 28 January 2023
bibliography: paper.bib
---

# Summary

Small aerial drones conveniently achieve scales of observation between satellite resolutions and in situ sampling, effectively diminishing the “blind spot” between these established measurement techniques [@gray_larsen_johnston_2022]. Drones equipped with off-the-shelf multispectral sensors originally designed for terrestrial applications are being increasingly used to derive water quality properties. Multispectral drone imagery requires post processing to radiometrically calibrate raw pixel values to useful radiometric units, remove surface reflected light and sun glint, and map spatial patterns of water quality parameters. 

# Statement of need

`DroneWQ` is a Python package for multispectral drone imagery processing to obtain remote sensing reflectance (R<sub>rs</sub>), the fundamental input into ocean color algorithms which can be used to estimate and map water quality parameters. The processing steps, calibrations, and corrections necessary to obtain research quality R<sub>rs</sub> data from drones can be prohibitively difficult for those who do not specialize in optics and remote sensing, yet the data once obtained can reveal entirely new insight into aquatic ecosystems. `DroneWQ` was designed to be a simple pipeline for managers, researchers, and students who wish to utilize drone multispectral remote sensing to analyze ocean color and water quality. The combination of processing, georeferencing, and mapping drone imagery will enable effective water quality monitoring at fine spatial resolutions. The simple functionality of `DroneWQ` will enable exciting scientific exploration of drone remote sensing by students and experts alike. 

# Background/Theory

Following the notation style and large body of research from the optical oceanography community, drones can measure remote sensing reflectance (R<sub>rs</sub>) defined as:

<div align="center">
R<sub>rs</sub> (θ, φ, λ) = L<sub>W</sub>(θ, φ, λ) / E<sub>d</sub>(θ, φ, λ)  Eq. 1 
</div>
<br/>

where L<sub>W</sub> (W m<sup>-2</sup> nm<sup>-1</sup> sr<sup>-1</sup>) is water-leaving radiance, E<sub>d</sub> (W m<sup>-2</sup> nm<sup>-1</sup>) is downwelling irradiance, θ represents the sensor viewing angle between the sun and the vertical (zenith), φ represents the angular direction realtive to the sun (azimuth) and λ represents wavelength. 

Like all above-water optical measurements, drones do not measure R<sub>rs</sub> directly as the at-sensor total radiance (L<sub>T</sub>, W m<sup>-2</sup> nm<sup>-1</sup> sr<sup>-1</sup>) constitutes the sum of L<sub>W</sub> and incident radiance reflected off the sea surface into the detector's field of view, referred to as surface reflected radiance (L<sub>SR</sub>). L<sub>W</sub> is radiance that emanates from the water and contains a spectral shape and magnitude governed by optically active water constituents interacting with downwelling irradiance, while L<sub>SR</sub> is independent of water constituents and is instead governed by a given sea-state surface reflecting the downwelling light; a familiar example is sun glint. Here we define UAS total reflectance (R<sub>UAS</sub>) as:

<div align="center">
R<sub>UAS</sub>(θ, Φ, λ) = L<sub>T</sub>(θ, Φ, λ) / E<sub>d</sub>(λ) Eq. 2
<br/>
</div>
where
<br/>
<div align="center">
L<sub>T</sub>(θ, Φ, λ)= L<sub>W</sub>(θ, Φ, λ) + L<sub>SR</sub>(θ, Φ, λ) Eq. 3 
</div>
<br/>

If a water surface was perfectly flat, incident light would reflect specularly and could be measured with known viewing geometries. This specular reflection of a level surface is known as the Fresnel reflection; however, most water bodies are not flat as winds and currents create tilting surface wave facets. Due to differing orientation of wave facets reflecting radiance from different parts of the sky, L<sub>SR</sub> can vary widely within a single image. A common approach to model L<sub>SR</sub> is to express it as the product of sky radiance (L<sub>sky</sub>, W m<sup>-2</sup> nm<sup>-1</sup> sr<sup>-1</sup>) and ⍴, the effective sea-surface reflectance of the wave facet [@mobley_1999; @lee_ahn_mobley_arnone_2010]:

<div align="center">
L<sub>SR</sub>(θ, Φ, λ)= ρ(θ, Φ, λ) ∗ L<sub>sky</sub>(θ', Φ, λ) Eq. 4
<br/>
</div>
Where θ' is the mirror of θ (θ' = 180-θ). Rearranging Eqs. 3 Eqs. 4, ⍴ can be derived by:
<br/>
<div align="center">
ρ(θ, Φ, λ) = L<sub>T</sub>(θ, Φ, λ) − L<sub>W</sub>(θ, Φ, λ) / L<sub>sky</sub>(θ', Φ, λ) Eq. 5
</div>
<br/>
Given measurements of L<sub>sky</sub>, an accurate determination of ⍴ is critical to derive R<sub>rs</sub> by:
<div align="center">
<br/>
R<sub>rs</sub>(θ, Φ, λ) = R<sub>UAS</sub>(θ, Φ, λ) − (L<sub>sky</sub>(θ', Φ, λ) ∗ ρ(θ, Φ, λ) / E<sub>d</sub>(λ))  Eq. 6
</div>
<br/>

# Removal of surface reflected light (L<sub>T</sub> - L<sub>SR</sub> = L<sub>W</sub>) 

The inclusion of L<sub>SR</sub> can lead to an overestimation of R<sub>rs</sub> and remotely sensed water quality retrievals, as shown in Figure 1. `DroneWQ` provides three common approaches to remove L<sub>SR</sub> as described below. See an intercomparison of these methods for drone imagery in [@windle_silsbe_2021].

![Caption for example figure.\label{fig:removal_Lsr_fig}](figs/removal_Lsr_fig.jpg)
<br/>
Figure 1. Example of an individual drone image (green band) with different radiometric values: (A) R<sub>UAS</sub>, (B) R<sub>UAS</sub> with initial sun glint masking and (C–F) remote sensing reflectance (R<sub>rs</sub>) using various methods to remove surface reflected light: (C) ⍴ look-up table (LUT) from HydroLight simulations, (D) Dark pixel assumption with NIR = 0, (E) Dark pixel assumption with NIR > 0, (F) Deglingting methods following [@hedley_harborne_mumby_2005]. Figure taken from [@windle_silsbe_2021].

`blackpixel_method()`
<br/>
One method to remove L<sub>SR</sub> relies on the so-called black pixel assumption that assumes L<sub>W</sub> in the near infrared (NIR) is negligible due to strong absorption of water. Where this assumption holds, at-sensor radiance measured in the NIR is solely L<sub>SR</sub> and allows ⍴ to be calculated if L<sub>sky</sub> is known. Studies have used this assumption to estimate and remove L<sub>SR</sub>; however, the assumption tends to fail in more turbid waters where high concentrations of particles enhance backscattering and L<sub>W</sub> in the NIR [@siegel_wang_maritorena_robinson_2000]. *Therefore, this method should only be used in waters whose optical propeties are dominated and co-vary with phytoplankton (e.g. Case 1, open ocean waters).* 

`mobley_rho_method()`
<br/>
Tabulated ρ values have been derived from numerical simulations with modelled sea surfaces, Cox and Munk wave states (wind), and viewing geometries [@mobley_1999]. Mobley (1999) provides the recommendation of collecting radiance measurements at viewing directions of θ = 40° from nadir and ɸ = 135° from the sun to minimize the effects of sun glint and nonuniform sky radiance with a ⍴ value of 0.028 for wind speeds less than 5 m/s. These suggested viewing geometries and ⍴ value have been used to estimate and remove L<sub>SR</sub> in many remote sensing studies. *This method should only be used if using a drone sensor that is angled 30-40° from nadir and if wind speed is less than 5 m/s.*

`hedley_method()`
<br/>
Other methods to remove L<sub>SR</sub> include modelling a constant 'ambient' NIR signal that is removed from all pixels. This method relies on two assumptions: 1) The brightness in the NIR is composed only of sun glint and a spatially constant 'ambient' NIR component, and 2) The amount of L<sub>SR</sub> in the visible bands is linearly related to the amount in the NIR band [@hedley_harborne_mumby_2005]. Briefly, the minimum 10% of NIR radiance, min(Lt<sub>NIR</sub>), is calculated from a random subset of images. Next, linear relationships are established between the Lt<sub>NIR</sub> and the visible band values, which would be homogenous if not for the presence of L<sub>SR</sub>. Then, the slope (*b*) of the regressions are used to predict L<sub>SR</sub> for all pixels in the visible bands that would be expected if those pixels had a Lt<sub>NIR</sub> value of min(Lt<sub>NIR</sub>):
<div align="center">
<br/>
Lw<sub>i</sub> = Lt<sub>i</sub> - b<sub>i</sub>(Lt(NIR) - min(Lt<sub>NIR</sub>)), where i is each band
<br/>
</div>
<br/>

*This method can be utilized without the collection of L<sub>sky</sub> images.*  

# Normalizing by downwelling irradiance (L<sub>W</sub> / E<sub>d</sub> =  R<sub>rs</sub>) 
 After L<sub>SR</sub> is removed from L<sub>t</sub>, the product of that removal L<sub>w</sub> needs to be normalized by E<sub>d</sub> to calculate R<sub>rs</sub> (Eq. 6). The downwelling light sensor (DLS) or calibration reflectance panel can be used to calculate E<sub>d</sub>.

`panel_ed()`
<br/> 
An image capture of the MicaSense calibrated reflectance panel with known reflectance values can be used to calculate E<sub>d</sub>. It is recommended to use this method when flying on a clear sunny day. 

`dls_ed()`
<br/>
The MicaSense DLS measures downwelling hemispherical irradiance (E<sub>d</sub>) in the same spectral wavebands during in-flight image captures. According to MicaSense, the DLS is better at estimating changing light conditions (e.g. variable cloud cover) since it records DLS throughout a flight; however, it is not a perfect measurement due to movement of the drone. The the MicaSense function `capture.dls_irradiance()` incorporates tilt-compensated DLS values from the onboard orientation sensor but is imperfect. 

On days with changing cloud conditions it is recommended to use both the DLS and calibration reflectance panel measurements, when possible. This is done by applying a compensation factor from the calibration reflectance panel to all DLS measurements. This can be done by setting the argument dls_corr to TRUE in `dls_ed()`.
  
<br/> 
  
# R<sub>rs</sub> pixel masking
An optional pixel masking procedure can be applied to R<sub>rs</sub> data to remove instances of specular sun glint and other artifacts in the imagery such as adjacent land, vegetation shadowing, or boats when present in the imagery. Pixels can be masked two ways: 

`rrs_threshold_pixel_masking()`
<br/> 
This function masks pixels based on a user supplied R<sub>rs</sub> thresholds to mask pixels containing values > R<sub>rs</sub>(NIR) threshold and < R<sub>rs</sub>(green) threshold.  

`rrs_std_pixel_masking()`
<br/>
This function masks pixels based on a user supplied NIR factor. The mean and standard deviation of NIR is calculated from a user supplied amount of images, and pixels contain a NIR value > mean + std * mask_std_factor are masked. The lower the mask_std_factor, the more pixels will be masked.
<br/>
 
# Water quality retrievals 
R<sub>rs</sub> is often used as input into various bio-optical algorithms to obtain concentrations of optically active water quality constituents such as chlorophyll-a or total suspended matter (TSM). Several functions can be applied to calculate concentrations. 

`chl_hu()`
<br/>
This is the Ocean Color Index (CI) three-band reflectance difference algorithm [@hu_lee_franz_2012]. This should only be used for chlorophyll-a retrievals below 0.15 mg m^-3.
<br/>

`chl_ocx()`
<br/>
This is the OCx algorithm which uses a fourth-order polynomial relationship [@oreilly_maritorena_mitchell_siegel_carder_garver_kahru_mcclain_1998]. This should be used for chlorophyll retrievals above 0.2 mg m^-3. The coefficients for OC2 (OLI/Landsat 8) are used as default as the closest match in bands to the Micasense sensors.
<br/>

`chl_hu_ocx()`
<br/>
This is the blended NASA chlorophyll algorithm which merges the Hu et al. (2012) color index (CI) algorithm (chl_hu) and the O'Reilly et al. (1998) band ratio OCx algortihm (chl_ocx). This specific code is grabbed from https://github.com/nasa/HyperInSPACE. Documentation can be found here https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/.
<br/>

`chl_gitelson()`
<br/>
This algorithm estimates chlorophyll-a concentrations using a 2-band algorithm designed and recommended for turbid coastal (Case 2) waters [@gitelson_schalles_hladik_2007].
<br/>

`nechad_tsm()`
<br/>
This algorithm estimates total suspended matter (TSM) concentrations and is tuned and tested in turbid waters [@nechad_ruddick_park_2010].
<br/>


# Georeferencing and mapping
`georeference()`
<br/>
This function uses MicaSense metadata (altitude, pitch, roll, yaw, lat, lon) to georeference all captures to a known coordinate space. See notes on georeferencing below. 

`mosaic()`
<br/>
This function mosaics all the given georeferenced captures into one georeferenced mosaicked raster file. 

`downsample()`
<br/>
This function performs a downsampling procedure to reduce the spatial resolution of the final georeferenced mosaic.  

`plot_basemap()`
<br/>
This function loads a basemap and plots the georeferenced mosaic in the axes provides using pseudo-Mercator projection (epsg:3857).

Notes on georeferencing:

* The pitch, roll, and yaw angles are associated with the MicaSense sensor. The following statements should help you understand the angles:
    * pitch = 0°, roll = 0°, yaw = 0° means: the sensor is nadir (looking down to the ground), the sensor is assumed to be fixed (or on a gimbal), and not moving side to side, the top of the image points to the north.
    * pitch = 90°, roll = 0°, yaw = 0° means: the sensor is looking forward from the aircraft, the sensor is assumed to be fixed (or on a gimbal), and not moving side to side, the top of the image points to the north.
    * pitch = 0°, roll = 0°, yaw = 90° means: the sensor is nadir (looking down to the ground), the sensor is assumed to be fixed (or on a gimbal), and not moving side to side, the top of the image points to the east.
<br/>

* If possible, it is recommended to fly the drone using a consistent yaw angle (e.g. drone/sensor does not turn 180° every transect). This will make georeferencing easier and alleviate issues with changing sun glint on different transects. Some drone flight planning softwares allow you to do this (e.g. UGCS). If not, it is recommended that you note the drone/sensor's yaw angle and use this in the `georeference()` function.
* If a yaw angle is not available, it is recommended to test a couple captures that contain land and use the MicaSense metadata. The MicaSense sensor contains an Inertial Measurement Unit (IMU) that collects data on the sensor pitch, roll, and yaw; however, this data can be impacted by IMU errors, especially during turns and windy flights. You can see how much the sensor yaw angle varies by plotting the IMU metadata yaw angle over captures. An example is included in the primary_demo.ipynb.
    * If you have a small dataset, you can manually go through the captures to select which ones line up with what transect to inform the yaw argument in the georeference() function. It is recommended to skip images that are taken when the drone/sensor is turning since the IMU is prone to errors during drone turns.
    * If you have a large dataset where this can be too time consuming, we have provided functions to automatically select captures with varying yaw angles that line up with different transects. The `compute_flight_lines()` function returns a list of image captures taken in different transects that contain consistent yaw angles. This can be incorporated into the  `georeference()` function to improve georeferencing and mosaicking. 

  
# Demo notebook
DroneWQ includes a jupyter notebooks to demonstrate the processing functions. 
* `primary_demo.ipynb` includes a standard workflow to process raw UAS imagery to Rrs. It also demostrates how to derive water quality concentrations (chloropyll a and total suspended matter) from Rrs. Lastly, it demonstrates how to georeference using sensor metadata and mosaic derived images to visualize spatial patterns on a map. 

# Publications utilizing DroneWQ

Román, A., Heredia, S., Windle, A. E., Tovar-Sánchez, A., & Navarro, G. (2024). Enhancing Georeferencing and Mosaicking Techniques over Water Surfaces with High-Resolution Unmanned Aerial Vehicle (UAV) Imagery. Remote Sensing, 16(2), 290.

Gray, P. C., Windle, A. E., Dale, J., Savelyev, I. B., Johnson, Z. I., Silsbe, G. M., ... & Johnston, D. W. (2022). Robust ocean color from drones: Viewing geometry, sky reflection removal, uncertainty analysis, and a survey of the Gulf Stream front. Limnology and Oceanography: Methods, 20(10), 656-673.

Windle, A. E., & Silsbe, G. M. (2021). Evaluation of unoccupied aircraft system (UAS) remote sensing reflectance retrievals for water quality monitoring in coastal waters. Frontiers in Environmental Science, 9, 674247.

# Acknowledgements

We acknowledge and appreciate helpful support from the Micasense team. We thank Julian Dale for assisting with drone flights. 

# References

