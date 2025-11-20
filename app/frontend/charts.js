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
  const outputs = JSON.parse(sessionStorage.getItem('selectedOutputs') || '[]');

  // Always included cards
  const always = [
    { title: 'RGB Preview', file: 'rgb_preview.png', blurb: 'RGB overview of the scene.' }
  ];

  const byOutput = [
    { out: 'rrs', title: 'Rrs Plot', file: 'rrs_plot.png', blurb: 'Remote sensing reflectance across wavelengths.' },
    { out: 'rrs', title: 'Masked Rrs Plot', file: 'masked_rrs_plot.png', blurb: 'Reflectance after masking.' },
    { out: 'rrs', title: 'Lt Plot', file: 'lt_plot.png', blurb: 'Top-of-water radiance.' },
    { out: 'rrs', title: 'Ed Plot', file: 'ed_plot.png', blurb: 'Downwelling irradiance summary.' },
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
  // for (const a of always) addCardIfExists(a.title, a.file, a.blurb);

  // Conditional cards
  console.log(outputs)
  const outSet = new Set(outputs);
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
