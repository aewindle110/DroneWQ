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