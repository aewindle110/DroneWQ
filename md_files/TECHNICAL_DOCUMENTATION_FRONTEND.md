# DroneWQ Frontend Documentation
---

## Table of Contents

1. [Overview](#overview)
2. [File Structure](#file-structure)
3. [Core JavaScript Modules](#core-javascript-modules)
4. [User Flow](#user-flow)
5. [API Integration](#api-integration)
6. [Development Setup](#development-setup)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### Purpose

The DroneWQ frontend is an Electron-based desktop application that provides a graphical interface for processing and analyzing multispectral drone imagery for water quality assessment. It connects to a Flask backend that handles the computational processing using the DroneWQ Python package.

### Key Features

- **Project Management**: Create, open, and manage water quality analysis projects
- **Data Upload**: Easy folder selection with automatic structure validation
- **Processing Configuration**: User selection of sky glint correction, irradiance methods, and masking parameters
- **Real-time Results**: Visualization of radiometry plots, water quality maps, and trajectory data
- **CSV Data Tables**: Interactive table views
- **Mosaic Generation**: Create georeferenced mosaics with adjustable parameters

### Technology Stack

- **Electron**: Desktop application framework 
- **JavaScript**: No additional frameworks or libraries 
- **Node.js**: File system access, path manipulation
- **Flask API**: Backend communication (REST)
- **HTML5/CSS3**: Modern, accessible UI

---

### Communication Flow

1. **User Interaction** → JavaScript event handlers
2. **Data Collection** → Form inputs, file selections
3. **API Request** → `fetch()` to Flask backend (`localhost:8889`)
4. **Backend Processing** → DroneWQ Python package
5. **Result Storage** → Files written to project folder
6. **Frontend Update** → JavaScript reads files and updates UI

---

## File Structure

```
app/frontend/
├── main.js                 # Electron main process
├── wireframes/
│   ├── wireframe-v2.html  # Main UI structure
│   └── styles.css          # Application styles
├── app_ui.js               # Navigation and core UI logic
├── dashboard.js            # Project dashboard
├── upload.js               # File/folder selection
├── project_settings.js     # Processing configuration for project settings
├── charts.js               # Plot visualization
├── csv_handler.js          # CSV data tables
├── image_handler.js        # Image gallery
├── trajectory_handler.js   # Flight path display
├── mosaic_handler.js       # Mosaic generation
└── package.json            # Node dependencies
```

---

## Core JavaScript Modules

### `main.js`
**Electron Main Process**

**Purpose**: Manages the Electron application window, spawns the Flask backend, and handles inter-process communication (IPC).

**Key Functions**:
- `startFlask()` - Spawns Python Flask process on port 8889
- `waitForBackend()` - Polls `/health` endpoint until backend is ready  
- `createWindow()` - Creates main browser window with dev tools
- IPC handlers for file/folder dialogs

---

### `app_ui.js`
**Core Navigation & UI Controller**

**Purpose**: Central navigation hub that manages screen transitions and coordinates between different modules.

**Screen Flow**:
```
home → project-name → upload → method → outputs → results
                                                   ↓
                                                  settings
```

**Key Functions**:

#### `navigate(screen, fromScreen)`
Switches between application screens.

**Special Cases**:
- **home**: Clears project data only when NOT coming from results (preserves back navigation)
- **results**: Most complex - loads project from backend, initializes all visualization modules


### navigate('results'); // Loads project data, charts, CSV, images, trajectory, mosaics


#### Settings Management
- `openProjectSettings()` - Loads settings for current project
- `applySettingsChanges()` - Saves changes and triggers reprocessing
- `loadSettingsScreen()` - Populates all form fields with project data
---

### `dashboard.js`
**Project Dashboard & Management**

**Purpose**: Displays list of all projects, handles project operations (open, delete, settings).

**Key Functions**:

#### `initializeDashboard()`
Loads projects from backend and renders the table.

#### `renderProjects(projectsToRender)`
Generates HTML table rows with:
- Project name (clickable link to results)
- Processing method
- Data source (with tooltip showing full path)
- Creation date
- Three-dot menu (Settings, Find in Folder, Delete)

#### Project Operations
- `viewProjectResults(projectId)` - Stores ID in sessionStorage, navigates to results
- `showDeleteModal(projectId)` - Confirmation dialog before deletion
- `confirmDeleteProject()` - DELETE request to backend, updates UI
- `findProjectInFolder(projectId)` - Opens result folder in system file browser

**API Endpoints**:
- `GET /api/projects` - Fetch all projects
- `DELETE /api/projects/{id}/delete` - Delete project

---

### `upload.js`
**File & Folder Selection**

**Purpose**: Two-screen workflow for project name input and data folder selection.

**Screen 1: Project Name**

#### `initializeProjectName()`
Sets up project name input with validation:
- Checks if name already exists in backend
- Auto-appends suffix (-1, -2, etc.) if duplicate
- Enables/disables Next button based on input

**Screen 2: Folder Selection**

#### `initializeUpload()`
Folder selection with backend validation:

1. User clicks "Select Folder" → Opens native dialog via IPC
2. Backend validates folder structure (checks for required subdirectories)
3. If valid → saves to sessionStorage, enables Next button
4. If invalid → shows error, user must select different folder

**Required Folder Structure**:
```
project_folder/
├── panel/              # Calibration panel images
├── raw_sky_imgs/       # Sky reference images
├── raw_water_imgs/     # Water images
└── align_img/          # Alignment sample (5 images)
```

**API Endpoint**:
- `POST /api/projects/check_folder` - Validates folder structure

---

### `project_settings.js`
**Processing Configuration**

**Purpose**: Collects processing parameters and triggers backend processing.

**Configuration Screens**:

1. **Method Selection**: Sky glint removal + Irradiance normalization
2. **Outputs**: Water quality algorithms 

#### `setupMethodValidation()`
Enforces required selections before proceeding:
- Red border appears on empty dropdowns
- Alert if user tries to continue without selections
- Resets borders when user makes selection

**Available Methods**:

**Sky Glint Removal**:
- `mobley_rho` - Mobley rho method 
- `hedley` - Hedley method
- `blackpixel` - Black pixel method

**Irradiance**:
- `dls_ed` - Downwelling Light Sensor
- `panel_ed` - Calibration panel
- `combined` - DLS + Panel

**Masking** (optional):
- `value_threshold` - NIR/Green thresholds
- `std_threshold` - Standard deviation

#### `submitProcessing()`
Main processing workflow:

1. Collect all settings from forms
2. Validate required fields
3. POST to `/api/projects/new` (saves settings)
4. GET `/api/process/new/{projectId}` (triggers processing)
5. Navigate to loading screen
6. Poll backend or wait for completion
7. Navigate to results

#### `applySettingsChanges()`
Updates existing project settings:
- Used from Settings screen to modify algorithms
- Triggers WQ-only reprocessing (faster than full reprocess)
- Preserves radiometry, only regenerates selected WQ plots

**API Endpoints**:
- `POST /api/projects/new` - Create new project
- `GET /api/process/new/{id}` - Process new project
- `POST /api/projects/update` - Update settings
- `GET /api/process/updated/{id}` - Reprocess with new settings

---

### `charts.js` 
**Visualization & Plot Management**

**Purpose**: Loads and displays all plots generated by the backend.

#### `buildOverviewFromFolder(folderPath, selectedWQAlgs)`
Main visualization builder:

**Always Displayed (Radiometry)**:
- `rrs_plot.png` - Remote sensing reflectance spectra
- `masked_rrs_plot.png` - Masked Rrs (glint/artifacts removed)
- `lt_plot.png` - Total radiance
- `ed_plot.png` - Downwelling irradiance

**Conditional (Water Quality)**:
- `chl_hu_plot.png` - Chlorophyll (Hu Color Index)
- `chl_ocx_plot.png` - Chlorophyll (OCx Band Ratio)
- `chl_hu_ocx_plot.png` - Chlorophyll (Blended)
- `chl_gitelson_plot.png` - Chlorophyll (Gitelson)
- `tsm_nechad_plot.png` - Total Suspended Matter

**Dynamic Features**:
- Only shows WQ plots for selected algorithms
- Each plot is clickable → opens full-size modal
- Keyboard navigation support (Tab, Enter, Escape)

#### `addCard(title, fileName, blurb, container, plotKey)`
Creates individual plot cards with:
- Image thumbnail
- Title and description
- Min/Max value inputs (for WQ plots only)
- Click to enlarge

#### `updateWQCharts(selectedWQAlgs)`
Regenerates WQ plots with custom value ranges:

1. Collects vmin/vmax from input fields
2. POST to `/api/plot/wq` with parameters
3. Backend regenerates plots
---

### `csv_handler.js`
**CSV Data Tables**

**Purpose**: Displays CSV files generated during processing as interactive tables.

**Supported Files**:
- `metadata.csv` - Image metadata (GPS, altitude, yaw, etc.)
- `median_rrs.csv` - Median Rrs values per image
- `median_rrs_and_wq.csv` - Rrs + water quality results
- `dls_ed.csv` - Downwelling irradiance measurements

#### `loadCSVData(folderPath)`
Scans project folder for CSV files and creates cards:

**Card Display**:
- File title
- Row count
- Column count
- File size
- "View" button → Opens modal with table
- "Show in Folder" button → Opens in file browser

**Accessibility**:
- Escape key closes modal
- Click outside closes modal
- Keyboard-navigable table

---

### `image_handler.js`
**Image Gallery**

**Purpose**: Displays all thumbnail images from the `lt_thumbnails/` folder.

#### `loadImages(folderPath)`
Grid gallery with ALL images:

**Why lt_thumbnails?**
Backend generates thumbnail versions of all Lt (total radiance) images for faster loading in the UI.

---

### `trajectory_handler.js`
**Flight Path Visualization**

**Purpose**: Displays flight metadata and trajectory plot.

#### `loadTrajectoryData(folderPath)`
Loads two components:

1. **Flight Data Summary** (from `metadata.csv`):
   - Altitude range
   - Latitude range
   - Longitude range
   - Yaw range
   - Total image count

2. **Flight Plan Image** (`result/flight_plan.png`):
   - 3-subplot figure generated by backend
   - Altitude vs time
   - Lat/Long scatter
   - Yaw vs time

---

### `mosaic_handler.js`
**Mosaic Generation**

**Purpose**: Interface for creating georeferenced water quality mosaics.

#### `processMosaic()`
Mosaic generation workflow:

**User Inputs**:
- Water quality algorithm (checkbox - only one)
- Even yaw angle (degrees, optional)
- Odd yaw angle (degrees, optional)
- Altitude (meters, required)
- Pitch (degrees, default 0)
- Roll (degrees, default 0)
- Method (mean/first/min/max)
- Downsample factor (1 = no downsampling)

**Processing Steps**:
1. Validate inputs
2. POST to `/api/process/mosaic`
3. Backend creates mosaic
5. Saves PNG to `result/` folder
6. Frontend displays mosaic card

#### `renderMosaicCards()`
Scans result folder for mosaic files:
- Looks for files containing `mosaic` and ending in `.png`
- Creates clickable cards
- Distinguishes between original and downsampled versions

**File Naming Convention**:
- `mosaic_chl_hu.png` - Original resolution
- `mosaic_chl_hu_downsampled_2.png` - Downsampled by factor of 2

**Why Downsampling?**
Large mosaics can be 100+ MB. Downsampling reduces file size for easier visualization while preserving spatial patterns.

---

## User Flow

### Complete Workflow

```
1. Launch Application
   ↓
2. Dashboard (View Existing Projects)
   ↓
3a. Open Existing Project → Results Screen
   OR
3b. Create New Project:
       ↓
    4. Enter Project Name
       ↓
    5. Select Data Folder
       ↓
    6. Choose Processing Methods
       - Sky Glint Removal
       - Irradiance Normalization
       - Masking (optional)
       ↓
    7. Select Output Algorithms
       - Chlorophyll algorithms
       - TSM
       - Mosaics
       ↓
    8. Processing (Loading Screen)
       Backend processes images
       ↓
    9. Results Screen
       - Overview Tab: Plots
       - Table Data Tab: CSV files
       - Images Tab: Image gallery
       - Trajectory Tab: Flight path
       - Mosaics Tab: Generate mosaics
       ↓
   10. Settings (Optional)
       Modify algorithms, reprocess
```

### Session Management

**SessionStorage Keys**:
- `currentProjectId` - Active project ID
- `projectFolder` - Project folder path
- `projectName` - Project name
- `selectedWQAlgs` - Selected algorithms (JSON array)
- `mosaic` 

---

## API Integration

### Backend URL
```javascript
const BACKEND_URL = "http://localhost:8889";
```

### API Endpoints

#### Projects
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/projects` | List all projects |
| GET | `/api/projects/{id}` | Get project details |
| POST | `/api/projects/new` | Create new project |
| POST | `/api/projects/update` | Update project settings |
| POST | `/api/projects/check_folder` | Validate folder structure |
| DELETE | `/api/projects/{id}/delete` | Delete project |

#### Processing
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/process/new/{id}` | Process new project |
| GET | `/api/process/updated/{id}` | Reprocess with new settings |
| POST | `/api/process/mosaic` | Generate mosaic |
| POST | `/api/plot/wq` | Regenerate WQ plots |

#### Health Check
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Check if backend is ready |

### Error Handling

---

## Development Setup

### Prerequisites

- Node.js 16+ and npm
- Python 3.8-3.12
- DroneWQ Python package installed
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/aewindle110/DroneWQ.git
cd DroneWQ/app/frontend

# Install Node dependencies
npm install

# Start development
npm start
```
## Testing

### Manual Testing Checklist

**Dashboard**:
- Projects load from backend
- Search filters projects
- Three-dot menu opens/closes
- Delete modal confirms before deletion
- Find in Folder opens correct directory

**Project Creation**:
- Project name validation works
- Duplicate names get auto-suffix
- Folder selection opens native dialog
- Invalid folder shows error
- Valid folder enables Next button

**Processing**:
- Method dropdowns validate
- Output checkboxes work
- Loading screen appears
- Results load after processing
- Error messages display clearly

**Results**:
- All plots load correctly
- CSV tables display data
- Images load in gallery
- Trajectory data shows
- Modal views work
- Keyboard navigation functions

**Mosaics**:
- Mosaic form validates
- Processing completes
- Mosaic displays in card
- Downsampling works

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.