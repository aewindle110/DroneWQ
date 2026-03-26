# Installation

## Requirements

> [!IMPORTANT]
> Our code requires system level dependencies `gdal`, `zbar`, `exiftool`, and `opencv`.
> It is the most straightforward to install them through conda-forge.

### Install from PyPI (Recommended)

The easiest way to install DroneWQ is using conda and pip:

First, create your conda environment:
```bash
conda create -n {your project name} python=3.13 exiftool gdal zbar opencv -c conda-forge
```

Then, activate your environemt:

```bash
conda activate {your project name}
```

Finally, install dronewq:
```bash
pip install dronewq
```

### Install from environment.yml

1. Clone the repository or download the [environment.yml](./environment.yml) file.
2. Create a conda environment using the environment.yml file:
```bash
conda env create -f environment.yml
```

3. Activate the environment:
```bash
conda activate dronewq
```

### Install from Source

If you want to install from source:

```bash
git clone https://github.com/aewindle110/DroneWQ.git
cd DroneWQ
conda create -n {your project name} python=3.13 exiftool gdal zbar opencv -c conda-forge
conda activate {your project name}
pip install .
```

### System Requirements

DroneWQ requires Python >=3.10. Some dependencies require additional system libraries which is installed through conda:

- **GDAL**: Required for geospatial operations
- **ExifTool**: Required for reading MicaSense image metadata
- **ZBar**: Required for QR code reading from calibration panels


On Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install gdal-bin libgdal-dev exiftool opencv zbar-tools python3-gdal python3-cartopy
```

> [!IMPORTANT]
> Pip on macOS currently doesn't search through the place homebrew installations go to.
> Thus, you have to specify it using this method https://github.com/npinchot/zbar/issues/3#issuecomment-1038005495

On macOS (using Homebrew):
```bash
brew install gdal exiftool zbar opencv
```

**Note**: We have included a modified version of the MicaSense imageprocessing scripts in this repo. Our modifications include:
- Radiance data type expressed as Float32 instead of Uint16
- Image radiance output in milliwatts (mW) instead of watts (W)
- Modified `capture.save_capture_as_stack()` to not scale and filter data

These modifications impact the `panel_ed` calculation. If MicaSense releases a package with user-specified radiance data types, we will revert to their official package. 


## Quick Start

### Organize Your Data

DroneWQ requires MicaSense images organized in a specific folder structure:

```
<main_directory>/
    ├── panel/              # Calibrated reflectance panel images (before/after flight)
    ├── raw_sky_imgs/       # Sky images (40° from zenith, ~135° azimuth)
    ├── raw_water_imgs/     # Water images from flight
    └── align_img/          # One image capture (5 .tif files) for alignment
```

**Directory descriptions:**
- **panel**: Contains image captures of the MicaSense calibrated reflectance panel
- **raw_sky_imgs**: Contains sky images taken at 40° from zenith and ~135° azimuthal viewing direction
- **raw_water_imgs**: Contains all water images captured during the flight
- **align_img**: Contains one image capture (5 .tif files, one per band) from `raw_water_imgs` used to compute the warp matrix for aligning all images

A sample drone dataset consisting of images collected over western Lake Erie is available on [Zenodo](https://doi.org/10.5281/zenodo.14018788) and is 5.84 GB unzipped. Depending on your computer's speed, you may want to subset the data before running the full workflow. 

### Configure Settings

Before processing, configure the main directory path:

```python
import dronewq

# Configure the main directory containing your organized images
dronewq.configure(main_dir="/path/to/your/main_directory")
```

The `configure()` function automatically sets up all subdirectory paths based on the main directory.

