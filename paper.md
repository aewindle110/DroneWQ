---
title: 'UAS_WQ: A Python package for processing MicaSense multispectral drone imagery for aquatic remote sensing'
tags:
  - Python
  - UAS
  - drone
  - remote sensing
  - water quality
authors:
  - name: Anna E. Windle^[Corresponding author]  # note this makes a footnote saying 'Corresponding author'
    orcid: 0000-0000-0000-0000
    affiliation: 1 # 
  - name: Patrick Gray 
  - orcid: 0000-0000-0000-0000
    affiliation: 2
  - name: Greg M. Silsbe
    affiliation: 1
affiliations:
 - name: Horn Point Laboratory, University of Maryland Center for Environmental Science, Cambridge, MD, United States
   index: 1
 - name:  Division of Marine Science and Conservation, Nicholas School of the Environment, Duke University Marine Laboratory, Beaufort, NC, United States
   index: 2
date: 16 March 2022
bibliography: paper.bib

# Optional fields if submitting to a AAS journal too, see this blog post:
# https://blog.joss.theoj.org/2018/12/a-new-collaboration-with-aas-publishing
aas-doi: 10.3847/xxxxx <- update this with the DOI from AAS once you know it.
aas-journal: Astrophysical Journal <- The name of the AAS journal.
---

# Summary

Small aerial drones conveniently achieve scales of observation between satellite 
resolutions and in- situ sampling, and effectively diminish the “blind spot” between 
these established measurement techniques. Drones equipped with off-the-shelf multispectral
sensors originally designed for terrestrial applications are being increasingly used to 
derive water quality in water bodies. Drone imagery requires post processing to radiometrically
calibrate raw pixel values and obtain useful reflectance measurements. Accounting  
for sun glint and reflected skylight remain obstacles as well as georeferencing and mosaicking
individual drone images. 


# Statement of need

`UAS_WQ` is a Python package for drone imagery processing for effective water quality monitoring. 
`UAS_WQ` was designed to be used by managers, researchers, and students who wish to utilize drone 
multispectral remote sensing to analyze water quality. The combination of processing, georeferencing, 
and mapping drone imagery will enable effective water quality monitoring at fine spatial resolutions.
The simple functionality of `UAS_WQ` will enable exciting scientific exploration of drone remote sensing 
by students and experts alike. 


# Mathematics

Single dollars ($) are required for inline mathematics e.g. $f(x) = e^{\pi/x}$

Double dollars make self-standing equations:

$$\Theta(x) = \left\{\begin{array}{l}
0\textrm{ if } x < 0\cr
1\textrm{ else}
\end{array}\right.$$

You can also use plain \LaTeX for equations
\begin{equation}\label{eq:fourier}
\hat f(\omega) = \int_{-\infty}^{\infty} f(x) e^{i\omega x} dx
\end{equation}
and refer to \autoref{eq:fourier} from text.

# Citations

Citations to entries in paper.bib should be in
[rMarkdown](http://rmarkdown.rstudio.com/authoring_bibliographies_and_citations.html)
format.

If you want to cite a software repository URL (e.g. something on GitHub without a preferred
citation) then you can do it with the example BibTeX entry below for @fidgit.

For a quick reference, the following citation commands can be used:
- `@author:2001`  ->  "Author et al. (2001)"
- `[@author:2001]` -> "(Author et al., 2001)"
- `[@author1:2001; @author2:2001]` -> "(Author1 et al., 2001; Author2 et al., 2002)"

# Figures

Figures can be included like this:
![Caption for example figure.\label{fig:example}](figure.png)
and referenced from text using \autoref{fig:example}.

Figure sizes can be customized by adding an optional second parameter:
![Caption for example figure.](figure.png){ width=20% }

# Acknowledgements

We acknowledge contributions from Brigitta Sipocz, Syrtis Major, and Semyeong
Oh, and support from Kathryn Johnston during the genesis of this project.

# References
