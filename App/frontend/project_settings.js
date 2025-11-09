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
    'Reflectance spectra': 'reflectance',
    'Chlorophyll-a (Hu Color Index)': 'chlorophyll-hu',
    'Chlorophyll-a (OCx Band Ratio)': 'chlorophyll-ocx',
    'Chlorophyll-a (Blended Hu+OCx)': 'chlorophyll-blended',
    'Chlorophyll-a (Gitelson)': 'chlorophyll-gitelson',
    'Total Suspended Matter (TSM)': 'tsm',
    'Mosaics': 'mosaics'
};

// Initialize settings functionality
function initializeSettings() {
    setupSettingsCheckboxes();
    loadCurrentSettings();
}

// Make functions globally available
window.initializeSettings = initializeSettings;
window.updateSelectedOutputs = updateSelectedOutputs;
window.applySettingsChanges = applySettingsChanges;
window.getCurrentSettings = getCurrentSettings;

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

// Load current settings into the form
function loadCurrentSettings() {
    // Set checkbox states based on current settings
    const checkboxes = document.querySelectorAll('#settings .checkbox-option input[type="checkbox"]');
    
    checkboxes.forEach(checkbox => {
        const label = checkbox.nextElementSibling.textContent.trim();
        
        // Check boxes based on current settings
        if (outputMapping[label] && currentProjectSettings.selectedOutputs.includes(outputMapping[label])) {
            checkbox.checked = true;
        }
    });
}

// Apply settings changes (called when user clicks "Apply Changes")
function applySettingsChanges() {
    updateSelectedOutputs();
    
    // Filter out mosaics for chart display (mosaics go in Mosaics tab)
    const chartsToShow = currentProjectSettings.selectedOutputs.filter(output => output !== 'mosaics');
    
    // Update charts if we're viewing results
    if (typeof updateChartsFromSettings === 'function') {
        updateChartsFromSettings(chartsToShow);
    }
    
    showNotification('Settings applied successfully! Charts updated.', 'success');
    return currentProjectSettings;
}

// Get current settings
function getCurrentSettings() {
    return currentProjectSettings;
}