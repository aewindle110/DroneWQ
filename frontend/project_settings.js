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
window.updateSelectedOutputs = updateSelectedOutputs;

// Set up checkbox event listeners
function setupSettingsCheckboxes() {
    const checkboxes = document.querySelectorAll('#settings .checkbox-option input[type="checkbox"]');
    
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateSelectedOutputs();
        });
    });
}

// Update selected outputs based on checkboxes
function updateSelectedOutputs() {
    const selectedOutputs = [];
    const checkboxes = document.querySelectorAll('#settings .checkbox-option input[type="checkbox"]:checked');
    
    checkboxes.forEach(checkbox => {
        const label = checkbox.nextElementSibling.textContent.trim();
        
        // Map checkbox labels to output types using our mapping
        if (outputMapping[label]) {
            selectedOutputs.push(outputMapping[label]);
        }
    });
    
    currentProjectSettings.selectedOutputs = selectedOutputs;
    console.log('Updated outputs:', selectedOutputs);
}