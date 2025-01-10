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
  - name: Patrick C. Gray 
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
 
date: 13 November 2024
bibliography: paper.bib
---

# Summary

Small aerial drones, or unoccupied aerial systems (UAS), conveniently achieve scales of observation between satellite resolutions and in situ sampling, effectively diminishing the “blind spot” between these established measurement techniques [@gray_larsen_johnston_2022]. UAS equipped with off-the-shelf multispectral sensors originally designed for terrestrial applications are being increasingly used to derive water quality properties. Multispectral UAS imagery requires post processing to radiometrically calibrate raw pixel values to useful radiometric units such as reflectance. In aquatic applications, there are additional steps to remove surface reflected light and sun glint, and different approaches to estimate water quality parameters. Georeferencing and mapping UAS imagery over water also comes with challenges since typical structure from motion photogrammtey techniques fail due to lack of feature matching. `DroneWQ` can **1)** convert raw multispectral imagery to total radiance (L<sub>t</sub>) with units of W/m<sup>2</sup>/nm/sr, **2)** remove surface reflected light (L<sub>sr</sub>) to calculate water leaving radiance (L<sub>w</sub>), **3)** measure downwelling irradiance (E<sub>d</sub>) from either the calibrated reflectance panel, downwelling light sensor (DLS), or a combination of the two, **4)** calculate remote sensing reflectance (R<sub>rs</sub>) by dividing E<sub>d</sub> by L<sub>w</sub>, and **5)** mask pixels containing specular sun glint or instances of vegetation, shadowing, etc., **6)** use R<sub>rs</sub> as input into various bio-optical algorithms to derive chlorophyll a and total suspended sediment concentrations, and **7)** georeference using image metadata and sensor specifications to orient and map to a known coordinate system. 

# Statement of need

`DroneWQ` is a Python package for multispectral UAS imagery processing to obtain remote sensing reflectance (R<sub>rs</sub>), the fundamental input into ocean color algorithms which can be used to estimate and map water quality parameters. The processing steps, calibrations, and corrections necessary to obtain research quality R<sub>rs</sub> data from UAS can be prohibitively difficult for those who do not specialize in optics and remote sensing, yet this data can reveal entirely new insight into aquatic ecosystems. `DroneWQ` was designed to be a simple pipeline for those who wish to utilize UAS multispectral remote sensing to analyze ocean color and water quality. The simple functionality of `DroneWQ` will enable effective water quality monitoring at fine spatial resolutions, leading to exciting scientific exploration of UAS remote sensing by students, scientists, and water quality managers. 

# Background/Theory

UAS can measure remote sensing reflectance (R<sub>rs</sub>) defined as:

<div align="center">
Eq. 1&nbsp;&nbsp;&nbsp;&nbsp; R<sub>rs</sub> (θ, φ, λ) = L<sub>W</sub>(θ, φ, λ) / E<sub>d</sub>(θ, φ, λ) 
</div>
<br/>

where L<sub>W</sub> (W m<sup>-2</sup> nm<sup>-1</sup> sr<sup>-1</sup>) is water-leaving radiance, E<sub>d</sub> (W m<sup>-2</sup> nm<sup>-1</sup>) is downwelling irradiance, θ represents the sensor viewing angle between the sun and the vertical (zenith), φ represents the angular direction relative to the sun (azimuth) and λ represents wavelength. 

UAS do not measure R<sub>rs</sub> directly as the at-sensor total radiance (L<sub>T</sub>, W m<sup>-2</sup> nm<sup>-1</sup> sr<sup>-1</sup>) constitutes the sum of L<sub>W</sub> and incident radiance reflected off the sea surface into the detector's field of view, referred to as surface reflected radiance (L<sub>SR</sub>). L<sub>W</sub> is the radiance that emanates from the water and contains a spectral shape and magnitude governed by optically active water constituents, while L<sub>SR</sub> is independent of water constituents and instead governed by the water surface reflecting the downwelling light; a familiar example is sun glint. Here we define UAS total reflectance (R<sub>UAS</sub>) as:

<div align="center">
Eq. 2&nbsp;&nbsp;&nbsp;&nbsp; R<sub>UAS</sub>(θ, Φ, λ) = L<sub>T</sub>(θ, Φ, λ) / E<sub>d</sub>(λ)
<br/>
</div>
where
<br/>
<div align="center">
Eq. 3&nbsp;&nbsp;&nbsp;&nbsp; L<sub>T</sub>(θ, Φ, λ) = L<sub>W</sub>(θ, Φ, λ) + L<sub>SR</sub>(θ, Φ, λ)
</div>
<br/>

Due to the differing orientation of wave facets reflecting radiance from different parts of the sky, L<sub>SR</sub> can vary widely within a single UAS image. 'DroneWQ` provides multiple options from the literature for removing L<sub>SR</sub>.

![Caption for example figure.\label{fig:removal_Lsr_fig}](figs/removal_Lsr_fig.jpg)
<br/>
Figure 1. Example of an individual UAS image (green band) at different processing steps and methods: (A) R<sub>UAS</sub>, (B) R<sub>UAS</sub> with initial sun glint masking and (C–F) remote sensing reflectance (R<sub>rs</sub>) using various methods to remove surface reflected light: (C) ⍴ look-up table (LUT) from HydroLight simulations, (D) Dark pixel assumption with NIR = 0, (E) Dark pixel assumption with NIR > 0, (F) Deglingting methods following [@hedley_harborne_mumby_2005]. Figure taken from [@windle_silsbe_2021].

A secondary challenge with aquatic UAS remote sensing is georeferencing and mosaicking imagery. Current photogrammetry techniques (e.g. Structure-from-Motion (SfM)) are not capable of stitching UAS images captured over large bodies of water due to a lack of key points in images of homogenous water surfaces. `DroneWQ` uses sensor pose information to project and mosaick imagery. <br>

![Caption for example figure.\label{fig:chl_mosaic}](figs/chl_mosaic.png)
<br/>
Figure 2. Final orthmosaic of UAS images collected over Western Lake Erie processed to chlorophyll a concentration.

# Publications utilizing `DroneWQ`

Román, A., Heredia, S., Windle, A. E., Tovar-Sánchez, A., & Navarro, G. (2024). Enhancing Georeferencing and Mosaicking Techniques over Water Surfaces with High-Resolution Unmanned Aerial Vehicle (UAV) Imagery. Remote Sensing, 16(2), 290.

Gray, P. C., Windle, A. E., Dale, J., Savelyev, I. B., Johnson, Z. I., Silsbe, G. M., ... & Johnston, D. W. (2022). Robust ocean color from drones: Viewing geometry, sky reflection removal, uncertainty analysis, and a survey of the Gulf Stream front. Limnology and Oceanography: Methods, 20(10), 656-673.

Windle, A. E., & Silsbe, G. M. (2021). Evaluation of unoccupied aircraft system (UAS) remote sensing reflectance retrievals for water quality monitoring in coastal waters. Frontiers in Environmental Science, 9, 674247.

# Acknowledgements

We acknowledge and appreciate helpful support from the Micasense team. We thank Julian Dale for assisting with UAS flights. 

# Contributions 
Contributions are welcome, and they are greatly appreciated! Every little bit helps, and credit will always be given.

Report bugs, request features or submit feedback as a GitHub Issue.
Make fixes, add content or improvements using GitHub Pull Requests

# References

