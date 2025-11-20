// frontend/project_settings.js

function initializeSettings() {
  // no-op so DOMContentLoaded("initializeSettings") won't crash
}

function initializeProjectSettings() {
  const processBtn = document.getElementById('processBtn');
  if (!processBtn) return;
  processBtn.addEventListener('click', submitProcessing);
}

async function submitProcessing() {
  // Pull references saved during Upload step
  const projectId = sessionStorage.getItem('projectId') || null;
  const folderPath = sessionStorage.getItem('projectFolder') || null;
  const projectName = sessionStorage.getItem('projectName') || null;

  // Collect Methods
  const glint = (document.getElementById('glintSelect') || {}).value || "";
  const irr = (document.getElementById('irradianceSelect') || {}).value || "";
  const mask = (document.getElementById('maskingSelect') || {}).value || "";

  // Collect Outputs
  const outputs = Array.from(document.querySelectorAll('.outputChk:checked'))
    .map(cb => cb.getAttribute('data-key'));

  const payload = {
    project_id: projectId,
    project_name: projectName,
    folderPath: folderPath,
    lwMethod: glint,
    edMethod: irr,
    maskMethod: mask,
    outputs: outputs
  };

  // Save outputs to sessionStorage so charts.js can use them
  sessionStorage.setItem('selectedOutputs', JSON.stringify(outputs));

  // Show the loading screen right away
  navigate('loading');

  try {
    // First, save the settings
    const settingsRes = await fetch('http://localhost:8889/manage/save_settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!settingsRes.ok) {
      const txt = await settingsRes.text();
      alert(`Backend error saving settings (${settingsRes.status}): ${txt || 'Failed'}`);
      navigate('outputs');
      return;
    }

    console.log("Settings saved, starting processing...");

    // Now trigger the actual processing
    const processRes = await fetch('http://localhost:8889/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folderPath: folderPath })
    });

    if (!processRes.ok) {
      const txt = await processRes.text();
      alert(`Backend error during processing (${processRes.status}): ${txt || 'Processing failed'}`);
      navigate('outputs');
      return;
    }

    //  Wait until backend confirms completion
    const data = await processRes.json();
    console.log("Processing complete:", data);

    if (data.success) {
      // Charts ready = 1 (true)
      navigate('results');
      buildOverviewFromFolder();
    } else {
      // Charts not ready = 0 (false)
      alert('Processing failed');
      navigate('outputs');
    }

    // After backend finishes, load charts and go to results
    if (typeof buildOverviewFromFolder === 'function') {
      buildOverviewFromFolder();
    }
    navigate('results');

  } catch (e) {
    console.error("Processing error:", e);
    alert(`Could not reach backend: ${e.message}`);
    navigate('outputs');
  }
}

window.initializeSettings = initializeSettings;
window.initializeProjectSettings = initializeProjectSettings;
