# DroneWQ User Guide
**Measuring Water Quality with Your Drone**

**Version:** 0.1.0
**Last Updated:** December 2025 
**Intended Audience:** Environmental scientists, citizen scientists, water quality monitors

---

## Table of Contents

1. [Welcome](#welcome)
2. [What You'll Need](#what-you-need)
3. [Getting Started](#getting-started)
4. [Organizing Your Photos](#organizing-your-photos)
5. [Processing Your Images](#processing-your-images)
6. [Analyzing Water Quality](#analyzing-water-quality)
7. [Creating Maps](#creating-maps)
8. [Troubleshooting](#troubleshooting)
9. [Getting Help](#getting-help)
10. [Simple Terms Explained](#simple-terms-explained)

---

## Welcome

Welcome to DroneWQ! This guide will help you turn photos from your drone into useful water quality information.

**What is DroneWQ?**

DroneWQ is a tool that analyzes photos taken by special cameras on drones to measure water quality. It can tell you things like how much algae (chlorophyll) is in the water or how murky the water is.

**Who is this guide for?**

This guide is for anyone who wants to monitor water quality using a drone, even if you've never written computer code before. If you can fly a drone and follow step-by-step instructions, you can use DroneWQ!

**What can DroneWQ measure?**

- Amount of algae in the water (chlorophyll levels)
- Water clarity (how murky or clear the water is)
- Suspended particles in the water

---

## What You'll Need

### Required Equipment

Before you begin, make sure you have:

- [ ] A drone with a **MicaSense RedEdge or Altum camera**
- [ ] A **calibrated reflectance panel**
- [ ] A computer with at least 8GB of memory
- [ ] Photos from your drone flight already copied to your computer

### Required Software

- [ ] Python 3.8 to 3.12
- [ ] DroneWQ software


---

## Getting Started

### Option 1: Easy Installation (Recommended for Beginners)

The simplest way to install DroneWQ uses a tool called "pip" that comes with Python.

1. **Open your command prompt or terminal**
   - Windows: Search for "Command Prompt" in the start menu
   - Mac: Search for "Terminal" in Spotlight

2. **Type this command and press Enter:**
   ```
   pip install dronewq
   ```

3. **Wait for installation to complete**  
   You'll see text scrolling by. When it stops and you see a new prompt, you're done!

---

### Option 2: Using Docker (Best for Consistency)

Docker is like a pre-packaged container that has everything you need already set up.

1. **Install Docker** from https://docs.docker.com/

2. **Open your command prompt or terminal**

3. **Type this command** (replace `<your-folder>` with where you want to save your work):
   ```
   docker run -it -v <your-folder>:/home/jovyan --rm -p 8888:8888 clifgray/dronewq:v3
   ```

4. **Start the workspace** by typing:
   ```
   jupyter lab --allow-root --ip 0.0.0.0 /home/jovyan
   ```

5. **Copy the web address that appears** into your browser

---

## Organizing Your Photos

DroneWQ needs your photos organized in a specific way, like organizing files in different folders.

### Create This Folder Structure

On your computer, create one main folder (call it whatever you want, like "Lake_Survey_2024"), then inside it create these four folders:

```
Lake_Survey_2024/
    ├── panel/              
    ├── raw_sky_imgs/       
    ├── raw_water_imgs/     
    └── align_img/          
```

### What Goes Where?

**panel/** - Photos of the white calibration panel  
Put photos of the special white board here. You should take these before and after your flight.

**raw_sky_imgs/** - Photos of the sky  
Put photos taken pointing at the sky here (at a 40-degree angle, looking away from the sun at about 135 degrees).

**raw_water_imgs/** - Photos of the water  
Put all your regular water photos from your flight here.

**align_img/** - One set of sample photos  
Copy just one set of photos (5 images) from your water photos here. This helps the software align all your images properly.

---

## Processing Your Images

Now we'll turn your raw photos into useful water quality data!

### Step 1: Tell DroneWQ Where Your Files Are

Open Python and type these commands:

```python
import dronewq

# Replace the path below with your actual folder location
dronewq.configure(main_dir="/Users/yourname/Lake_Survey_2024")
```

---

### Step 2: Convert Photos to Water Quality Measurements

This is where the magic happens! Type this command:

```python
dronewq.process_raw_to_rrs(
    output_csv_path="/Users/yourname/Lake_Survey_2024/results.csv",
    lw_method="mobley_rho_method",
    ed_method="dls_ed",
    mask_pixels=True,
    nir_threshold=0.01,
    green_threshold=0.005,
    num_workers=4
)
```

**What's happening?** DroneWQ is doing several things:
1. Reading the raw numbers from each photo
2. Removing reflections from the sky (glare)
3. Adjusting for the amount of sunlight
4. Removing pixels that show glare, shadows, or vegetation
5. Calculating how the water reflects light

**Settings explained:**
- `output_csv_path` - Where to save your results spreadsheet
- `mask_pixels=True` - Remove bad pixels (glare, shadows)
- `nir_threshold=0.01` - How sensitive to be when detecting glare
- `green_threshold=0.005` - How sensitive to be when detecting shadows
- `num_workers=4` - How many photos to process at once (use 4 for most computers)

**How long will this take?** Depends on how many photos you have. For 100 photos, expect 10-30 minutes.

---

## Analyzing Water Quality

Once your images are processed, you can calculate specific water quality measurements.

### Measuring Chlorophyll (Algae Levels)

Chlorophyll indicates how much algae is in the water. Type this command:

```python
dronewq.save_wq_imgs(
    wq_alg="chl_gitelson",
    num_workers=4
)
```

**What's happening?** DroneWQ looks at how green the water appears in your images and calculates chlorophyll concentration.

### Which Algorithm Should I Use?

**For most coastal and lake waters:**
- `wq_alg="chl_gitelson"` ← Use this one!

**For very clear ocean water (low algae):**
- `wq_alg="chl_hu"`

**For water with lots of algae:**
- `wq_alg="chl_ocx"`

**For measuring water clarity (murkiness):**
- `wq_alg="nechad_tsm"`

> **Default:** If you're not sure, start with `chl_gitelson`.

---

## Creating Maps

Now let's create a map showing your water quality measurements!

### Step 1: Load Your Results

```python
import pandas as pd

# Load the results file we created earlier
metadata = pd.read_csv("/Users/yourname/Lake_Survey_2024/results.csv")
```

---

### Step 2: Calculate Flight Path

This helps align all your photos correctly:

```python
flight_lines = dronewq.compute_flight_lines(
    captures_yaw=metadata['Yaw'].values,
    altitude=metadata['Altitude'].values[0],
    pitch=0,
    roll=0
)
```

**What's happening?** DroneWQ figures out the path your drone flew based on its heading and altitude.

---

### Step 3: Add Location Information to Each Photo

```python
dronewq.georeference(
    metadata=metadata,
    input_dir=dronewq.settings.rrs_dir,
    output_dir="/Users/yourname/Lake_Survey_2024/georeferenced/",
    lines=flight_lines
)
```

**What's happening?** Each photo is tagged with its GPS location so they can be combined into a map.

---

### Step 4: Create Your Final Map

```python
dronewq.mosaic(
    input_dir="/Users/yourname/Lake_Survey_2024/georeferenced/",
    output_path="/Users/yourname/Lake_Survey_2024/final_map.tif"
)
```

**What's happening?** All your individual photos are stitched together into one complete map!

**What to expect:** You'll have a file called `final_map.tif` that you can open in mapping software like QGIS or ArcGIS to visualize your water quality data.

---

### Can I use DroneWQ with other drone cameras?

Currently, DroneWQ only works with MicaSense RedEdge and Altum cameras. These cameras capture special wavelengths of light needed for water quality analysis.

---

## Troubleshooting

### Problem: Processing is very slow

**What's happening:** Your computer might be processing too many photos at once.

**How to fix it:**
1. Reduce `num_workers` from 4 to 2 or 1
2. Process photos in smaller batches using the `start` and `count` options
3. Close other programs to free up memory

---

### Problem: Out of memory errors

**What's happening:** Your computer doesn't have enough RAM.

**How to fix it:**
1. Process fewer photos at a time using `start` and `count` parameters
2. Reduce `num_workers` to 1
3. Close other applications
4. Consider using a computer with more memory

---

## Getting Help

### Documentation and Tutorials

For more detailed information:
- **Complete documentation:** https://dronewq.readthedocs.io/
- **Example tutorial:** Look for `primary_demo.ipynb` in the DroneWQ examples
- **Sample data to practice with:** Download from https://doi.org/10.5281/zenodo.14018788

### Contact Support

If you need additional assistance:
- **GitHub Issues:** Report bugs or ask questions at https://github.com/aewindle110/DroneWQ/issues
- **Email the developers:** Contact information available on the GitHub repository

### Additional Information

Román, A., Heredia, S., Windle, A. E., Tovar-Sánchez, A., & Navarro, G., 2024. Enhancing Georeferencing and Mosaicking Techniques over Water Surfaces with High-Resolution Unmanned Aerial Vehicle (UAV) Imagery. Remote Sensing, 16(2), 290. https://doi.org/10.3390/rs16020290

Gray, P.C., Windle, A.E., Dale, J., Savelyev, I.B., Johnson, Z.I., Silsbe, G.M., Larsen, G.D. and Johnston, D.W., 2022. Robust ocean color from drones: Viewing geometry, sky reflection removal, uncertainty analysis, and a survey of the Gulf Stream front. Limnology and Oceanography: Methods. https://doi.org/10.1002/lom3.10511

Windle, A.E. and Silsbe, G.M., 2021. Evaluation of unoccupied aircraft system (UAS) remote sensing reflectance retrievals for water quality monitoring in coastal waters. Frontiers in Environmental Science, p.182. https://doi.org/10.3389/fenvs.2021.674247

---

## Simple Terms Explained

**Algorithm**  
A set of mathematical steps the computer follows to calculate something, like a recipe.

**Band**  
One specific color or type of light. The MicaSense camera captures 5 different bands (like 5 different color filters).

**Calibration Panel**  
A special white board with known reflectance properties used to make accurate measurements.

**Capture**  
One snapshot from the drone. Creates 5 separate image files (one per band).

**Chlorophyll**  
The green pigment in algae and plants. Higher chlorophyll means more algae in the water.

**Georeferencing**  
Adding GPS location information to each photo so they can be placed on a map.

**Glint / Sky Reflection**  
Sunlight reflecting off the water surface, creating glare that interferes with measurements.

**Masking**  
Identifying and removing "bad" pixels that show glare, shadows, vegetation, or other unwanted features.

**Mosaic / Orthomosaic**  
Multiple photos stitched together to create one large map.

**Multispectral**  
Capturing multiple wavelengths of light beyond what human eyes can see.

**NIR (Near-Infrared)**  
A type of light humans can't see. Useful for detecting vegetation and water surface glare.

**Radiance**  
The amount of light coming from the water, measured by the camera.

**Reflectance**  
How much light the water reflects back. Different water conditions reflect light differently.

**Remote Sensing**  
Measuring something from a distance (like using a drone instead of being in a boat).

**Rrs (Remote Sensing Reflectance)**  
A standardized way to measure how water reflects light, accounting for viewing angle and sunlight.

**Total Suspended Matter (TSM)**  
Small particles floating in the water that make it cloudy or murky.

**Water-Leaving Radiance**  
Light coming from the water itself (after removing sky reflections and glare).

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
