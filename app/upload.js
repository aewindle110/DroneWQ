// frontend/upload.js
const { ipcRenderer } = require('electron');

let selectedFolderPath = null;
let projectName = null;
let uploadInitialized = false; // Flag to prevent duplicate listeners
let projectNameInitialized = false; // Flag for project name screen

// Initialize project name screen (Screen 1)
function initializeProjectName() {
  const projectNameInput = document.getElementById('projectNameInput');
  const nextBtn = document.getElementById('projectNameNextBtn');
  
  if (!projectNameInput || !nextBtn) return;
  
  // Check if we already have a project name (user went back)
  const savedName = sessionStorage.getItem('projectName');
  if (savedName) {
    projectNameInput.value = savedName;
  } else {
    projectNameInput.value = '';
  }
  
  // Enable/disable Next button
  function checkNextButton() {
    nextBtn.disabled = projectNameInput.value.trim() === '';
  }
  
  checkNextButton();
  
  // Only add listeners once
  if (projectNameInitialized) return;
  projectNameInitialized = true;
  
  projectNameInput.addEventListener('input', checkNextButton);
  
  // Add click handler to Next button
  nextBtn.addEventListener('click', function() {
    proceedToUpload();
  });
  
  // Handle Enter key
  projectNameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !nextBtn.disabled) {
      proceedToUpload();
    }
  });
  
  // Focus the input
  setTimeout(() => projectNameInput.focus(), 100);
}

// Check if project name already exists and modify if needed
async function getUniqueProjectName(baseName) {
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
    return baseName;
  }
}

// Proceed from project name screen to upload screen
async function proceedToUpload() {
  const projectNameInput = document.getElementById('projectNameInput');
  
  if (!projectNameInput || projectNameInput.value.trim() === '') {
    alert('Please enter a project name');
    return;
  }
  
  // Get unique project name (add suffix if duplicate)
  const requestedName = projectNameInput.value.trim();
  const uniqueName = await getUniqueProjectName(requestedName);
  
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
  
  // Store project name
  projectName = uniqueName;
  sessionStorage.setItem('projectName', uniqueName);
  
  // Show it on the upload screen
  const displayNameSpan = document.getElementById('displayProjectName');
  if (displayNameSpan) {
    displayNameSpan.textContent = uniqueName;
  }
  
  // Navigate to upload screen
  navigate('upload');
}

// Initialize upload screen (Screen 2)
function initializeUpload() {
  const btn = document.getElementById('uploadFolderBtn');
  const nextBtn = document.getElementById('uploadNextBtn');
  const displayDiv = document.getElementById('selectedFolderDisplay');
  const pathSpan = document.getElementById('selectedFolderPath');
  
  if (!btn) return;
  
  // Check if we already have a folder selected (user went back)
  const savedFolder = sessionStorage.getItem('projectFolder');
  if (savedFolder) {
    selectedFolderPath = savedFolder;
    if (displayDiv && pathSpan) {
      pathSpan.textContent = savedFolder;
      displayDiv.style.display = 'block';
    }
    if (nextBtn) nextBtn.disabled = false;
  } else {
    selectedFolderPath = null;
    if (displayDiv) displayDiv.style.display = 'none';
    if (nextBtn) nextBtn.disabled = true;
  }
  
  // Display project name
  const displayNameSpan = document.getElementById('displayProjectName');
  const savedName = sessionStorage.getItem('projectName');
  if (displayNameSpan && savedName) {
    displayNameSpan.textContent = savedName;
    projectName = savedName;
  }
  
  // Only add listener once
  if (uploadInitialized) return;
  uploadInitialized = true;
  
  btn.addEventListener('click', async () => {
    try {
      const res = await ipcRenderer.invoke('select-folder');
      if (!res || !res.success) return;
      
      selectedFolderPath = res.path;
      
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
        const displayDiv = document.getElementById('selectedFolderDisplay');
        const nextBtn = document.getElementById('uploadNextBtn');
        if (displayDiv) displayDiv.style.display = 'none';
        if (nextBtn) nextBtn.disabled = true;
        return;
      }
      
      // Show selected folder
      const displayDiv = document.getElementById('selectedFolderDisplay');
      const pathSpan = document.getElementById('selectedFolderPath');
      const nextBtn = document.getElementById('uploadNextBtn');
      
      if (displayDiv && pathSpan) {
        pathSpan.textContent = selectedFolderPath;
        displayDiv.style.display = 'block';
      }
      
      // Save to session
      sessionStorage.setItem('projectFolder', selectedFolderPath);
      
      // Enable next button
      if (nextBtn) nextBtn.disabled = false;
      
    } catch (err) {
      console.error(err);
      alert('Could not select folder.');
      selectedFolderPath = null;
      const nextBtn = document.getElementById('uploadNextBtn');
      if (nextBtn) nextBtn.disabled = true;
    }
  });
}

// Proceed to method selection screen
function proceedToMethod() {
  if (!selectedFolderPath) {
    alert('Please select a data folder');
    return;
  }
  
  if (!projectName) {
    projectName = sessionStorage.getItem('projectName');
  }
  
  // Folder path already saved to session
  console.log('Project Name:', projectName);
  console.log('Folder Path:', selectedFolderPath);
  
  // Navigate to method selection
  navigate('method');
}

window.initializeProjectName = initializeProjectName;
window.initializeUpload = initializeUpload;
window.proceedToUpload = proceedToUpload;
window.proceedToMethod = proceedToMethod;