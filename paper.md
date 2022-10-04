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

# Removal of surface reflected light (L<sub>SR</sub>) 

The inclusion of sun glint and L<sub>SR</sub> can lead to an overestimation of R<sub>rs</sub> and remotely sensed water quality retrievals, as shown in Figure _. `DroneWQ` provides a sun glint masking procedure to remove instances of specular sun glint and three common approaches to remove LSR as described below:

![Caption for example figure.\label{fig:removal_Lsr_fig}](removal_Lsr_fig.jpg)
<br/>
Figure 1. Example of an individual drone image (green band) with different radiometric values: (A) RUAS, (B) RUAS with initial sun glint masking and (C–F) remote sensing reflectance (Rrs) using various methods to remove surface reflected light: (C) ⍴ look-up table (LUT) from HydroLight simulations, (D) Dark pixel assumption with NIR = 0, (E) Dark pixel assumption with NIR >0, (F) Deglingting methods following Hochberg et al. (2003).

`mobley_rho_method()`
<br/>
Tabulated ρ values have been derived from numerical simulations with modelled sea surfaces, Cox and Munk wave states (wind), and viewing geometries (Cox and Munk, 1954; Mobley, 1999; Mobley, 2015). Mobley (1999) provides the recommendation of collecting radiance measurements at viewing directions of θ = 40° from nadir and ɸ = 135° from the sun to minimize the effects of sun glint and nonuniform sky radiance with a ⍴ value of 0.028. These suggested viewing geometries and ⍴ value from Mobley (1999) have been used to estimate and remove L<sub>SR</sub> in many remote sensing studies (Ruddick et al., 2006; Shang S. et al., 2017; Baek et al., 2019; Kim et al., 2020).

`blackpixel_method()`
<br/>
An alternative method to remove L<sub>SR</sub> relies on the so-called black pixel assumption that assumes L<sub>W</sub> in the near infrared (NIR) is negligible due to strong absorption of water. Where this assumption holds, at-sensor radiance measured in the NIR is solely L<sub>SR</sub> (Gordon and Wang, 1994; Siegel et al., 2000) and allows ⍴ to be calculated if L<sub>sky</sub> is known. Studies have used this assumption to estimate and remove L<sub>SR</sub>; however, the assumption tends to fail in more turbid waters where high concentrations of particles enhance backscattering and L<sub>W</sub> in the NIR (Siegel et al., 2000; Lavender et al., 2005).

`hedley_method()`
<br/>
Other methods include removing sun glint and L<sub>sky</sub> by utilization of the NIR band by calculating an 'ambient' NIR brightness level, representing the NIR brightness with no sun glint or LSR (Hochberg et al., 2003; Hedley et al., 2005). A linear relationship between Lt(NIR) and Lt in the visible bands is established, and for each pixel, the slope of this line is multiplied by the difference between the pixel NIR value and the ambient NIR level. 

# Water quality retrievals

# Georeferencing and mapping

# Acknowledgements

We acknowledge 

# References
