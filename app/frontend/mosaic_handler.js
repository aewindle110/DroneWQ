// frontend/mosaic_handler.js

function renderMosaicCards(folderPath, downsamplePath) {
  const container = document.getElementById("mosaicCards");
  if (!container) return;

  container.innerHTML = "";

  const items = []; 

  //Always include the original 

  if(folderPath){
    items.push({
      ttle: "Mosaic (Original Resolution)", 
      file: folderPath
    }); 
  }

  // Only include downsampled version if downsample > 1
  if (downsampleFactor > 1 && downsamplePath) {
    items.push({
      title: `Mosaic (Downsampled × ${downsampleFactor})`,
      file: downsamplePath
    });
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



// PROCESS MOSAIC (updated for backend)
async function processMosaic() {
  const projectId = sessionStorage.getItem("currentProjectId");
  if (!projectId) {
    alert("No project selected.");
    return;
  }

  // ---- SELECT ONLY ONE WQ ALGORITHM ----
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

  // ---- Collect fields ----
  const evenYaw = parseNumeric("mosaicYawEven");
  const oddYaw  = parseNumeric("mosaicYawOdd");
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

  // ---- Build payload to match backend ----
  const payload = {
    projectId: Number(projectId),
    wqAlg,               // single algorithm
    evenYaw,
    oddYaw,
    altitude,
    pitch,
    roll,
    method,
    downsample
  };

  console.log("[MOSAIC] Sending payload:", payload);

  const res = await fetch("http://localhost:8889/api/process/mosaic", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    console.error(await res.text());
    alert("Mosaic processing failed.");
    return;
  }

  const data = await res.json();
  console.log("[MOSAIC] Backend response:", data);

  // Backend returns:
  // { "folder_path": "...", "downsample_path": "..." }
  renderMosaicCards(data.folder_path, data.downsample_path, downsample);

  // hide settings panel and show "Mosaic Settings" button
  document.getElementById("mosaicSettingsPanel").style.display = "none";
  document.getElementById("mosaicSettingsToggle").style.display = "inline-block";
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
