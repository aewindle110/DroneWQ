// frontend/charts.js
const path = require('path');
const { pathToFileURL } = require('url');
const fs = require('fs');

function initializeCharts() {
  const resultsScreen = document.getElementById('results');
  if (resultsScreen && resultsScreen.classList.contains('active')) {
    buildOverviewFromFolder();
    buildFlightTrajectory();
  }
}

/**
 * Build the Overview cards from images the backend writes into the project's main folder.
 * We show only the cards that make sense based on selected outputs.
 */
function buildOverviewFromFolder(folderPath, selectedWQAlgs) {
  if (!folderPath) {
    console.warn('No project folder provided');
    return;
  }
  
  const resultDir = path.join(folderPath, 'result');

  // Load accessibility descriptions
  let accessibilityDescriptions = {};
  const descriptionsPath = path.join(resultDir, 'plot_descriptions.json');
  if (fs.existsSync(descriptionsPath)) {
    try {
      const data = fs.readFileSync(descriptionsPath, 'utf8');
      accessibilityDescriptions = JSON.parse(data);
      console.log('Loaded accessibility descriptions');
    } catch (err) {
      console.warn('Failed to load accessibility descriptions:', err);
    }
  }

  // Always included radiometry plots
  const radiometry = [
    { key: 'rrs_plot', title: 'Radiometry Spectra Plot', file: 'rrs_plot.png', blurb: 'Remote sensing reflectance (Rrs) from image captures that have not been masked for sun glint and image artifacts.' },
    { key: 'masked_rrs_plot', title: 'Radiometry Spectra Masked Plot', file: 'masked_rrs_plot.png', blurb: 'Rrs from images that have been masked for sun glint and artifacts. Bold black line shows the mean spectrum across all images.' },
    { key: 'lt_plot', title: 'Lt Plot', file: 'lt_plot.png', blurb: 'Total radiance (Lt) spectra from the image captures.' },
    { key: 'ed_plot', title: 'Ed Plot', file: 'ed_plot.png', blurb: 'Downwelling irradiance (Ed) from the image captures.' },
  ];

  // Water quality plots (conditional)
  const waterQuality = [
    { key: 'chl_hu_plot', out: 'chl_hu', title: 'Chlorophyll-a (Hu Color Index)', file: 'chl_hu_plot.png', blurb: 'Coordinate locations of individual image captures colored by chlorophyll a concentration (mg/m³).' },
    { key: 'chl_ocx_plot', out: 'chl_ocx', title: 'Chlorophyll-a (OCx Band Ratio)', file: 'chl_ocx_plot.png', blurb: 'Coordinate locations of individual image captures colored by chlorophyll a concentration (mg/m³).' },
    { key: 'chl_hu_ocx_plot', out: 'chl_hu_ocx', title: 'Chlorophyll-a (Blended Hu+OCx)', file: 'chl_hu_ocx_plot.png', blurb: 'Coordinate locations of individual image captures colored by chlorophyll a concentration (mg/m³).' },
    { key: 'chl_gitelson_plot', out: 'chl_gitelson', title: 'Chlorophyll-a (Gitelson)', file: 'chl_gitelson_plot.png', blurb: 'Coordinate locations of individual image captures colored by chlorophyll a concentration (mg/m³).' },
    { key: 'tsm_nechad_plot', out: 'tsm_nechad', title: 'Total Suspended Matter (TSM)', file: 'tsm_nechad_plot.png', blurb: 'Coordinate locations of individual image captures colored by total suspended matter (TSM, mg/L).' },
  ];

  const radiometryContainer = document.getElementById('radiometryCards');
  const waterQualityContainer = document.getElementById('waterQualityCards');
  
  if (!radiometryContainer || !waterQualityContainer) {
    console.error('Overview containers not found');
    return;
  }

  radiometryContainer.innerHTML = '';
  waterQualityContainer.innerHTML = '';

  // Add all radiometry plots
  radiometry.forEach(item => {
    addCard(item.title, item.file, item.blurb, radiometryContainer, item.key);
  });

  // Add selected water quality plots
  const selectedSet = new Set(selectedWQAlgs || []);
  waterQuality.forEach(item => {
    if (selectedSet.has(item.out)) {
      addCard(item.title, item.file, item.blurb, waterQualityContainer, item.key);
    }
  });

  // Show message if no WQ plots
  if (waterQualityContainer.children.length === 0) {
    waterQualityContainer.innerHTML = `
      <div style="padding: 40px; text-align: center; color: #7F8C8D; border: 1px dashed #DEE2E6; border-radius: 8px;">
        <p>No water quality analyses selected for this project.</p>
      </div>
    `;
  }

  // Show message if no radiometry plots
  if (radiometryContainer.children.length === 0) {
    radiometryContainer.innerHTML = `
      <div style="padding: 40px; text-align: center; color: #7F8C8D; border: 1px dashed #DEE2E6; border-radius: 8px;">
        <p>Processing results will appear here.</p>
      </div>
    `;
  }


  // Helper: create a card if file exists
  function addCard(title, fileName, blurb, container, plotKey) {
    const fullPath = path.join(resultDir, fileName);
    
    if (!fs.existsSync(fullPath)) {
      console.log(`File not found: ${fullPath}`);
      return;
    }

    const url = pathToFileURL(fullPath).href;
    
    // Get accessibility description if available
    const accessibleDesc = accessibilityDescriptions[plotKey] || null;
    
    const card = document.createElement('div');
    card.className = 'result-card';
    card.innerHTML = `
      <img 
        src="${url}" 
        alt="${title}" 
        class="card-image"
        onclick="openImageModal('${url}', '${title}')"
        tabindex="0"
        role="button"
        onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openImageModal('${url}','${title}')}"
      />
      <div class="card-content">
        <div class="card-title">${title}</div>
        <div class="card-description">${blurb}</div>
        ${accessibleDesc ? `
          <details style="margin-top: 12px;">
            <summary style="cursor: pointer; color: #3498DB; font-size: 13px; font-weight: 500; user-select: none;">
               View generated description of the graph
            </summary>
            <p style="font-size: 12px; color: #555; margin-top: 8px; padding: 12px; background: #F8F9FA; border-radius: 4px; line-height: 1.6;">
              ${accessibleDesc}
            </p>
          </details>
        ` : ''}
      </div>
    `;
    container.appendChild(card);
  }
}

