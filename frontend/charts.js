// charts.js - Chart interactions and modal functionality

// Track which charts should be displayed based on project settings
let selectedOutputs = [
    'reflectance', 
    'chlorophyll-hu', 
    'chlorophyll-ocx', 
    'tsm'
]; // Default for demo

// Initialize chart functionality
function initializeCharts() {
    setupChartClickHandlers();
    renderChartsBasedOnOutputs();
}

// Set up click handlers for chart expansion
function setupChartClickHandlers() {
    document.querySelectorAll('.chart-container img').forEach(img => {
        img.style.cursor = 'pointer';
        img.addEventListener('click', function() {
            openChartModal(this);
        });
    });
}

// Make functions globally available
window.initializeCharts = initializeCharts;