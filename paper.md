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
    orcid: 0000-0000-0000-0000
    affiliation: 1 
    equal-contrib: true
    corresponding: true
  - name: Patrick Gray 
    orcid: 0000-0000-0000-0000
    affiliation: 2
    equal_contrib:true
  - name: Greg M. Silsbe
    orcid: 0000-0000-0000-0000
    affiliation: 1
affiliations:
 - name: Horn Point Laboratory, University of Maryland Center for Environmental Science, Cambridge, MD, United States
   index: 1
 - name:  Division of Marine Science and Conservation, Nicholas School of the Environment, Duke University Marine Laboratory, Beaufort, NC, United States
   index: 2
date: 4 October 2022
bibliography: paper.bib

---

# Summary

Small aerial drones conveniently achieve scales of observation between satellite resolutions and in situ sampling, effectively diminishing the “blind spot” between these established measurement techniques. Drones equipped with off-the-shelf multispectral sensors originally designed for terrestrial applications are being increasingly used to derive water quality properties. Multispectral drone imagery requires post processing to radiometrically calibrate raw pixel values to useful radiometric units, remove sun glint and surface reflected light, and map spatial patterns of water quality parameters. 


# Statement of need

`DroneWQ` is a Python package for multispectral drone imagery processing to obtain and map estimates of water quality concentrations. `DroneWQ` was designed to be used by managers, researchers, and students who wish to utilize drone multispectral remote sensing to analyze water quality. The combination of processing, georeferencing, 
and mapping drone imagery will enable effective water quality monitoring at fine spatial resolutions. The simple functionality of `DroneWQ` will enable exciting scientific exploration of drone remote sensing by students and experts alike. 

# Background/Theory

Following a large body of research borne from earth observing satellites (Werdell and McClain, 2019), drones can measure remote sensing reflectance (R<sub>rs</sub>) defined as:

<div align="center">
R<sub>rs</sub> (θ, φ, λ) = L<sub>W</sub>(θ, φ, λ) / E<sub>d</sub>(θ, φ, λ)  Eq. 1 
</div>
<br/>

where L<sub>W</sub> (W m<sup>-2</sup> nm<sup>-1</sup> sr<sup>-1</sup>) is water-leaving radiance, Ed (W m<sup>-2</sup> nm<sup>-1</sup>) is downwelling irradiance, θ represents the sensor viewing angle between the sun and the vertical (zenith), φ represents the angular direction realtive to the sun (azimuth) and λ represents wavelength. 

Like all above-water optical measurements, drones do not measure R<sub>rs</sub> directly as the at-sensor total radiance (L<sub>T</sub>, W m<sup>-2</sup> nm<sup>-1</sup> sr<sup>-1</sup>) constitues the sum of L<sub>W</sub> and incident radiance reflected off the sea surface into the detecto's field of view, referred to as surface reflected radiance (L<sub>SR</sub>). L<sub>W</sub> is radiance that emanates from the water and contains a spectral shape and magnitude governed by optically active water constituents interacting with downwelling irradiance, while L<sub>SR</sub> is independent of water constituents and is instead governed by a given sea-state surface reflecting light; a familiar example is sun glint. Here we define UAS total reflectance (R<sub>UAS</sub>) as:

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

If a water surface was perfectly flat, incident light would reflect specularly and could be measured with known viewing geometries. This specular reflection of a level surface is known as the Fresnel reflection; however, most water bodies are not flat as winds and currents create tilting surface wave facets. Due to differing orientation of wave facets reflecting radiance from different parts of the sky, L<sub>SR</sub> can vary widely within a single image. A common approach to model LSR is to express it as the product of sky radiance (L<sub>sky</sub>, W m<sup>-2</sup> nm<sup>-1</sup> sr<sup>-1</sup>) and ⍴, the effective sea-surface reflectance of the wave facet (Mobley, 1999 ; Lee et al., 2010):

