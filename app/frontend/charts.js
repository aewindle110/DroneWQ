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

function buildOverviewFromFolder() {
  const folderPath = sessionStorage.getItem('projectFolder');
  if (!folderPath) {
    console.warn('No project folder set in sessionStorage');
    return;
  }

  const resultDir = path.join(folderPath, 'result');
  console.log(resultDir)
  const wqAlgs = JSON.parse(sessionStorage.getItem('selectedWQAlgs') || '[]');
  const mosaic = JSON.parse(sessionStorage.getItem('mosaic') || '[]');

  // Always included cards
  const always = [
    { out: 'rrs', title: 'Radiometry Spectra Plot', file: 'rrs_plot.png', blurb: 'Remote sensing reflectance (Rrs) from 25 image captures that have not been masked for sun glint and image artifacts.' },
    { out: 'rrs', title: 'Radiometry Spectra Masked Plot', file: 'masked_rrs_plot.png', blurb: 'Rrs from same set of 25 images that have been masked for sun glint and artifacts. Bold black line shows the mean spectrum across all 25 images.' },
    { out: 'rrs', title: 'Lt Plot', file: 'lt_plot.png', blurb: 'Total radiance (Lt) spectra from the same 25 image captures.' },
    { out: 'rrs', title: 'Ed Plot', file: 'ed_plot.png', blurb: 'Downwelling irradiance (Ed) from the same 25 image captures.' },
  ];

  const byOutput = [
    { out: 'chl_hu', title: '', file: 'chl_hu_plot.png', blurb: 'Coordinate locations of individual image captures colored by chlorophyll a concentration. (mg/m^3)' },
    { out: 'chl_ocx', title: 'Masked Rrs Plot', file: 'chl_ocx_plot.png', blurb: 'Coordinate locations of individual image captures colored by chlorophyll a concentration. (mg/m^3)' },
    { out: 'chl_hu_ocx', title: 'Lt Plot', file: 'chl_hu_ocx.png', blurb: 'Coordinate locations of individual image captures colored by chlorophyll a concentration. (mg/m^3)' },
    { out: 'chl_gitelson', title: 'Ed Plot', file: 'chl_gitelson.png', blurb: 'Coordinate locations of individual image captures colored by chlorophyll a concentration. (mg/m^3)' },
    { out: 'tsm_nechad', title: 'Ed Plot', file: 'tsm_nechad.png', blurb: 'Coordinate locations of individual image captures colored by total suspended matter (TSM, mg L-1).' },
  ];

  const container = document.getElementById('overviewCards');
  if (!container) {
    console.error('overviewCards container not found');
    return;
  }

  container.innerHTML = '';

  function addCardIfExists(title, fileName, blurb) {
    const fullPath = path.join(resultDir, fileName);
    if (!fs.existsSync(fullPath)) return;

    const url = pathToFileURL(fullPath).href;
    const card = document.createElement('div');
    card.className = 'chart-container';

    card.innerHTML = `
      <h4>${title}</h4>
      <img src="${url}" alt="${title}" />
      <div class="chart-blurb">${blurb}</div>
    `;
    container.appendChild(card);
  }

  // Always show
  for (const a of always) addCardIfExists(a.title, a.file, a.blurb);

  // Conditional cards
  console.log(wqAlgs)
  const outSet = new Set(wqAlgs);
  for (const item of byOutput) {
    if (outSet.has(item.out)) {
      addCardIfExists(item.title, item.file, item.blurb);
    }
  }

  if (!container.children.length) {
    const msg = document.createElement('div');
    msg.textContent = 'No result images found.';
    container.appendChild(msg);
  }
}

function buildFlightTrajectory() {
  const folderPath = sessionStorage.getItem('projectFolder');
  if (!folderPath) return;

  const resultDir = path.join(folderPath, 'result');
  const flightPlanPath = path.join(resultDir, 'flight_plan.png');

  if (!fs.existsSync(flightPlanPath)) return;

  const trajectoryTab = document.getElementById('trajectory');
  if (!trajectoryTab) return;

  const url = pathToFileURL(flightPlanPath).href;

  let img = trajectoryTab.querySelector('img');
  if (!img) {
    img = document.createElement('img');
    img.style.width = '100%';
    trajectoryTab.appendChild(img);
  }

  img.src = url;
  img.alt = 'Flight Plan';
}

window.initializeCharts = initializeCharts;
window.buildOverviewFromFolder = buildOverviewFromFolder;
