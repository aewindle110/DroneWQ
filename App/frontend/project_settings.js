// project_settings.js

function initializeProjectSettings() {
  const processBtn = document.getElementById('processBtn');
  if (!processBtn) return;

  processBtn.addEventListener('click', submitProcessing);
}

async function submitProcessing() {
  // Pull references saved during Upload step
  const projectId  = sessionStorage.getItem('projectId') || null;
  const folderPath = sessionStorage.getItem('projectFolder') || null;
  const projectName = sessionStorage.getItem('projectName') || null;

  // Collect Methods
  const glint = (document.getElementById('glintSelect') || {}).value || "";
  const irr   = (document.getElementById('irradianceSelect') || {}).value || "";
  const mask  = (document.getElementById('maskingSelect') || {}).value || "";

  // Collect Outputs
  const outputs = Array.from(document.querySelectorAll('.outputChk:checked'))
    .map(cb => cb.getAttribute('data-key'));

  const payload = {
    project_id: projectId,         
    project_name: projectName,    
    folderPath: folderPath,         //folder path again
    lwMethod: glint,            // ex: "mobley_rho"
    edMethod: irr,             // ex: "panel_ed"
    maskMethod: mask,        // ex:"value_threshold", "std_threshold"
    outputs : outputs                         // ex: ["reflectance","chla_hu","tsm"]
  };

  try {
    const res = await fetch('http://localhost:5000/manage/save_settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const txt = await res.text();
      alert(`Backend error (${res.status}): ${txt || 'Processing failed'}`);
      return;
    }

    // Go to loading → results (or stay on loading and poll if you add that later)
    navigate('loading');
    setTimeout(() => navigate('results'), 1200);
  } catch (e) {
    alert(`Could not reach backend: ${e.message}`);
  }
}

// expose
window.initializeProjectSettings = initializeProjectSettings;