<div align="center">
L<sub>SR</sub>(θ, Φ, λ)= ρ(θ, Φ, λ) ∗ L<sub>sky</sub>(θ, Φ, λ) Eq. 4
<br/>
</div>
Rearranging Eqs. 3 Eqs. 4, ⍴ can be derived by:
<br/>
<div align="center">
ρ(θ, Φ, λ) = L<sub>T</sub>(θ, Φ, λ) − L<sub>W</sub>(θ, Φ, λ) / L<sub>sky</sub>(θ, Φ, λ) Eq. 5
</div>
<br/>
Given measurements of L<sub>sky</sub>, an accurate determination of ⍴ is critical to derive R<sub>rs</sub> by:
<div align="center">
<br/>
R<sub>rs</sub>(θ, Φ, λ) = R<sub>UAS</sub>(θ, Φ, λ) − (L<sub>sky</sub>(θ, Φ, λ) ∗ ρ(θ, Φ, λ) / E<sub>d</sub>(λ))  Eq. 6
</div>
<br/>

# Removal of surface reflected light (L<sub>T</sub> - L<sub>SR</sub> = L<sub>W</sub>) 

The inclusion of sun glint and L<sub>SR</sub> can lead to an overestimation of R<sub>rs</sub> and remotely sensed water quality retrievals, as shown in Figure _. `DroneWQ` provides a sun glint masking procedure to remove instances of specular sun glint and three common approaches to remove LSR as described below:

![Caption for example figure.\label{fig:removal_Lsr_fig}](removal_Lsr_fig.jpg)
<br/>
Figure 1. Example of an individual drone image (green band) with different radiometric values: (A) RUAS, (B) RUAS with initial sun glint masking and (C–F) remote sensing reflectance (Rrs) using various methods to remove surface reflected light: (C) ⍴ look-up table (LUT) from HydroLight simulations, (D) Dark pixel assumption with NIR = 0, (E) Dark pixel assumption with NIR >0, (F) Deglingting methods following Hochberg et al. (2003).

`blackpixel_method()`
<br/>
One method to remove L<sub>SR</sub> relies on the so-called black pixel assumption that assumes L<sub>W</sub> in the near infrared (NIR) is negligible due to strong absorption of water. Where this assumption holds, at-sensor radiance measured in the NIR is solely L<sub>SR</sub> (Gordon and Wang, 1994; Siegel et al., 2000) and allows ⍴ to be calculated if L<sub>sky</sub> is known. Studies have used this assumption to estimate and remove L<sub>SR</sub>; however, the assumption tends to fail in more turbid waters where high concentrations of particles enhance backscattering and L<sub>W</sub> in the NIR (Siegel et al., 2000; Lavender et al., 2005). *Therefore, this method should only be used in waters whos optical propeties are dominated and co-vary with phytoplankton (e.g. Case 1, open ocean waters).* 

`mobley_rho_method()`
<br/>
Tabulated ρ values have been derived from numerical simulations with modelled sea surfaces, Cox and Munk wave states (wind), and viewing geometries (Cox and Munk, 1954; Mobley, 1999; Mobley, 2015). Mobley (1999) provides the recommendation of collecting radiance measurements at viewing directions of θ = 40° from nadir and ɸ = 135° from the sun to minimize the effects of sun glint and nonuniform sky radiance with a ⍴ value of 0.028 for wind speeds less than 5 m/s. These suggested viewing geometries and ⍴ value from Mobley (1999) have been used to estimate and remove L<sub>SR</sub> in many remote sensing studies (Ruddick et al., 2006; Shang S. et al., 2017; Baek et al., 2019; Kim et al., 2020). *This method should only be used if using a drone sensor that is angled 30-40° from nadir and if wind speed is less than 5 m/s.*

