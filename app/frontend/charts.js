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
function buildOverviewFromFolder() {
  const folderPath = sessionStorage.getItem('projectFolder');
  if (!folderPath) {
    console.warn('No project folder set in sessionStorage');
    return;
  }

 const resultDir = path.join(folderPath, 'result');

 const always = [
  { title: 'Rrs Plot', file: 'rrs_plot.png', blurb: 'Remote sensing reflectance (Rrs) from 25 image captures.' },
  { title: 'Masked Rrs Plot', file: 'masked_rrs_plot.png', blurb: 'Rrs from masked images.' },
  { title: 'Lt Plot', file: 'lt_plot.png', blurb: 'Total radiance (Lt) spectra.' },
  { title: 'Ed Plot', file: 'ed_plot.png', blurb: 'Downwelling irradiance (Ed).' },
];


  const outputs = JSON.parse(sessionStorage.getItem('selectedOutputs') || '[]');

  // Conditional cards mapped to outputs
  const byOutput = [
    { out: 'reflectance',   title: 'Rrs Plot',        file: 'rrs_plot.png',         blurb: 'Remote sensing reflectance across key wavelengths.' },
    { out: 'reflectance',   title: 'Masked Rrs Plot', file: 'masked_rrs_plot.png',  blurb: 'Reflectance after pixel masking.' },
    { out: 'tsm',           title: 'Lt Plot',         file: 'lt_plot.png',          blurb: 'Top-of-water radiance.' },
    { out: 'panel_ed',      title: 'Ed Plot',         file: 'ed_plot.png',          blurb: 'Downwelling irradiance summary.' },
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