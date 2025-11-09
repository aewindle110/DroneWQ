// upload.js - Handle folder upload with drag-and-drop support

const { ipcRenderer } = require('electron');

// Initialize upload page
function initializeUpload() {
    setupUploadButton();
    setupDragAndDrop();
}

// Make functions globally available
window.initializeUpload = initializeUpload;

// Set up single upload button
function setupUploadButton() {
    const uploadBtn = document.querySelector('.btn-primary');
    
    if (uploadBtn) {
        uploadBtn.addEventListener('click', handleFolderUpload);
    }
}

// Set up drag and drop
function setupDragAndDrop() {
    const uploadSection = document.querySelector('.upload-section');
    
    if (!uploadSection) return;
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadSection.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop area when dragging over
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadSection.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadSection.addEventListener(eventName, unhighlight, false);
    });
    
    // Handle dropped files
    uploadSection.addEventListener('drop', handleDrop, false);
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function highlight(e) {
    const uploadSection = document.querySelector('.upload-section');
    uploadSection.style.background = '#e3f2fd';
    uploadSection.style.borderColor = '#2196F3';
}

function unhighlight(e) {
    const uploadSection = document.querySelector('.upload-section');
    uploadSection.style.background = '';
    uploadSection.style.borderColor = '';
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const items = dt.items;
    
    if (items && items.length > 0) {
        // Get the first item (folder)
        const item = items[0];
        
        if (item.kind === 'file') {
            const entry = item.webkitGetAsEntry();
            
            if (entry && entry.isDirectory) {
                // User dropped a folder
                const folderPath = entry.fullPath;
                processFolderPath(folderPath);
            } else {
                showUploadStatus('Please drop a folder, not individual files', 'error');
            }
        }
    }
}

// Handle folder upload via button click
async function handleFolderUpload() {
    try {
        showUploadStatus('Selecting folder...', 'info');
        
        // Open folder selection dialog
        const result = await ipcRenderer.invoke('select-folder');
        
        if (!result.success) {
            showUploadStatus('No folder selected', 'info');
            return;
        }
        
        const folderPath = result.path;
        processFolderPath(folderPath);
        
    } catch (error) {
        console.error('Folder upload error:', error);
        showUploadStatus('Error selecting folder: ' + error.message, 'error');
    }
}

// Process the selected folder path
async function processFolderPath(folderPath) {
    showUploadStatus(`Selected: ${folderPath}`, 'info');
    showUploadStatus(`Validating folder structure...`, 'info');
    
    // Validate folder structure
    const validation = await ipcRenderer.invoke('validate-folder', folderPath);
    
    if (!validation.valid) {
        showUploadStatus(validation.message, 'error');
        showFolderStructureHelp();
        return;
    }
    
    // Folder is valid - send to backend
    showUploadStatus('Folder validated! Sending to backend...', 'success');
    
    try {
        // Send to Flask backend
        const response = await fetch('http://localhost:5000/manage/make_project', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                folderPath: folderPath 
            })
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            // Show success message from backend
            const successMessage = result.message || 'Project created successfully!';
            showUploadStatus(successMessage, 'success');
            
            // Store folder path for settings page
            sessionStorage.setItem('projectFolderPath', folderPath);
            
            // Navigate to settings page after brief delay
            setTimeout(() => {
                navigate('settings');
            }, 1500);
            
        } else {
            // Show error message from backend
            const errorMessage = result.message || result.error || 'Unknown error occurred';
            showUploadStatus('Error: ' + errorMessage, 'error');
        }
        
    } catch (error) {
        console.error('Failed to connect to backend:', error);
        showUploadStatus('Could not connect to Flask server. Is it running on port 5000?', 'error');
    }
}

// Show upload status message
function showUploadStatus(message, type = 'info') {
    // Remove any existing status messages
    const existingStatus = document.querySelector('.upload-status');
    if (existingStatus) {
        existingStatus.remove();
    }
    
    // Create new status message
    const statusDiv = document.createElement('div');
    statusDiv.className = 'upload-status';
    statusDiv.style.cssText = `
        margin-top: 20px;
        padding: 15px 20px;
        border-radius: 4px;
        text-align: center;
        font-size: 14px;
        animation: fadeIn 0.3s ease;
        ${type === 'success' ? 'background: #d4edda; color: #155724; border: 1px solid #c3e6cb;' : ''}
        ${type === 'error' ? 'background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;' : ''}
        ${type === 'info' ? 'background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb;' : ''}
    `;
    statusDiv.textContent = message;
    
    // Insert after the upload section
    const uploadSection = document.querySelector('.upload-section');
    if (uploadSection) {
        uploadSection.appendChild(statusDiv);
    }
}

// Show folder structure help
function showFolderStructureHelp() {
    const helpDiv = document.createElement('div');
    helpDiv.style.cssText = `
        margin-top: 20px;
        padding: 20px;
        background: #fff3cd;
        border: 1px solid #ffeeba;
        border-radius: 4px;
        color: #856404;
    `;
    
    helpDiv.innerHTML = `
        <h4 style="margin-top: 0; color: #856404;">Required Folder Structure:</h4>
        <p>Your data folder must contain these subfolders:</p>
        <ul style="margin-bottom: 10px;">
            <li><strong>panel/</strong> - Panel reference images</li>
            <li><strong>raw_sky_imgs/</strong> - Sky images for glint correction</li>
            <li><strong>raw_water_imgs/</strong> - Water surface images</li>
            <li><strong>align_img/</strong> - Alignment reference images</li>
        </ul>
        <p style="margin-bottom: 0;">Please organize your files according to this structure and try again.</p>
    `;
    
    const uploadSection = document.querySelector('.upload-section');
    if (uploadSection) {
        // Remove existing help if present
        const existingHelp = document.querySelector('.folder-structure-help');
        if (existingHelp) existingHelp.remove();
        
        helpDiv.className = 'folder-structure-help';
        uploadSection.appendChild(helpDiv);
    }
}