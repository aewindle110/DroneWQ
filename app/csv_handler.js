/*
 * csv_handler.js
 * Author: Nidhi Khiantani
 * Description: Displays CSV data files as interactive tables with modal views
 */

// Parse CSV file into array of objects
function parseCSV(csvText) {
  const lines = csvText.trim().split('\n');
  if (lines.length === 0) return [];
  
  const headers = lines[0].split(',').map(h => h.trim());
  const rows = [];
  
  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',');
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index] ? values[index].trim() : '';
    });
    rows.push(row);
  }
  
  return { headers, rows };
}

// Build compact CSV card (thumbnail view)
function buildCSVCard(csvData, title, filePath) {
  const { headers, rows } = csvData;
  
  if (!headers || rows.length === 0) {
    return `
      <div class="csv-card">
        <div class="csv-card-header">
          <h5>${title}</h5>
          <span style="color: #7F8C8D; font-size: 13px;">No data</span>
        </div>
      </div>
    `;
  }
  
  return `
    <div class="csv-card">
      <div class="csv-card-header">
        <h5 style="margin: 0; color: #2C3E50; font-size: 16px; font-weight: 600;">${title}</h5>
        <button class="btn btn-primary" style="padding: 6px 12px; font-size: 13px;" onclick="viewCSVDetails('${filePath}', '${title}')">
           View
        </button>
      </div>
      <div class="csv-card-body">
        <div class="csv-stat">
          <span class="csv-stat-label">Rows:</span>
          <span class="csv-stat-value">${rows.length}</span>
        </div>
        <div class="csv-stat">
          <span class="csv-stat-label">Columns:</span>
          <span class="csv-stat-value">${headers.length}</span>
        </div>
        <div class="csv-stat">
          <span class="csv-stat-label">Size:</span>
          <span class="csv-stat-value">${getFileSize(filePath)}</span>
        </div>
      </div>
      <button class="btn btn-secondary" style="width: 100%; margin-top: 10px; padding: 8px;" onclick="showInFinder('${filePath}')">
         Show in Folder
        </button>
    </div>
  `;
}

// Get file size in a good format
function getFileSize(filePath) {
  try {
    const stats = fs.statSync(filePath);
    const bytes = stats.size;
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  } catch (err) {
    return 'N/A';
  }
}

function loadCSVData(folderPath) {
  const container = document.getElementById('csvDataContainer');
  if (!container) return;
  
  container.innerHTML = '<p style="color: #7F8C8D;">Loading CSV data...</p>';
  
  const csvFiles = [
    { file: 'metadata.csv', title: 'Image Metadata' },
    { file: 'median_rrs.csv', title: 'Median Rrs Values' },
    { file: 'median_rrs_and_wq.csv', title: 'Rrs and Water Quality Data' },
    { file: 'dls_ed.csv', title: 'Downwelling Irradiance' }
  ];
  
  let htmlContent = '<div class="csv-grid">';
  let foundFiles = 0;
  
  for (const csvFile of csvFiles) {
    const filePath = path.join(folderPath, csvFile.file);
    
    if (fs.existsSync(filePath)) {
      try {
        const csvText = fs.readFileSync(filePath, 'utf8');
        const csvData = parseCSV(csvText);
        htmlContent += buildCSVCard(csvData, csvFile.title, filePath);
        foundFiles++;
      } catch (err) {
        console.error(`Error reading ${csvFile.file}:`, err);
      }
    }
  }
  
  htmlContent += '</div>';
  
  if (foundFiles === 0) {
    container.innerHTML = `
      <div style="padding: 40px; text-align: center; color: #7F8C8D;">
        <p>No CSV data files found.</p>
        <p style="font-size: 13px; margin-top: 10px;">CSV files are generated after processing completes.</p>
      </div>
    `;
  } else {
    container.innerHTML = htmlContent;
  }
}

function showInFinder(filePath) {
  const { shell } = require('electron');
  shell.showItemInFolder(filePath);
}


// View CSV details in a modal
function viewCSVDetails(filePath, title) {
  try {
    const csvText = fs.readFileSync(filePath, 'utf8');
    const csvData = parseCSV(csvText);
    const { headers, rows } = csvData;
    
    // Create modal
    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.5);
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    `;
    
    const displayRows = rows.slice(0, 100);
    
    modal.innerHTML = `
      <div style="background: white; border-radius: 8px; max-width: 90%; max-height: 90%; display: flex; flex-direction: column; overflow: hidden;">
        <div style="padding: 20px; border-bottom: 1px solid #dee2e6; display: flex; justify-content: space-between; align-items: center;">
          <h4 style="margin: 0; color: #2C3E50;">${title}</h4>
          <button onclick="this.closest('div').parentElement.parentElement.remove()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #7F8C8D;">&times;</button>
        </div>
        <div style="overflow: auto; flex: 1; padding: 20px;">
          <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
            <thead style="background: #f8f9fa; position: sticky; top: 0;">
              <tr>
                ${headers.map(h => `<th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6; white-space: nowrap;">${h}</th>`).join('')}
              </tr>
            </thead>
            <tbody>
              ${displayRows.map(row => `
                <tr style="border-bottom: 1px solid #f1f3f5;">
                  ${headers.map(h => `<td style="padding: 8px; white-space: nowrap;">${row[h] || ''}</td>`).join('')}
                </tr>
              `).join('')}
            </tbody>
          </table>
          ${rows.length > 100 ? `<p style="color: #7F8C8D; margin-top: 15px; text-align: center;">Showing first 100 of ${rows.length} rows</p>` : ''}
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    
  // Close on background click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.remove();
    });
    
    //Close on Escape key
    const escapeHandler = (e) => {
      if (e.key === 'Escape') {
        modal.remove();
        document.removeEventListener('keydown', escapeHandler);
      }
    };
    document.addEventListener('keydown', escapeHandler);
    
  } catch (err) {
    alert('Error loading CSV: ' + err.message);
  }
}

window.viewCSVDetails = viewCSVDetails;

// Export functions
window.loadCSVData = loadCSVData;
window.showInFinder = showInFinder;