// Add modal function for viewing full-size images
function openImageModal(imageUrl, title) {
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
    padding: 40px;
  `;
  
  modal.innerHTML = `
    <div style="position: relative; max-width: 90%; max-height: 90%; display: flex; flex-direction: column; align-items: center;">
      <div style="position: absolute; top: -40px; right: 0; display: flex; gap: 15px; align-items: center;">
        <span style="color: white; font-size: 14px;">${title}</span>
        <button onclick="this.closest('div').parentElement.parentElement.remove()" 
                style="background: white; border: none; border-radius: 50%; width: 36px; height: 36px; font-size: 24px; cursor: pointer; color: #333;">
          &times;
        </button>
      </div>
      <img src="${imageUrl}" style="max-width: 100%; max-height: 50vh; object-fit: contain; border-radius: 4px;" />
    </div>
  `;
  
  document.body.appendChild(modal);
  
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.remove();
  });
}

window.openImageModal = openImageModal;

/**
 * Load the flight plan image into the trajectory tab
 */
function buildFlightTrajectory() {
  const folderPath = sessionStorage.getItem('projectFolder');
  if (!folderPath) {
    console.warn('No project folder set in sessionStorage');
    return;
  }

  const resultDir = path.join(folderPath, 'result');

  const flightPlanPath = path.join(resultDir, 'flight_plan.png');

  if (!fs.existsSync(flightPlanPath)) {
    console.log('flight_plan.png not found in', resultDir);
    return;
  }

  const trajectoryTab = document.getElementById('trajectory');
  if (!trajectoryTab) {
    console.error('trajectory tab not found');
    return;
  }

  // Find the existing img tag in trajectory tab and replace its src
  const existingImg = trajectoryTab.querySelector('img');
  if (existingImg) {
    const url = pathToFileURL(flightPlanPath).href;
    existingImg.src = url;
    existingImg.alt = 'Flight Plan';
    console.log('Flight plan image loaded into trajectory tab');
  } else {
    // If no img tag exists, create one
    const url = pathToFileURL(flightPlanPath).href;
    const img = document.createElement('img');
    img.src = url;
    img.alt = 'Flight Plan';
    img.style.width = '100%';
    img.style.borderRadius = '4px';
    img.style.marginTop = '20px';
    trajectoryTab.appendChild(img);
  }
}


window.initializeCharts = initializeCharts;
window.buildOverviewFromFolder = buildOverviewFromFolder;