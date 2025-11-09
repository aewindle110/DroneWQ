// upload.js — front-end only: send folder path to Flask; NO frontend validation
const { ipcRenderer } = require('electron');

async function handleUploadClick() {
  const btn = document.getElementById('uploadFolderBtn');
  if (!btn) return;

  try {
    btn.disabled = true;
    btn.textContent = 'Selecting…';

    // 1) Open native folder picker
    const res = await ipcRenderer.invoke('select-folder');
    if (!res || !res.success) {
      btn.disabled = false;
      btn.textContent = 'Upload Folder';
      return; // user cancelled
    }

    const folderPath = res.path;
    btn.textContent = 'Uploading…';

    // 2) Send directly to backend — NO validation here
    const r = await fetch('http://localhost:5000/manage/make_project', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folderPath })
    });

    const data = await r.json().catch(() => ({}));

    if (r.ok && data && data.success) {
      // show success and go to settings
      alert(data.message || 'Project created successfully.');
      if (typeof navigate === 'function') navigate('project-settings'); // adjust id if needed
    } else {
      const msg = (data && data.message) || `Backend error (${r.status})`;
      alert(msg);
    }
  } catch (err) {
    console.error(err);
    alert('Could not reach backend. Is Flask running on http://localhost:5000?');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Upload Folder';
    }
  }
}

function initializeUpload() {
  const btn = document.getElementById('uploadFolderBtn');
  if (btn && !btn.__wired) {
    btn.addEventListener('click', handleUploadClick);
    btn.__wired = true;
    console.log('[Upload] Click handler attached (no frontend validation)');
  }
}

window.initializeUpload = initializeUpload;
