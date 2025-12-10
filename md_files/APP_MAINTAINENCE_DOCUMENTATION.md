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
├── Dockerfile
├── environment.yml
├── LICENSE
├── pyproject.toml
├── README.md
├── md_files/
│   ├── APP_MAINTENCE_DOCUMENTATION.md
│   ├── BACKLOG.md
│   ├── paper.bib
│   ├── paper.md
│   ├── RELEASE_NOTES.md
│   └── USER_DOCUMENTATION.md
├── app/
│   ├── app.py
│   ├── config.py
│   ├── health.py
│   ├── pipeline.py
│   ├── process.py
│   ├── projects.py
│   ├── result.py
│   └── frontend/
│       ├── app_ui.js
│       ├── charts.js
│       ├── csv_handler.js
│       ├── dashboard.js
│       ├── image_handler.js
│       ├── main.js
│       ├── mosaic_handler.js
│       ├── package.json
│       ├── project_settings.js
│       ├── trajectory_handler.js
│       ├── upload.js
│       └── wireframes/
│           ├── styles.css
│           ├── wireframe-v1.html
│           └── wireframe-v2.html
├── src/
│   ├── dronewq/
│   │   ├── __init__.py
│   │   ├── _version.py
│   │   ├── core/
│   │   │   ├── raw_to_rss.py
│   │   │   ├── wq_calc.py
│   │   │   ├── georeference.py
│   │   │   ├── geometry.py
│   │   │   ├── mosaic.py
│   │   │   ├── mosaic_methods.py
│   │   │   └── plot_map.py
│   │   ├── lw_methods/     # mobley_rho, hedley, blackpixel
│   │   ├── ed_methods/     # dls_ed, panel_ed
│   │   ├── masks/          # threshold_masking, std_masking
│   │   └── utils/          # settings, images, metadata
│   └── micasense/
│       ├── capture.py
│       ├── dls.py
│       ├── image.py
│       ├── imageset.py
│       ├── imageutils.py
│       ├── metadata.py
│       ├── panel.py
│       ├── plotutils.py
│       └── utils.py
├── models/
│   └── model_project.py
├── tests/
│   ├── test_geometry.py
│   ├── test_georeferencing.py
│   ├── test_legacy_geometry.py
│   ├── test_legacy_to_pipeline.py
│   ├── test_legacy_wqcalc.py
│   ├── test_lw_blackpixel.py
│   ├── test_lw_hedly.py
│   ├── test_mobley_rho.py
│   ├── test_std_masking.py
│   ├── test_threshholdmasking.py
│   ├── test_utils_high_priority.py
│   ├── test_whole_pipeline.py
│   ├── test_wq_edge.py
│   ├── test_wqcalc.py
│   └── test_set/           # sample test data and folders
│       └── (sample data folders)
├── docs/
│   ├── source/
│   └── pre_built_html/
├── figs/
│   ├── DroneWQ.png
│   └── chl_mosaic.png
├── docker/
│   └── Dockerfile
└──  requirements.txt
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
