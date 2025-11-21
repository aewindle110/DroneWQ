// frontend/upload.js
const { ipcRenderer } = require('electron');

function initializeUpload() {
  const btn = document.getElementById('uploadFolderBtn');
  if (!btn) return;

  btn.addEventListener('click', async () => {
    try {
      const res = await ipcRenderer.invoke('select-folder');
      if (!res || !res.success) return;

      const folderPath = res.path;
      // Persist for later steps
      sessionStorage.setItem('projectFolder', folderPath);


      const projectName = folderPath.split(/[\\/]/).pop() || 'My Project';
      sessionStorage.setItem('projectName', projectName);

      // Tell backend to make project — backend expects "folderPath"
      const resp = await fetch('http://localhost:8889/api/projects/check_folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folderPath })
      });

      if (!resp.ok) {
        const msg = await resp.text();
        alert(`Backend error (check_folder): ${msg || resp.statusText}`);
        return;
      }

      navigate('method');
    } catch (err) {
      console.error(err);
      alert('Could not select folder.');
    }
  });
}

window.initializeUpload = initializeUpload;
