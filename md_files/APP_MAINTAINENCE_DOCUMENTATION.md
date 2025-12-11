# DroneWQ Maintenance Documentation

**Package:** dronewq  
**PyPI:** https://pypi.org/project/dronewq/  
**Repository:** https://github.com/aewindle110/DroneWQ  
**Current Version:** 0.1.0
**Last Updated:** December 2024  
**Maintainer:** Anna Windle  
**DOI:** https://doi.org/10.5281/zenodo.14018788

---

## Table of Contents

1. [Overview](#overview)
2. [Package Structure](#package-structure)
3. [Development Environment Setup](#development-environment-setup)
4. [Testing](#testing)
5. [PyPi Release Process](#pypi-release-process)
---

## Overview

### Package Purpose

DroneWQ is a Python package for analyzing multispectral data collected from drones to derive ocean color radiometry and water quality properties. The package is specifically designed for MicaSense RedEdge and Altum cameras.

**Primary Use Cases:**
- Converting raw drone imagery to calibrated remote sensing reflectance (Rrs)
- Calculating water quality parameters (chlorophyll-a, total suspended matter)
- Georeferencing and mosaicking drone imagery
- Ocean and coastal water quality monitoring

### Architecture Overview

DroneWQ follows a modular pipeline architecture:
1. **Raw → Lt**: Raw pixel values converted to radiance
2. **Lt → Lw**: Sky reflection removal to get water-leaving radiance
3. **Lw → Rrs**: Normalization by downwelling irradiance
4. **Rrs → Water Quality**: Bio-optical algorithms applied

**Key Processing Methods:**
- Multiple sky glint removal methods (Mobley rho, Hedley, Black pixel)
- Multiple irradiance calculation methods (DLS, Panel, Combined)
- Pixel masking for glint, shadows, and vegetation
- Parallel processing support

### Key Components

- **Core Processing** (`dronewq.core`): Main processing pipeline
- **Water-Leaving Radiance** (`dronewq.lw_methods`): Sky reflection removal methods
- **Downwelling Irradiance** (`dronewq.ed_methods`): Irradiance calculation methods
- **Masking** (`dronewq.masks`): Pixel quality control
- **Water Quality Algorithms** (`dronewq.core.wq_calc`): Bio-optical algorithms
- **Georeferencing** (`dronewq.core.georeference`): Spatial referencing
- **Mosaicking** (`dronewq.core.mosaic`): Image stitching

### Dependencies Overview

**Core Dependencies:**
- **GDAL** (≥3.0): Geospatial operations and raster processing
- **ExifTool**: MicaSense image metadata extraction
- **ZBar**: QR code reading from calibration panels
- **NumPy**: Numerical computations
- **Pandas**: Metadata management
- **Matplotlib**: Visualization
- **Cartopy**: Geospatial plotting


**Development Dependencies:**
- pytest: Testing framework
- pytest-cov: Code coverage

---

## Package Structure

```
DroneWQ/
├── ABOUT.md
├── app
│   ├── app_ui.js
│   ├── backend
│   ├── charts.js
│   ├── csv_handler.js
│   ├── dashboard.js
│   ├── dist
│   ├── image_handler.js
│   ├── main.js
│   ├── mosaic_handler.js
│   ├── node_modules
│   ├── package-lock.json
│   ├── package.json
│   ├── project_settings.js
│   ├── projects.db
│   ├── python
│   ├── trajectory_handler.js
│   ├── upload.js
│   └── wireframes
├── Dockerfile
├── docs
│   ├── make.bat
│   ├── Makefile
│   ├── pre_built_html
│   ├── requirements.txt
│   └── source
├── environment.yml
├── examples
│   └── primary_demo.ipynb
├── figs
│   ├── automatic_flightlines_QGIS.png
│   ├── chl_mosaic.png
│   ├── DroneWQ.png
│   ├── manual_flightlines_QGIS.png
│   ├── OLCI_Rrs_Lake_Erie.png
│   └── removal_Lsr_fig.jpg
├── Lake_Erie
│   ├── align_img
│   ├── automatic_georeferenced_lt_thumbnails_subset
│   ├── dls_ed.csv
│   ├── georeferenced_masked_chl_hu_ocx
│   ├── georeferenced_masked_chl_hu_ocx_imgs
│   ├── lt_imgs
│   ├── lt_thumbnails
│   ├── lt_thumbnails_subset
│   ├── lw_imgs
│   ├── manual_georeferenced_lt_thumbnails_subset
│   ├── masked_chl_gitelson_imgs
│   ├── masked_chl_hu_imgs
│   ├── masked_chl_hu_ocx_imgs
│   ├── masked_chl_ocx_imgs
│   ├── masked_rrs_imgs
│   ├── masked_tsm_nechad_imgs
│   ├── median_rrs_and_wq.csv
│   ├── median_rrs.csv
│   ├── metadata.csv
│   ├── mosaic_chl_hu_ocx
│   ├── panel
│   ├── raw_water_imgs
│   ├── result
│   ├── rrs_hedley_subset
│   └── rrs_imgs
├── LICENSE
├── md_files
│   ├── APP_MAINTAINENCE_DOCUMENTATION.md
│   ├── BACKLOG.md
│   ├── paper.bib
│   ├── paper.md
│   ├── RELEASE_NOTES.md
│   ├── TECHNICAL_DOC_BACKEND.md
│   ├── TECHNICAL_DOCUMENTATION_FRONTEND.md
│   └── USER_DOCUMENTATION.md
├── pyproject.toml
├── README.md
├── src
│   └── dronewq
└── tests
    ├── __init__.py
    ├── __pycache__
    ├── test_geometry.py
    ├── test_georeferencing.py
    ├── test_legacy_geometry.py
    ├── test_legacy_to_pipeline.py
    ├── test_legacy_wqcalc.py
    ├── test_set
    ├── test_utils_high_priority.py
    ├── test_whole_pipeline.py
    ├── test_wq_edge.py
    └── test_wqcalc.py
```

### Important Files

**setup.py / pyproject.toml**  
Build configuration specifying Python 3.8 - 3.12 support and dependencies

**requirements.txt**  
Production dependencies including GDAL, numpy, pandas, matplotlib

**environment.yml**  
Conda environment specification for reproducible setup

**Dockerfile**  
Docker image configuration (clifgray/dronewq:v3) with all dependencies pre-installed

**primary_demo.ipynb**  
Example notebook demonstrating complete workflow with Lake Erie dataset

---

## Development Environment Setup

### Prerequisites

- **Python**: 3.8 - 3.12
- **Git**: For version control
- **System Libraries**:
  - GDAL (geospatial library)
  - ExifTool (metadata extraction)
  - ZBar (QR code reading)

### System Library Installation

**Install from PyPi**
The easiest way to install DroneWQ is through pip.
```bash
pip install dronewq
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install gdal-bin libgdal-dev exiftool zbar-tools python3-gdal python3-cartopy
```

**macOS (Homebrew):**
```bash
brew install gdal exiftool zbar
```

**Windows:**
- Download GDAL from OSGeo4W installer
- Install ExifTool from exiftool.org
- Install ZBar from GitHub releases

### Installation from source

```bash
# Clone repository
git clone https://github.com/aewindle110/DroneWQ.git
cd DroneWQ

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
# OR
pip install -r requirements-dev.txt

# Verify installation
python -c "import dronewq; print(dronewq.__version__)"
```

### Docker Setup

```bash
# Pull Docker image
docker pull clifgray/dronewq:v3

# Launch container with local directory mounted
docker run -it -v ~/DroneWQ_work:/home/jovyan --rm -p 8888:8888 clifgray/dronewq:v3

# Start Jupyter Lab
jupyter lab --allow-root --ip 0.0.0.0 /home/jovyan

# Copy URL to browser (will include token)
```

### Conda Setup

```bash
# Create environment from file
conda env create -f environment.yml

# Activate environment
conda activate dronewq
```

### Testing

```bash
# Run test suite to verify setup
pytest

# Check code coverage as well as running tests for other Python versions
hatch run test:run
```
---

## PyPi Release Process
### Github Trusted Publishing
The PyPi package is already linked to the Github respository, so updating the package should be fairly straightforwards. 

**Step 1**
Update the version in all files, like pyproject.toml, setup.py, or __init__.py

**Step 2**
Create a tag with the name as the version
```bash
git tag v1.2.3

#push tag to Github

git push origin v1.2.3
```
**Step 3**
1. Go to your repository on GitHub
2. Click ***"Releases"*** (right sidebar)
3. Click ***"Draft a new release"***
4. Click ***"Choose a tag"*** → Select `v1.2.3`
5. ***Release title:*** `Version 1.2.3` or `v1.2.3`
6. Check ***"Set as the latest release"*** (usually checked by default)
7. Click ***"Publish release"***

### Manual Publishing
**Step 1**
Package your package using hatch
```bash
hatch build

# upload the built package using twine
twine upload dist/* # or your version name
```
Afterwards, input your PyPi token(please reach out to us if you don't have a token)

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
