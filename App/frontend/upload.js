// upload.js
const { ipcRenderer } = require('electron');

function initializeUpload() {
  const btn = document.getElementById('uploadFolderBtn');
  if (!btn) return;

  btn.addEventListener('click', async () => {
    // 1) Let user pick a folder
    const result = await ipcRenderer.invoke('select-folder');
    if (!result || !result.success) return;

    const selectedFolderPath = result.path;

    // 2) Send folder to backend to create/organize the project
    try {
      const resp = await fetch('http://localhost:8889/manage/make_project', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folderPath: selectedFolderPath })
      });

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok || data?.success === false) {
        alert(data?.message || `Upload failed (${resp.status})`);
        return;
      }

      // 3) Stash folder + backend project ref for later
      sessionStorage.setItem('projectFolder', selectedFolderPath);
      if (data?.project_id) {
        sessionStorage.setItem('projectId', String(data.project_id));
      }
      if (data?.project_name) {
        sessionStorage.setItem('projectName', data.project_name);
      }

      // 4) Proceed to method selection screen
      navigate('method');
    } catch (e) {
      alert(`Could not reach backend: ${e.message}`);
    }
  });
}

// expose
window.initializeUpload = initializeUpload;
