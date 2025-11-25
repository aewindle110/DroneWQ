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
  console.log('=== buildOverviewFromFolder DEBUG ===');
  console.log('folderPath:', folderPath);
  console.log('selectedWQAlgs:', selectedWQAlgs);
  console.log('selectedWQAlgs type:', typeof selectedWQAlgs);
  console.log('selectedWQAlgs is array?', Array.isArray(selectedWQAlgs));

  //const folderPath = sessionStorage.getItem('projectFolder');
  if (!folderPath) {
    console.warn('No project folder set in sessionStorage');
    return;
  }

 const resultDir = path.join(folderPath, 'result');

// Always included cards
  const always = [
    { out: 'rrs', title: 'Radiometry Spectra Plot', file: 'rrs_plot.png', blurb: 'Remote sensing reflectance (Rrs) from 25 image captures that have not been masked for sun glint and image artifacts.' },
    { out: 'rrs', title: 'Radiometry Spectra Masked Plot', file: 'masked_rrs_plot.png', blurb: 'Rrs from same set of 25 images that have been masked for sun glint and artifacts. Bold black line shows the mean spectrum across all 25 images.' },
    { out: 'rrs', title: 'Lt Plot', file: 'lt_plot.png', blurb: 'Total radiance (Lt) spectra from the same 25 image captures.' },
    { out: 'rrs', title: 'Ed Plot', file: 'ed_plot.png', blurb: 'Downwelling irradiance (Ed) from the same 25 image captures.' },
  ];


  const outputs = JSON.parse(sessionStorage.getItem('selectedOutputs') || '[]');

const byOutput = [
    { out: 'chl_hu', title: '', file: 'chl_hu_plot.png', blurb: 'Coordinate locations of individual image captures colored by chlorophyll a concentration. (mg/m^3)' },
    { out: 'chl_ocx', title: 'Masked Rrs Plot', file: 'chl_ocx_plot.png', blurb: 'Coordinate locations of individual image captures colored by chlorophyll a concentration. (mg/m^3)' },
    { out: 'chl_hu_ocx', title: 'Lt Plot', file: 'chl_hu_ocx.png', blurb: 'Coordinate locations of individual image captures colored by chlorophyll a concentration. (mg/m^3)' },
    { out: 'chl_gitelson', title: 'Ed Plot', file: 'chl_gitelson.png', blurb: 'Coordinate locations of individual image captures colored by chlorophyll a concentration. (mg/m^3)' },
    { out: 'tsm_nechad', title: 'Ed Plot', file: 'tsm_nechad.png', blurb: 'Coordinate locations of individual image captures colored by total suspended matter (TSM, mg L-1).' },
]

  const container = document.getElementById('overviewCards');
  if (!container) {
    console.error('overviewCards container not found');
    return;
  }
  container.innerHTML = ''; // clear

  // Helper: create a card if file exists
  function addCardIfExists(title, fileName, blurb) {
    const fullPath = path.join(resultDir, fileName);

    
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

  // Always show the 4 basic radiometry plots
  for (const a of always) addCardIfExists(a.title, a.file, a.blurb);

  

 // Only show WQ plots that the user selected
  const selectedSet = new Set(selectedWQAlgs || []);
  console.log('Selected WQ algorithms:', selectedWQAlgs);
  console.log('selectedSet:', selectedSet);
  console.log('selectedSet size:', selectedSet.size);
  
  for (const item of byOutput) {
    console.log(`Checking ${item.out}:`, selectedSet.has(item.out));
    if (selectedSet.has(item.out)) {
      addCardIfExists(item.title, item.file, item.blurb, folderPath);
    }
  }
  console.log('=== END DEBUG ===');

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