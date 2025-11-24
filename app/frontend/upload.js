// frontend/upload.js
const { ipcRenderer } = require('electron');

let selectedFolderPath = null; 

function initializeUpload() {
  const btn = document.getElementById('uploadFolderBtn');
  const projectNameInput = document.getElementById('projectNameInput'); 
  const nextBtn = document.getElementById('uploadNextBtn'); 
  if (!btn) return;

   // Enable/disable Next button based on inputs
  function checkFormValidity() {
    const hasName = projectNameInput && projectNameInput.value.trim() !== '';
    const hasFolder = selectedFolderPath !== null;
    
    if (nextBtn) {
      nextBtn.disabled = !(hasName && hasFolder);
    }
  }
  
  // Listen for project name changes
  if (projectNameInput) {
    projectNameInput.addEventListener('input', checkFormValidity);
  }

  btn.addEventListener('click', async () => {
    try {
      const res = await ipcRenderer.invoke('select-folder');
      if (!res || !res.success) return;
      
      selectedFolderPath = res.path;
      
      // Show selected folder
      const displayDiv = document.getElementById('selectedFolderDisplay');
      const pathSpan = document.getElementById('selectedFolderPath');
      if (displayDiv && pathSpan) {
        pathSpan.textContent = selectedFolderPath;
        displayDiv.style.display = 'block';
      }
      
      // Auto-fill project name if empty
      if (projectNameInput && projectNameInput.value.trim() === '') {
        const folderName = selectedFolderPath.split(/[\\/]/).pop() || 'My Project';
        projectNameInput.value = folderName;
      }
      
      // Check folder structure with backend
      const resp = await fetch('http://localhost:8889/api/projects/check_folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folderPath: selectedFolderPath })
      });
      
      if (!resp.ok) {
        const msg = await resp.text();
        alert(`Folder structure error: ${msg || resp.statusText}`);
        selectedFolderPath = null;
        if (displayDiv) displayDiv.style.display = 'none';
        checkFormValidity();
        return;
      }
      
      checkFormValidity();
      
    } catch (err) {
      console.error(err);
      alert('Could not select folder.');
      selectedFolderPath = null;
      checkFormValidity();
    }
  });
}

// Check if project name already exists and modify if needed
async function getUniquProjectName(baseName) {
  try {
    const response = await fetch('http://localhost:8889/api/projects');
    if (!response.ok) {
      console.warn('Could not fetch existing projects');
      return baseName;
    }
    
    const projects = await response.json();
    const existingNames = projects.map(p => p.name.toLowerCase());
    
    // If name doesn't exist, return it
    if (!existingNames.includes(baseName.toLowerCase())) {
      return baseName;
    }
    
    // Find the next available number
    let counter = 1;
    let newName = `${baseName}-${counter}`;
    
    while (existingNames.includes(newName.toLowerCase())) {
      counter++;
      newName = `${baseName}-${counter}`;
    }
    
    return newName;
    
  } catch (err) {
    console.error('Error checking project names:', err);
    return baseName; // Return original if error
  }
}

// Validate and proceed to next step
async function validateAndProceed() {
  const projectNameInput = document.getElementById('projectNameInput');
  
  if (!projectNameInput || projectNameInput.value.trim() === '') {
    alert('Please enter a project name');
    return;
  }
  
  if (!selectedFolderPath) {
    alert('Please select a data folder');
    return;
  }
  
  // Get unique project name (add suffix if duplicate)
  const requestedName = projectNameInput.value.trim();
  const uniqueName = await getUniquProjectName(requestedName);
  
  // If name was changed, notify user
  if (uniqueName !== requestedName) {
    const proceed = confirm(
      `A project named "${requestedName}" already exists.\n\n` +
      `Your project will be named "${uniqueName}" instead.\n\n` +
      `Continue?`
    );
    
    if (!proceed) {
      return; // User cancelled
    }
  }
  
  // Store in sessionStorage for later steps
  sessionStorage.setItem('projectName', uniqueName);
  sessionStorage.setItem('projectFolder', selectedFolderPath);
  
  console.log('Project Name:', uniqueName);
  console.log('Folder Path:', selectedFolderPath);
  
  // Proceed to method selection
  navigate('method');
}

window.initializeUpload = initializeUpload;
window.validateAndProceed = validateAndProceed;
