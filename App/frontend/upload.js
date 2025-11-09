// upload.js - Handle folder upload and validation (Frontend only)

const { ipcRenderer } = require('electron');

// Initialize upload page
function initializeUpload() {
    setupUploadButtons();
}

// Make functions globally available
window.initializeUpload = initializeUpload;

// Set up upload button handlers
function setupUploadButtons() {
    const uploadFolderBtn = document.querySelector('.btn-primary');
    const manualUploadBtn = document.querySelector('.btn-secondary');
    
    if (uploadFolderBtn) {
        uploadFolderBtn.addEventListener('click', handleFolderUpload);
    }
    
    if (manualUploadBtn) {
        manualUploadBtn.addEventListener('click', handleManualUpload);
    }
}

// Handle folder upload
async function handleFolderUpload() {
    try {
        // Show loading state
        showUploadStatus('Selecting folder...', 'info');
        
        // Open folder selection dialog
        const result = await ipcRenderer.invoke('select-folder');
        
        if (!result.success) {
            showUploadStatus('No folder selected', 'info');
            return;
        }
        
        const folderPath = result.path;
        showUploadStatus(`Selected: ${folderPath}`, 'info');
        showUploadStatus(`Validating folder structure...`, 'info');
        
        // Validate folder structure
        const validation = await ipcRenderer.invoke('validate-folder', folderPath);
        
        if (!validation.valid) {
            showUploadStatus(validation.message, 'error');
            showFolderStructureHelp();
            return;
        }
        
        // Folder is valid - proceed to project settings
        showUploadStatus('Folder validated successfully!', 'success');
        
        // Store the folder path for use in project creation
        sessionStorage.setItem('selectedFolderPath', folderPath);
        sessionStorage.setItem('uploadMethod', 'folder');
        
        // Navigate to project settings after a brief delay
        setTimeout(() => {
            navigate('settings');
        }, 1000);
        
    } catch (error) {
        console.error('Folder upload error:', error);
        showUploadStatus('Error selecting folder: ' + error.message, 'error');
    }
}

// Handle manual file upload
async function handleManualUpload() {
    try {
        showUploadStatus('Selecting files...', 'info');
        
        // Open file selection dialog
        const result = await ipcRenderer.invoke('select-files');
        
        if (!result.success) {
            showUploadStatus('No files selected', 'info');
            return;
        }
        
        const filePaths = result.paths;
        showUploadStatus(`Selected ${filePaths.length} file(s)`, 'success');
        
        // Store file paths for manual organization
        sessionStorage.setItem('selectedFiles', JSON.stringify(filePaths));
        sessionStorage.setItem('uploadMethod', 'manual');
        
        // Navigate to settings (your teammate will handle file organization)
        setTimeout(() => {
            navigate('settings');
        }, 1000);
        
    } catch (error) {
        console.error('Manual upload error:', error);
        showUploadStatus('Error selecting files: ' + error.message, 'error');
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

// Get the selected folder/files data to send to backend
// Your teammate can call this function to get the data they need
function getUploadDataForBackend() {
    const uploadMethod = sessionStorage.getItem('uploadMethod');
    
    if (uploadMethod === 'folder') {
        return {
            method: 'folder',
            folderPath: sessionStorage.getItem('selectedFolderPath')
        };
    } else if (uploadMethod === 'manual') {
        return {
            method: 'manual',
            files: JSON.parse(sessionStorage.getItem('selectedFiles') || '[]')
        };
    }
    
    return null;
}

// Export function for your teammate's backend integration
window.getUploadDataForBackend = getUploadDataForBackend;