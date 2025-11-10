// frontend/main.js
const { app, BrowserWindow, Menu, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let flaskProcess;

/* ---------- Flask child process helpers ---------- */
function pythonCmd() {
  if (process.env.PYTHON_BIN) return process.env.PYTHON_BIN;
  return process.platform === 'win32' ? 'python' : 'python3';
}

function startFlask() {
  const backendDir = path.join(__dirname, '..', 'backend'); // adjust if needed
  const scriptPath = path.join(backendDir, 'app.py');

  const env = { ...process.env };
 
  flaskProcess = spawn(pythonCmd(), [scriptPath], {
    cwd: backendDir,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  flaskProcess.stdout.on('data', d => console.log(`[flask] ${d}`.trim()));
  flaskProcess.stderr.on('data', d => console.error(`[flask ERR] ${d}`.trim()));
  flaskProcess.on('exit', (code, sig) => {
    console.log(`[flask] exited code=${code} signal=${sig}`);
  });
}

function waitForBackend(timeoutMs = 15000, intervalMs = 300) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const ping = () => {
      const req = http.get('http://127.0.0.1:5000/health', res => {
        res.destroy();
        if (res.statusCode === 200) return resolve();
        if (Date.now() > deadline) return reject(new Error('Backend not ready (HTTP status)'));
        setTimeout(ping, intervalMs);
      });
      req.on('error', () => {
        if (Date.now() > deadline) return reject(new Error('Backend not reachable'));
        setTimeout(ping, intervalMs);
      });
    };
    ping();
  });
}

/* ---------- BrowserWindow & Menu ---------- */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });

  // Load your HTML
  mainWindow.loadFile(path.join(__dirname, 'wireframes', 'wireframe-v2.html'));
  mainWindow.webContents.openDevTools();

  // Menu (keep one)
  const menuTemplate = [
    {
      label: 'File',
      submenu: [
        {
          label: 'New Project',
          accelerator: 'CmdOrCtrl+N',
          click: () => mainWindow.webContents.executeJavaScript("navigate('upload')"),
        },
        {
          label: 'Open Project',
          accelerator: 'CmdOrCtrl+O',
          click: () => console.log('Open project'),
        },
        { type: 'separator' },
        { role: 'quit', label: 'Exit' },
      ],
    },
    {
      label: 'Edit',
      submenu: [{ role: 'undo' }, { role: 'redo' }, { type: 'separator' }, { role: 'cut' }, { role: 'copy' }, { role: 'paste' }],
    },
    {
      label: 'View',
      submenu: [{ role: 'reload' }, { role: 'toggleDevTools' }, { type: 'separator' }, { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' }],
    },
    {
      label: 'Help',
      submenu: [
        { label: 'Documentation', click: () => console.log('Open docs') },
        { label: 'About', click: () => console.log('About DroneWQ') },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(menuTemplate);
  Menu.setApplicationMenu(menu);

  mainWindow.on('closed', () => { mainWindow = null; });
}

/* ---------- IPC (keep single definitions) ---------- */
ipcMain.handle('select-folder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Select your data folder',
    buttonLabel: 'Select Folder',
  });
  if (!result.canceled && result.filePaths.length > 0) return { success: true, path: result.filePaths[0] };
  return { success: false };
});

ipcMain.handle('select-files', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile', 'multiSelections'],
    title: 'Select your data files',
    buttonLabel: 'Select Files',
    filters: [
      { name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'tif', 'tiff', 'raw'] },
      { name: 'All Files', extensions: ['*'] },
    ],
  });
  if (!result.canceled && result.filePaths.length > 0) return { success: true, paths: result.filePaths };
  return { success: false };
});

/* ---------- App lifecycle (single set) ---------- */
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(async () => {
    startFlask();
    try {
      await waitForBackend();
      console.log('Flask is ready.');
    } catch (e) {
      console.error(e);
      dialog.showErrorBox('Backend Error', 'Flask backend did not start. Check console for logs.');
    }
    createWindow();
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });

  app.on('before-quit', () => {
    if (flaskProcess && !flaskProcess.killed) {
      try { process.platform === 'win32' ? flaskProcess.kill() : flaskProcess.kill('SIGTERM'); } catch {}
    }
  });

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
  });
}
