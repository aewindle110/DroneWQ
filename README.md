# UAS_WQ

# UAS multispectral remote sensing
____ is a Python package that can be used to analyze multispectral data collected from a UAS. These scripts are specific for the MicaSense RedEdge-MX camera. 

This package allows users to 1) calculate remote sensing reflectance, 2) Apply bio-optical algorithms, and 3) georegister and mosaic individual UAS images

Background:

- Remote sensing reflectance (Rrs) can be defined as:

`Rrs(θ,φ,λ) = Lw(θ,φ,λ) / Ed(λ)`

  -where Lw (W m−2nm−1sr−1) is water-leaving radiance, Ed (Wm−2nm−1) is downwelling irradiance, θ represents the sensor viewing angle between the sun and the vertical (zenith), ɸ represents the angular direction relative to the sun (azimuth), and λ represents wavelength
  
- Like all above-water optical measurements, UAS do not measure Rrs directly as the at-sensor total radiance (Lt (W m−2nm−1sr−1)) constitutes the **sum** of Lw and incident radiance reflectedd off the sea surface and into the detector's field of view, herein referred to as surface-reflected radiance (Lsr). 
- UAS total reflectance can be defined as:

`RUAS(θ,φ,λ) = Lt(θ,φ,λ) / Ed(λ)

`Lw(θ,φ,λ) = Lt(θ,φ,λ) - ρ(θ,φ,θ0) * Lsky(θ’,φ,λ,)`
