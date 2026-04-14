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
    affiliation: 3
    equal_contrib: true
  - name: Alejandro Román
    orcid: 0000-0002-8868-9302
    affiliation: 4
  - name: Sergio Heredia
    orcid: 0009-0003-9495-9625
    affiliation: 4
  - name: Gabriel Navarro
    orcid: 0000-0002-8919-0060
    affiliation: 4
  - name: Temuulen Enkhtamir
    orcid: 0009-0000-1354-0792
    affiliation: 5
  - name: Kurtis Kwan
    affiliation: 5
  - name: Nidhi Khiantani
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
 - name: Department of Ecology and Coastal Management, Institute of Marine Sciences of Andalusia (ICMAN-CSIC), Spanish National Research Council (CSIC), 11519 Puerto Real, Spain
   index: 4
 - name: Duke University, Durham, NC, United States
   index: 5
 - name: Horn Point Laboratory, University of Maryland Center for Environmental Science, Cambridge, MD, United States
   index: 6
 
date: 19 March 2026
bibliography: paper.bib
---

# Summary

Small aerial drones, or unoccupied aerial systems (UAS), conveniently achieve scales of observation between satellite resolutions and in situ sampling, effectively diminishing the “blind spot” between these established measurement techniques [@gray_larsen_johnston_2022]. UAS equipped with off-the-shelf multispectral sensors originally designed for terrestrial applications are being increasingly used to derive water quality properties. Multispectral UAS imagery requires post processing to radiometrically calibrate raw pixel values to useful radiometric units such as reflectance. In aquatic applications, there are additional steps to remove surface reflected light and sun glint, and different approaches to estimate water quality parameters. Georeferencing and mapping UAS imagery over water also comes with challenges since typical structure from motion photogrammetry techniques fail due to lack of feature matching. `DroneWQ` can **1)** convert raw multispectral imagery to total radiance (L<sub>t</sub>) with units of W m<sup>-2</sup> nm<sup>-1</sup> sr<sup>-1</sup>, **2)** remove surface reflected light (L<sub>sr</sub>) to calculate water leaving radiance (L<sub>w</sub>), **3)** measure downwelling irradiance (E<sub>d</sub>) from either the calibrated reflectance panel, downwelling light sensor (DLS), or a combination of the two, **4)** calculate remote sensing reflectance (R<sub>rs</sub>) by dividing E<sub>d</sub> by L<sub>w</sub>, and **5)** mask pixels containing specular sun glint or instances of vegetation, shadowing, etc., **6)** use R<sub>rs</sub> as input into various bio-optical algorithms to derive chlorophyll a and total suspended sediment concentrations, and **7)** georeference using image metadata and sensor specifications to orient and map to a known coordinate system. 

# Statement of need

`DroneWQ` is a Python package for multispectral UAS imagery processing to obtain remote sensing reflectance (R<sub>rs</sub>), the fundamental input into ocean color algorithms which can be used to estimate and map water quality parameters. The processing steps, calibrations, and corrections necessary to obtain research quality R<sub>rs</sub> data from UAS can be prohibitively difficult for those who do not specialize in optics and remote sensing, yet this data can reveal entirely new insight into aquatic ecosystems. `DroneWQ` was designed to be a simple pipeline for those who wish to utilize UAS multispectral remote sensing to analyze ocean color and water quality. The simple functionality of `DroneWQ` will enable effective water quality monitoring at fine spatial resolutions, leading to exciting scientific exploration of UAS remote sensing by students, scientists, and water quality managers. 

# State of the field

Private software and applications exist for UAS post-processing, georeferencing, and mapping (e.g., Pix4D, Agisoft Metashape); however, these tools are primarily designed for terrestrial imagery and often perform poorly over water due to lack of stable features for image matching. The MicaSense company (now EagleNXT) developed a codebase for Python-based image processing of MicaSense RedEdge and Altum imagery (https://github.com/micasense/imageprocessing) which is suitable for basic terrestrial remote sensing.

`DroneWQ` builds upon these workflows to enable the calculation of aquatic remote sensing reflectance and derived water quality parameters. To our knowledge, `DroneWQ` is the first open-source software package that allows users to process raw multispectral UAS imagery into aquatic remote sensing reflectances and water quality metrics relevant to environmental research and management.


# Software design
`DroneWQ` is a modular, object oriented Python package that implements a processing pipeline for transforming raw multispectral UAS imagery into georeferenced remote sensing reflectance and derived water quality products. The software follows a workflow-oriented design in which individual processing steps (data ingestion, radiometric calibration, reflectance retrieval, quality control, bio-optical inversion, georeferencing, and mosaicking) are implemented in reusable classes. This architecture promotes transparency, flexibility, and ease of extension, allowing users to modify or replace individual components without altering the overall pipeline.
A key design feature of `DroneWQ` is the ability to project and georeference imagery, which leverages onboard GPS and orientation metadata to map imagery without relying on conventional structure-from-motion approaches that often fail over water due to limited spatial feature contrast. The package integrates radiometric corrections, glint correction methods, and established ocean color algorithms to produce remote sensing reflectance and water quality products within a unified framework. Configuration is handled through a centralized setup function that manages file paths and processing parameters, supporting reproducible workflows. The software has fairly minimal dependencies and can be integrated into a wide range of development workflows. Here it is demonstrated within a Jupyter notebook, enabling interactive analysis while maintaining reproducibility for batch processing.


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
Figure 2. Final orthomosaic of UAS images collected over Western Lake Erie processed to chlorophyll a concentration.

# Research impact statement

`DroneWQ` has demonstrated growing research impact and community engagement since its initial development. The project has expanded beyond its original authors (@aewindle110; @patrickcgray) to include contributions from four additional developers, reflecting increasing adoption and collaborative development. Community involvement has supported the evolution of the software through feature requests, bug reports, and user feedback submitted via GitHub Issues and direct communication, indicating active use by a broader research community.
`DroneWQ` has been used in multiple peer-reviewed studies focused on UAS aquatic remote sensing and water quality retrievals [@roman_heredia_windle_tovar; @gray_windle_dale_savelyev_johnson_silsbe_larsen_johnston_2022; @windle_silsbe_2021]. These applications demonstrate the utility of the software for advancing research using multispectral UAS imagery in aquatic environments, particularly where traditional processing approaches are limited. As interest in UAS-based water quality monitoring continues to grow, `DroneWQ` provides an open, extensible framework that supports both scientific investigation and applied environmental monitoring.

# AI usage disclosure

The creation of this software was mostly done by humans. AI assisted in identifying and diagnosing bugs, as well as generating docstrings, both of which were thoroughly reviewed by humans.

# Acknowledgements

We acknowledge and appreciate helpful support from the Micasense team. We thank Julian Dale for assisting with UAS flights. 

# References

