// frontend/mosaic_handler.js

// Build mosaic cards
function renderMosaicCards(folderPath, mosaics) {
  const container = document.getElementById("mosaicCards");
  if (!container) return;

  if (!mosaics || mosaics.length === 0) {
    container.innerHTML = `
      <p style="padding: 40px; text-align:center; color:#7F8C8D;">
        No mosaic results yet. Process mosaics using the controls above.
      </p>`;
    return;
  }

  container.innerHTML = mosaics.map(m => {

    // Build filename from method + mosaic + alg
    const filename = `${m.method}_mosaic_${m.alg}.png`;

    const filePath = path.join(folderPath, "result", filename);
    const url = pathToFileURL(filePath).href;

    return `
      <div class="overview-card" style="cursor:pointer;"
           onclick="openImageModal('${url}', 'Mosaic – ${m.alg}')">

        <div class="card-title">Mosaic – ${m.alg}</div>
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

  const algCheckboxes = document.querySelectorAll(".mosaic-alg-chk");

  // Enforce single choice
  algCheckboxes.forEach(cb => {
    cb.addEventListener("change", function() {
      if (this.checked) {
        algCheckboxes.forEach(otherCb => {
          if (otherCb !== this) otherCb.checked = false;
        });
      }
    });
  });

  // Get selected algorithm as a single variable
  let wq_alg = null;
  algCheckboxes.forEach(cb => {
    if (cb.checked) {
      const alg = cb.getAttribute("data-key");
      if (alg) wq_alg = alg;
    }
  });

  if (!wq_alg) {
    alert("Please select a water quality algorithm.");
    return;
  }


  // Collect sensor + flight inputs
  const yaw_even = parseNumeric("mosaicYawEven");
  const yaw_odd = parseNumeric("mosaicYawOdd");
  const altitude = parseRequiredNumeric("mosaicAltitude");
  const pitch = parseNumericDefault("mosaicPitch", 0);
  const roll = parseNumericDefault("mosaicRoll", 0);

  //  method + downsample
  const method = document.getElementById("mosaicMethodSelect")?.value || "mean";

  const downsampleInput = document.getElementById("mosaicDownsampleFactor")?.value;
  let downsample = parseFloat(downsampleInput);
  if (isNaN(downsample) || downsample < 1) downsample = 1;

  if (altitude === null) {
    alert("Altitude is required.");
    return;
  }

  const payload = {
    projectId: Number(projectId),
    wq_alg,
    yaw_even,
    yaw_odd,
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
    alert("Mosaic processing failed. See console.");
    return;
  }

  const data = await res.json();
  console.log("[MOSAIC] Backend response:", data);

  renderMosaicCards(data.folder_path, data.mosaics);
}


// Helpers to parse numbers
function parseNumeric(id) {
  const el = document.getElementById(id);
  if (!el || el.value.trim() === "") return null;
  const num = parseFloat(el.value);
  return isNaN(num) ? null : num;
}

function parseNumericDefault(id, def) {
  const el = document.getElementById(id);
  if (!el || el.value.trim() === "") return def;
  const num = parseFloat(el.value);
  return isNaN(num) ? def : num;
}

function parseRequiredNumeric(id) {
  const el = document.getElementById(id);
  if (!el || el.value.trim() === "") return null;
  const num = parseFloat(el.value);
  return isNaN(num) ? null : num;
}


// Expose globally
window.processMosaic = processMosaic;
window.renderMosaicCards = renderMosaicCards;
