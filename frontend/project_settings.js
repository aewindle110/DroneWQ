// projectsettings.js - Project settings state management

// Current project settings
let currentProjectSettings = {
    glintMethod: 'Mobley Rho Method',
    irradianceMethod: 'Panel Ed',
    pixelMasking: 'Value Threshold',
    selectedOutputs: ['chlorophyll-hu', 'tsm'] // Default selected outputs
};

// Output mapping from checkbox labels to chart types
const outputMapping = {
    'Reflectance spectra only': 'reflectance',
    'Chlorophyll-a (Hu Color Index)': 'chlorophyll-hu',
    'Chlorophyll-a (OCx Band Ratio)': 'chlorophyll-ocx',
    'Chlorophyll-a (Blended Hu+OCx)': 'chlorophyll-blended',
    'Chlorophyll-a (Gitelson)': 'chlorophyll-gitelson',
    'Total Suspended Matter (TSM)': 'tsm',
    'Custom Algorithm (load Python function)': 'custom',
    'Generate Mosaics for each metric': 'mosaics'
};

// Initialize settings functionality
function initializeSettings() {
    setupSettingsCheckboxes();
    loadCurrentSettings();
}

// Make functions globally available
window.initializeSettings = initializeSettings;