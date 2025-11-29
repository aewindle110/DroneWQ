// frontend/project_settings.js

let methodValidationSetup = false; // Flag to prevent multiple setups

function initializeProjectSettings() {
  const processBtn = document.getElementById('processBtn');
  
  if (processBtn) {
    processBtn.addEventListener('click', submitProcessing);
  }
  
  // Only setup method validation once
  const currentScreen = document.querySelector('.screen.active');
  if (currentScreen && currentScreen.id === 'method' && !methodValidationSetup) {
    setupMethodValidation();
    methodValidationSetup = true;
  }
}

// Setup validation for method selection
function setupMethodValidation() {
  const glintSelect = document.getElementById('glintSelect');
  const irradianceSelect = document.getElementById('irradianceSelect');
  const nextBtn = document.querySelector('#method .btn-primary');
  
  if (!glintSelect || !irradianceSelect || !nextBtn) return;
  
  // DON'T clear selections - preserve what user selected
  // Only reset borders
  glintSelect.style.borderColor = '';
  glintSelect.style.borderWidth = '';
  irradianceSelect.style.borderColor = '';
  irradianceSelect.style.borderWidth = '';
  
  // Remove any existing onclick attribute
  nextBtn.removeAttribute('onclick');
  
  // Remove any existing listeners by cloning the button
  const newNextBtn = nextBtn.cloneNode(true);
  nextBtn.parentNode.replaceChild(newNextBtn, nextBtn);
  
  // Add single click handler with validation
  newNextBtn.addEventListener('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    
    const glintSelected = glintSelect.value && glintSelect.value !== '';
    const irradianceSelected = irradianceSelect.value && irradianceSelect.value !== '';
    
    // Reset borders first
    glintSelect.style.borderColor = '';
    glintSelect.style.borderWidth = '';
    irradianceSelect.style.borderColor = '';
    irradianceSelect.style.borderWidth = '';
    
    // Check if required fields are selected
    if (!glintSelected || !irradianceSelected) {
      // Show red borders only on empty fields
      if (!glintSelected) {
        glintSelect.style.borderColor = '#e74c3c';
        glintSelect.style.borderWidth = '2px';
      }
      if (!irradianceSelected) {
        irradianceSelect.style.borderColor = '#e74c3c';
        irradianceSelect.style.borderWidth = '2px';
      }
      
      alert('Please select both Sky Glint Removal Method and Irradiance Normalization Method before proceeding.');
      return;
    }
    
    // If validation passes, proceed
    navigate('outputs');
  });
  
  // Remove red border when user selects something
  glintSelect.addEventListener('change', function() {
    if (this.value && this.value !== '') {
      this.style.borderColor = '';
      this.style.borderWidth = '';
    }
  });
  
  irradianceSelect.addEventListener('change', function() {
    if (this.value && this.value !== '') {
      this.style.borderColor = '';
      this.style.borderWidth = '';
    }
  });
}

// Clear all project data when returning to dashboard
function clearProjectData() {
  // Clear session storage
  sessionStorage.removeItem('projectName');
  sessionStorage.removeItem('projectFolder');
  sessionStorage.removeItem('selectedWQAlgs');
  sessionStorage.removeItem('mosaic');
  
  // Clear method selections
  const glintSelect = document.getElementById('glintSelect');
  const irradianceSelect = document.getElementById('irradianceSelect');
  const maskingSelect = document.getElementById('maskingSelect');
  
  if (glintSelect) glintSelect.value = '';
  if (irradianceSelect) irradianceSelect.value = '';
  if (maskingSelect) maskingSelect.value = '';
  
  // Clear output checkboxes
  document.querySelectorAll('.outputChk').forEach(cb => cb.checked = false);
  
  // Reset validation flag
  methodValidationSetup = false;
  
  // Reset upload flags (defined in upload.js)
  if (typeof window.uploadInitialized !== 'undefined') {
    window.uploadInitialized = false;
  }
  if (typeof window.projectNameInitialized !== 'undefined') {
    window.projectNameInitialized = false;
  }
}

async function submitProcessing() {
  // Pull references saved during Upload step
  const folderPath = sessionStorage.getItem('projectFolder') || null;
  const projectName = sessionStorage.getItem('projectName') || null;
  
  // Collect Methods
  const glint = (document.getElementById('glintSelect') || {}).value || "";
  const irr = (document.getElementById('irradianceSelect') || {}).value || "";
  const mask = (document.getElementById('maskingSelect') || {}).value || "";
  
  // Double-check validation
  if (!glint || glint === '') {
    alert('Please select a Sky Glint Removal Method');
    navigate('method');
    return;
  }
  
  if (!irr || irr === '') {
    alert('Please select an Irradiance Normalization Method');
    navigate('method');
    return;
  }
  
  // Collect masking parameters
  let maskingParams = null;
  if (mask === 'value_threshold') {
    maskingParams = {
      nir_threshold: parseFloat(document.getElementById('nirThreshold').value),
      green_threshold: parseFloat(document.getElementById('greenThreshold').value)
    };
  } else if (mask === 'std_threshold') {
    maskingParams = {
      mask_std_factor: parseFloat(document.getElementById('maskStdFactor').value)
    };
  }
  
  // Collect all selected output keys
  const selected = Array.from(document.querySelectorAll('.outputChk:checked'))
    .map(cb => cb.getAttribute('data-key'));
  
  // Split into wqAlg vs mosaic
  const wqAlgs = selected.filter(key => key !== 'mosaics');
  const mosaic = selected.includes('mosaics');
  
  const payload = {
    project_name: projectName,
    folderPath: folderPath,
    lwMethod: glint,
    edMethod: irr,
    maskMethod: mask,
    wqAlgs: wqAlgs,
    mosaic: mosaic,
    maskingParams: maskingParams
  };
  
  // Save outputs to sessionStorage
  sessionStorage.setItem('selectedWQAlgs', JSON.stringify(wqAlgs));
  sessionStorage.setItem('mosaic', JSON.stringify(mosaic));
  
  // Show loading screen
  navigate('loading');
  
  try {
    // Save settings
    const settingsRes = await fetch('http://localhost:8889/api/projects/new', {
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

    const newProject = await settingsRes.json();
    sessionStorage.setItem('currentProjectId', newProject.id);
    console.log("Settings saved, project ID:", newProject.id);

    // Now trigger the actual processing
    const processRes = await fetch('http://localhost:8889/api/process/new/${newProject.id}');
    
    if (!processRes.ok) {
      const txt = await processRes.text();
      alert(`Backend error during processing (${processRes.status}): ${txt || 'Processing failed'}`);
      navigate('outputs');
      return;
    }
    
    const data = await processRes.json();
    console.log("Processing complete:", data);
    
    if (data.success) {
      if (typeof buildOverviewFromFolder === 'function') {
        buildOverviewFromFolder(folderPath, wqAlgs);
      }
      navigate('results');
    } else {
      alert('Processing failed');
      navigate('outputs');
    }
  } catch (e) {
    console.error("Processing error:", e);
    alert(`Could not reach backend: ${e.message}`);
    navigate('outputs');
  }
}

window.initializeProjectSettings = initializeProjectSettings;
window.clearProjectData = clearProjectData;