`hedley_method()`
<br/>
Other methods to remove L<sub>SR</sub> include modelling a constant 'ambient' NIR signal that is removed from all pixels. This method relies on two assumptions: 1) The brightness in the NIR is composed only of sun glint and a spatially constant 'ambient' NIR component, and 2) The amount of L<sub>SR</sub> in the visible bands is linearly related to the amount in the NIR band (Hedley et al., 2005). Briefly, the minimum 10% of NIR radiance, min(Lt<sub>NIR</sub>), is calcualted from a random subset of images (number of images is user selected). Next, linear relationships are established between the Lt<sub>NIR</sub> and the visible band values, which would be homogenous if not for the presence of L<sub>SR</sub>. Then, the slope (*b*) of the regressions are used to predict L<sub>SR</sub> for all pixels in the visible bands that would be expected if those pixels had a Lt<sub>NIR</sub> value of min(Lt<sub>NIR</sub>):
<div align="center">
<br/>
Lw<sub>i</sub> = Lt<sub>i</sub> - b<sub>i</sub>(Lt(NIR) - min(Lt<sub>NIR</sub>)), where *i* is each band
<br/>
</div>
  
# Normalizing by downwelling irradiance (L<sub>W</sub> / E<sub>d</sub> =  R<sub>rs</sub>) 
 
After Lsr is removed from Lt, Lw needs to be normalized by Ed to calculate Rrs (Eq. 6). The downwelling light sensor (DLS) or calibration reflectane panel should be used depending on weather conditions. 

<br/>
`dls_ed()`
<br/>
According to MicaSense, the DLS is better at estimating changing light conditions (e.g. variable cloud cover) since it records DLS throughout a flight; however, it is not a perfect measurement due to movement of the drone. However, the the MicaSense function Capture.dls_irradiance() incorporates tilt-compensated DLS values from the onboard orientation sensor. 
  
<br/>
`panel_ed()`
When flying on a clear sunny day or a completely overcast cloudy day, the calibration reflectance panel should be used. This method uses the MicaSense function Capture.panel_irraidiance() which returns a list of mean panel irradiance values. 
<br/> 
  

# Water quality retrievals 
<br/>
R<sub>rs</sub> is often used as input into various bio-optical algorithms to obtain concentrations of optically active water quality constituents such as chlorophyll a or total suspended matter (TSM). Several functions can be applied to calculate concentrations. 
<br/>

`chl_hu()`
<br/>
This is the Ocean Color Index (CI) three-band reflectance difference algorithm (Hu et al. 2012). This should only be used for chlorophyll retrievals below 0.15 mg m^-3. Documentation can be found here https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/. doi:10.1029/2011jc007395
<br/>

`chl_ocx()`
<br/>
This is the OCx algorithm which uses a fourth-order polynomial relationship (O'Reilly et al. 1998). This should be used for chlorophyll retrievals above 0.2 mg m^-3. Documentation can be found here https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/. The coefficients for OC2 (OLI/Landsat 8) are used as default. doi:10.1029/98JC02160.
<br/>

`chl_hu_ocx()`
<br/>
This is the blended NASA chlorophyll algorithm which combines Hu color index (CI) algorithm (chl_hu) and the O'Reilly band ratio OCx algortihm (chl_ocx). This specific code is grabbed from https://github.com/nasa/HyperInSPACE. Documentation can be found here https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/.
<br/>

`chl_gitelson()`
<br/>
This algorithm estimates chlorophyll a concentrations using a 2-band algorithm with coefficients from Gitelson et al. 2007. This algorithm is recommended for coastal (Case 2) waters. doi:10.1016/j.rse.2007.01.016
<br/>

`nechad_tsm()`
<br/>
This algorithm estimates total suspended matter (TSM) concentrations using the Nechad et al. (2010) algorithm. doi:10.1016/j.rse.2009.11.022.
<br/>

# Pixel masking
<br/>
`rrs_pixel_masking()`
<br/>
This function masks pixels based on a user supplied Rrs thresholds in an effort to remove instances of specular sun glint, shadowing, or adjacent land when present in the images. It is designed to be applied to processed Rrs images. 
<br/>

`std_glint_removal_method()`
<br/>
This function masks pixels based on a user supplied NIR threshold in an effort to remove instances of specular sun glint. The mean and standard deviation of NIR values from the first N images is calculated and any pixels containing an NIR value > mean + std x glint_std_factor is masked across all bands. The lower the glint_std_factor, the more pixels will be masked. It is designed to 
<br/>

# Georeferencing and mapping

# Acknowledgements

We acknowledge 

# References
