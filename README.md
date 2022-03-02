# UAS_WQ

# UAS multispectral remote sensing
____ is a Python package that can be used to analyze multispectral data collected from a UAS. These scripts are specific for the MicaSense RedEdge-MX camera. 

This package allows users to 1) calculate remote sensing reflectance, 2) Apply bio-optical algorithms, and 3) georegister and mosaic individual UAS images

## Background:

Remote sensing reflectance (R<sub>rs</sub>) can be defined as:


R<sub>rs</sub>(θ,φ,λ) = L<sub>w</sub>(θ,φ,λ) / E<sub>d</sub>(λ) (1)

where L<sub>w</sub> (W m<sup>-2</sup> nm<sup>-1</sup> sr<sup>-1</sup>) is water-leaving radiance, E<sub>d</sub> (W m<sup>-2</sup> nm<sup>-1</sup>) is downwelling irradiance, θ represents the sensor viewing angle between the sun and the vertical (zenith), ɸ represents the angular direction relative to the sun (azimuth), and λ represents wavelength
  
Like all above-water optical measurements, UAS do not measure R<sub>rs</sub> directly as the at-sensor total radiance (L<sub>t</sub> (W m<sup>-2</sup> nm<sup>-1</sup> sr<sup>-1</sup>)) constitutes the **sum** of L<sub>w</sub> and incident radiance reflected off the sea surface and into the detector's field of view, herein referred to as surface-reflected radiance (L<sub>SR</sub>). 

UAS total reflectance can be defined as:

R<sub>UAS</sub>(θ,φ,λ) = L<sub>t</sub>(θ,φ,λ) / E<sub>d</sub>(λ) (2)

where L<sub>T</sub>(θ,φ,λ) = L<sub>w</sub>(θ,φ,λ) + L<sub>SR</sub>(θ,φ,λ) (3)

If a water surface was perfectly flat, incident light would reflect specularly and could be measured with known viewing geometries. However, most water bodies are not flat as winds and currents create tilting surface wave facets. Due to differing orientation of wave facets reflecting radiance from different parts of the sky, LSR can vary widely within a single image. A common approach tomodel L<sub>SR</sub> is to express it as the product of sky radiance (L<sub>sky</sub>, W m<sup>-2</sup> nm<sup>-1</sup> sr<sup>-1</sup>) and ⍴, the effective sea-surface reflectance of the wave facet (Mobley, 1999; Lee et al., 2010):

L<sub>SR</sub>(θ,Φ,λ) = ρ(θ,Φ,λ)* L<sub>sky</sub>(θ,Φ,λ) (4)

Rearranging Eqs. 3 and 4, ρ can be derived by:

ρ(θ,Φ,λ) = L<sub>T</sub>(θ,Φ,λ) − L<sub>w</sub>(θ,Φ,λ) / L<sub>sky</sub>(θ,Φ,λ) (5)

Given measurements of L<sub>sky</sub>, an accurate determination of ρ is critical to derive R<sub>rs</sub> by:

R<sub>rs</sub>(θ,Φ,λ) = R<sub>UAS</sub>(θ,Φ,λ) − (L<sub>sky</sub>(θ,Φ,λ)* ρ(θ,Φ,λ) / E<sub>d</sub>(λ)) (6)

This 

