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
    addExportButtons();
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
window.updateChartsFromSettings = updateChartsFromSettings;


// Open chart in full-size modal
function openChartModal(imgElement) {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.9);
        z-index: 10000;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: fadeIn 0.3s ease;
    `;
    
    const chartTitle = imgElement.closest('.chart-container').querySelector('h4').textContent;
    
    modal.innerHTML = `
        <div style="position: relative; max-width: 90%; max-height: 90%; background: white; border-radius: 8px; padding: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="color: #2C3E50; margin: 0;">${chartTitle}</h3>
                <div>
                    <button id="exportChart" class="btn btn-primary" style="margin-right: 10px;">Export PNG</button>
                    <button id="closeModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #7F8C8D;">&times;</button>
                </div>
            </div>
            <img src="${imgElement.src}" alt="${chartTitle}" style="max-width: 100%; max-height: 70vh; object-fit: contain;">
            <div style="margin-top: 15px; padding: 15px; background: #F8F9FA; border-radius: 4px; border-left: 3px solid #3498DB;">
                <strong>How to read this graph:</strong><br>
                Example text on how to read graph will go here. This will be customized for each chart type to help users understand the data visualization.
            </div>
        </div>
    `;
    
    // Add fade animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
    `;
    document.head.appendChild(style);
    
    document.body.appendChild(modal);
    
    // Close modal handlers
    modal.querySelector('#closeModal').onclick = () => closeChartModal(modal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeChartModal(modal);
    });
    
    // Export handler
    modal.querySelector('#exportChart').onclick = () => exportChart(imgElement, chartTitle);
    
    // ESC key handler
    const handleEscape = (e) => {
        if (e.key === 'Escape') {
            closeChartModal(modal);
            document.removeEventListener('keydown', handleEscape);
        }
    };
    document.addEventListener('keydown', handleEscape);
}

// Close chart modal
function closeChartModal(modal) {
    modal.style.animation = 'fadeIn 0.3s ease reverse';
    setTimeout(() => modal.remove(), 300);
}

// Export chart as PNG
function exportChart(imgElement, chartTitle) {
    // Create a temporary canvas to export the image
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = function() {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
        
        // Download the image
        const link = document.createElement('a');
        link.download = `${chartTitle.replace(/\s+/g, '_')}.png`;
        link.href = canvas.toDataURL();
        link.click();
        
        showNotification(`Chart "${chartTitle}" exported successfully!`, 'success');
    };
    img.src = imgElement.src;
}

// Add export buttons to each chart
function addExportButtons() {
    document.querySelectorAll('.chart-container').forEach(container => {
        const exportBtn = document.createElement('button');
        exportBtn.className = 'btn btn-secondary';
        exportBtn.style.cssText = 'position: absolute; top: 15px; right: 15px; padding: 6px 12px; font-size: 12px;';
        exportBtn.textContent = 'Export';
        exportBtn.onclick = (e) => {
            e.stopPropagation();
            const img = container.querySelector('img');
            const title = container.querySelector('h4').textContent;
            exportChart(img, title);
        };
        
        container.style.position = 'relative';
        container.appendChild(exportBtn);
    });
}

// Render charts based on selected outputs (will be connected to settings later)
function renderChartsBasedOnOutputs() {
    const chartsGrid = document.querySelector('.charts-grid');
    if (!chartsGrid) return;
    
    // Clear existing charts
    chartsGrid.innerHTML = '';
    
    // Chart configurations based on selected outputs
    const chartConfigs = {
        'reflectance': {
            title: 'Remote Sensing Reflectance',
            image: 'https://i.imgur.com/TbT82XV.png',
            description: 'Example text on how to read reflectance spectra will go here. This shows the spectral signature of water at different wavelengths.'
        },
        'chlorophyll-hu': {
            title: 'Chlorophyll-a (Hu Color Index)',
            image: 'https://i.imgur.com/Jy2rdnZ.png',
            description: 'Example text on how to read chlorophyll maps will go here. Green areas indicate higher chlorophyll concentrations.'
        },
        'chlorophyll-ocx': {
            title: 'Chlorophyll-a (OCx Band Ratio)',
            image: 'https://i.imgur.com/TbT82XV.png',
            description: 'Example text on how to read OCx band ratio results will go here. This method uses blue-green ratios for estimation.'
        },
        'tsm': {
            title: 'Total Suspended Matter (TSM)',
            image: 'https://i.imgur.com/Jy2rdnZ.png',
            description: 'Example text on how to read TSM maps will go here. Darker areas typically indicate higher sediment loads.'
        }
    };
    
    // Render only selected charts
    selectedOutputs.forEach(outputType => {
        if (chartConfigs[outputType]) {
            const config = chartConfigs[outputType];
            const chartElement = createChartElement(config);
            chartsGrid.appendChild(chartElement);
        }
    });
    
    // Re-setup click handlers and export buttons
    setupChartClickHandlers();
    addExportButtons();
}

// Create individual chart element
function createChartElement(config) {
    const chartDiv = document.createElement('div');
    chartDiv.className = 'chart-container';
    chartDiv.innerHTML = `
        <h4>${config.title}</h4>
        <img src="${config.image}" alt="${config.title}">
        <div class="chart-blurb">${config.description}</div>
    `;
    return chartDiv;
}

// Update charts based on project settings (called from settings screen)
function updateChartsFromSettings(outputs) {
    selectedOutputs = outputs;
    renderChartsBasedOnOutputs();
    showNotification('Charts updated based on selected outputs', 'success');
}