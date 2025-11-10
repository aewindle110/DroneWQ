// frontend/charts.js
const path = require('path');
const { pathToFileURL } = require('url');
const fs = require('fs');

function initializeCharts() {
  // Optionally auto-build when page loads if already on results
  const resultsScreen = document.getElementById('results');
  if (resultsScreen && resultsScreen.classList.contains('active')) {
    buildOverviewFromFolder();
  }
}

/**
 * Build the Overview cards from images the backend writes into the project's main folder.
 * We show only the cards that make sense based on selected outputs.
 */
function buildOverviewFromFolder() {
  const folderPath = sessionStorage.getItem('projectFolder');
  if (!folderPath) {
    console.warn('No project folder set in sessionStorage');
    return;
  }

  const outputs = JSON.parse(sessionStorage.getItem('selectedOutputs') || '[]');

  // Backend file names (as per your teammate's Pipeline code)
  // Always-safe cards:
  const always = [
    { key: 'flight_plan', title: 'Flight Plan', file: 'flight_plan.png', blurb: 'Flight path, altitude, yaw summary.' }
  ];

  // Conditional cards mapped to outputs
  const byOutput = [
    { out: 'reflectance',   title: 'Rrs Plot',        file: 'rrs_plot.png',         blurb: 'Remote sensing reflectance across key wavelengths.' },
    { out: 'reflectance',   title: 'Masked Rrs Plot', file: 'masked_rrs_plot.png',  blurb: 'Reflectance after pixel masking.' },
    { out: 'tsm',           title: 'Lt Plot',         file: 'lt_plot.png',          blurb: 'Top-of-water radiance.' },
    { out: 'panel_ed',      title: 'Ed Plot',         file: 'ed_plot.png',          blurb: 'Downwelling irradiance summary.' },
    // If your teammate also saves chlorophyll maps as files, add them similarly:
    // { out: 'chla_hu', title: 'Chlorophyll (Hu)', file: 'chla_hu_map.png', blurb: 'Hu color index map.' },
    // { out: 'chla_ocx', title: 'Chlorophyll (OCx)', file: 'chla_ocx_map.png', blurb: 'OCx band ratio map.' },
  ];

  const container = document.getElementById('overviewCards');
  if (!container) {
    console.error('overviewCards container not found');
    return;
  }
  container.innerHTML = ''; // clear

  // Helper: create a card if file exists
  function addCardIfExists(title, fileName, blurb) {
    const fullPath = path.join(folderPath, fileName);
    
    // Check if file exists
    if (!fs.existsSync(fullPath)) {
      console.log(`File not found: ${fullPath}`);
      return;
    }

    const url = pathToFileURL(fullPath).href;
    const card = document.createElement('div');
    card.className = 'chart-container';
    card.innerHTML = `
      <h4 style="color: #2C3E50; font-size: 18px; margin-bottom: 10px; font-weight: 600;">${title}</h4>
      <img src="${url}" alt="${title}" style="width: 100%; border-radius: 4px; margin: 10px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
      <div class="chart-blurb" style="color: #7F8C8D; font-size: 14px; line-height: 1.5;">${blurb}</div>
    `;
    container.appendChild(card);
  }

  // Always add these if present
  for (const a of always) addCardIfExists(a.title, a.file, a.blurb);

  // Decide which conditional plots to show
  const outSet = new Set(outputs || []);
  for (const item of byOutput) {
    if (outSet.has(item.out)) {
      addCardIfExists(item.title, item.file, item.blurb);
    }
  }

  // Fallback: if nothing rendered, show a friendly message
  if (!container.children.length) {
    const msg = document.createElement('div');
    msg.className = 'chart-blurb';
    msg.style.padding = '40px';
    msg.style.textAlign = 'center';
    msg.style.color = '#7F8C8D';
    msg.textContent = 'No result images found yet. The backend may still be processing, or check your output selection.';
    container.appendChild(msg);
  }
}

window.initializeCharts = initializeCharts;
window.buildOverviewFromFolder = buildOverviewFromFolder;