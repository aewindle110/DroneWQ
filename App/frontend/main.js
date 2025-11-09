const { app, BrowserWindow, Menu, ipcMain, dialog } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 700,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            enableRemoteModule: true
        }
    });

    // Load the wireframe HTML
    mainWindow.loadFile('wireframes/wireframe-v2.html');

    // Open DevTools in development (optional - remove for production)
    mainWindow.webContents.openDevTools();

    // Create application menu
    const menuTemplate = [
        {
            label: 'File',
            submenu: [
                {
                    label: 'New Project',
                    accelerator: 'CmdOrCtrl+N',
                    click: () => {
                        mainWindow.webContents.executeJavaScript("navigate('upload')");
                    }
                },
                {
                    label: 'Open Project',
                    accelerator: 'CmdOrCtrl+O',
                    click: () => {
                        console.log('Open project');
                    }
                },
                { type: 'separator' },
                {
                    label: 'Exit',
                    accelerator: 'CmdOrCtrl+Q',
                    click: () => {
                        app.quit();
                    }
                }
            ]
        },
        {
            label: 'Edit',
            submenu: [
                { role: 'undo' },
                { role: 'redo' },
                { type: 'separator' },
                { role: 'cut' },
                { role: 'copy' },
                { role: 'paste' }
            ]
        },
        {
            label: 'View',
            submenu: [
                { role: 'reload' },
                { role: 'toggleDevTools' },
                { type: 'separator' },
                { role: 'resetZoom' },
                { role: 'zoomIn' },
                { role: 'zoomOut' }
            ]
        },
        {
            label: 'Help',
            submenu: [
                {
                    label: 'Documentation',
                    click: () => {
                        console.log('Open docs');
                    }
                },
                {
                    label: 'About',
                    click: () => {
                        console.log('About DroneWQ');
                    }
                }
            ]
        }
    ];

    const menu = Menu.buildFromTemplate(menuTemplate);
    Menu.setApplicationMenu(menu);

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

// App lifecycle
app.whenReady().then(() => {
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// IPC Handlers for folder selection
ipcMain.handle('select-folder', async (event) => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory'],
        title: 'Select your data folder',
        buttonLabel: 'Select Folder'
    });
    
    if (!result.canceled && result.filePaths.length > 0) {
        return { success: true, path: result.filePaths[0] };
    }
    return { success: false };
});

// IPC Handler for manual file upload (individual files)
ipcMain.handle('select-files', async (event) => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openFile', 'multiSelections'],
        title: 'Select your data files',
        buttonLabel: 'Select Files',
        filters: [
            { name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'tif', 'tiff', 'raw'] },
            { name: 'All Files', extensions: ['*'] }
        ]
    });
    
    if (!result.canceled && result.filePaths.length > 0) {
        return { success: true, paths: result.filePaths };
    }
    return { success: false };
});

// IPC Handler to validate folder structure
ipcMain.handle('validate-folder', async (event, folderPath) => {
    const fs = require('fs');
    const requiredSubfolders = ['panel', 'raw_sky_imgs', 'raw_water_imgs', 'align_img'];
    
    try {
        const contents = fs.readdirSync(folderPath);
        const missingFolders = requiredSubfolders.filter(folder => !contents.includes(folder));
        
        if (missingFolders.length === 0) {
            return { valid: true, path: folderPath };
        } else {
            return { 
                valid: false, 
                message: `Missing required folders: ${missingFolders.join(', ')}`,
                missingFolders 
            };
        }
    } catch (error) {
        return { valid: false, message: `Error reading folder: ${error.message}` };
    }
});

// IPC Handler to prepare data for backend
ipcMain.handle('process-data', async (event, projectData) => {
    console.log('Data ready for backend processing:', projectData);
    
    // For now, return success so the frontend flow works
    return { 
        success: true, 
        message: 'Ready for backend processing',
        projectData: projectData
    };
});