// frontend/mosaic_handler.js

function renderMosaicCards() {
  const projectFolder = sessionStorage.getItem('projectFolder');
  if (!projectFolder) {
    console.warn('No project folder provided');
    return;
  }

  const resultDir = path.join(projectFolder, 'result');
  const container = document.getElementById("mosaicCards");
  
  if (!container) return;

  // Check if result directory exists
  if (!fs.existsSync(resultDir)) {
    console.log('Result directory does not exist:', resultDir);
    container.innerHTML = `
      <p style="padding: 40px; text-align: center; color: #7F8C8D;">
        No mosaics generated yet. Adjust settings and click <strong>Process Mosaic</strong>.
      </p>
    `;
    return;
  }

  const items = [];

  // Scan the result directory for mosaic PNG files
  const files = fs.readdirSync(resultDir);
  
  files.forEach(file => {
    if (file.startsWith('mosaic_') && file.endsWith('.png')) {
      const fullPath = path.join(resultDir, file);
      
      // Parse: mosaic_chl_hu.png or mosaic_chl_hu_downsampled_2.png
      const fileName = file.replace('.png', '');
      
      let title;
      if (fileName.includes('_downsampled_')) {
        // Extract algorithm and downsample factor
        const match = fileName.match(/mosaic_(.+)_downsampled_(\d+)/);
        if (match) {
          const algorithm = match[1];
          const factor = match[2];
          title = `${algorithm} (Downsampled ×${factor})`;
        }
      } else {
        // Just algorithm
        const algorithm = fileName.replace('mosaic_', '');
        title = algorithm;
      }
      
      items.push({
        title: title,
        file: fullPath
      });
    }
  });

  // Render cards
  if (items.length === 0) {
    container.innerHTML = `
      <p style="padding: 40px; text-align: center; color: #7F8C8D;">
        No mosaics generated yet. Adjust settings and click <strong>Process Mosaic</strong>.
      </p>
    `;
    return;
  }

  container.innerHTML = items.map(item => {
    const url = pathToFileURL(item.file).href;

    return `
      <div class="overview-card" style="cursor:pointer;"
           onclick="openImageModal('${url}', '${item.title}')">
        <div class="card-title">${item.title}</div>
        <img src="${url}" style="width:100%; border-radius:4px; margin-top:10px;">
      </div>
    `;
  }).join("");
}

// PROCESS MOSAIC
async function processMosaic() {
  const projectId = sessionStorage.getItem("currentProjectId");
  if (!projectId) {
    alert("No project selected.");
    return;
  }

  const checked = [...document.querySelectorAll(".mosaic-alg-chk")].filter(cb => cb.checked);

  if (checked.length === 0) {
    alert("Please select one water quality algorithm.");
    return;
  }
  if (checked.length > 1) {
    alert("Only one algorithm is allowed.");
    return;
  }

  const wqAlg = checked[0].getAttribute("data-key");

  const evenYaw = parseNumericDefault("mosaicYawEven", 0);
  const oddYaw = parseNumericDefault("mosaicYawOdd", 0);
  const altitude = parseRequiredNumeric("mosaicAltitude");
  const pitch = parseNumericDefault("mosaicPitch", 0);
  const roll = parseNumericDefault("mosaicRoll", 0);
  const method = document.getElementById("mosaicMethodSelect")?.value || "mean";

  let downsample = parseFloat(document.getElementById("mosaicDownsampleFactor")?.value);
  if (isNaN(downsample) || downsample < 1) downsample = 1;

  if (altitude === null) {
    alert("Altitude is required.");
    return;
  }

  const payload = {
    projectId: Number(projectId),
    wqAlg,
    evenYaw,
    oddYaw,
    altitude,
    pitch,
    roll,
    method,
    downsample
  };

  console.log("[MOSAIC] Sending payload:", payload);

  try {
    const res = await fetch("http://localhost:8889/api/process/mosaic", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const error = await res.text();
      console.error(error);
      alert("Mosaic processing failed: " + error);
      return;
    }

    const data = await res.json();
    console.log("[MOSAIC] Backend response:", data);

    // Refresh cards to show newly generated mosaic
    renderMosaicCards();

    document.getElementById("mosaicSettingsPanel").style.display = "none";
    document.getElementById("mosaicSettingsToggle").style.display = "inline-block";
    
    alert('Mosaic generated successfully!');
    
  } catch (error) {
    console.error('[MOSAIC] Error:', error);
    alert('Error processing mosaic: ' + error.message);
  }
}

function showMosaicSettingsPanel(show) {
  const panel = document.getElementById("mosaicSettingsPanel");
  const toggle = document.getElementById("mosaicSettingsToggle");
  
  if (show) {
    panel.style.display = "block";
    toggle.style.display = "none";
  } else {
    panel.style.display = "none";
    toggle.style.display = "inline-block";
  }
}

// helpers
function parseNumeric(id) {
  const el = document.getElementById(id);
  if (!el || !el.value.trim()) return null;
  const num = parseFloat(el.value);
  return isNaN(num) ? null : num;
}

function parseNumericDefault(id, def) {
  const el = document.getElementById(id);
  if (!el || !el.value.trim()) return def;
  const num = parseFloat(el.value);
  return isNaN(num) ? def : num;
}

function parseRequiredNumeric(id) {
  const el = document.getElementById(id);
  if (!el || !el.value.trim()) return null;
  const num = parseFloat(el.value);
  return isNaN(num) ? null : num;
}

window.processMosaic = processMosaic;
window.renderMosaicCards = renderMosaicCards;
window.showMosaicSettingsPanel = showMosaicSettingsPanel;