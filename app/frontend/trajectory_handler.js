/**
 * trajectory_handler.js
 * Author: Nidhi Khiantani
 * Description: Displays flight metadata summary and trajectory visualization plot
 */

function loadTrajectoryData(folderPath) {
  loadFlightData(folderPath);
  loadFlightPlanImage(folderPath);
}

// Load flight data summary from metadata.csv
function loadFlightData(folderPath) {
  const summaryContainer = document.getElementById('flightDataSummary');
  if (!summaryContainer) return;
  
  try {
    const metadataPath = path.join(folderPath, 'metadata.csv');
    
    if (!fs.existsSync(metadataPath)) {
      summaryContainer.innerHTML = '<p style="color: #7F8C8D;">Flight data not available.</p>';
      return;
    }
    
    // Read and parse CSV
    const csvText = fs.readFileSync(metadataPath, 'utf8');
    const lines = csvText.trim().split('\n');
    
    if (lines.length < 2) {
      summaryContainer.innerHTML = '<p style="color: #7F8C8D;">No flight data found.</p>';
      return;
    }
    
    // Parse header and rows
    const headers = lines[0].split(',').map(h => h.trim());
    const rows = lines.slice(1).map(line => {
      const values = line.split(',').map(v => v.trim());
      const row = {};
      headers.forEach((header, i) => {
        row[header] = values[i];
      });
      return row;
    });
    
    console.log('Parsed metadata:', rows[0]); // Debug
    
    // Extract altitude, lat/long, yaw ranges
   const altitudes = rows.map(r => parseFloat(r.Altitude)).filter(v => !isNaN(v));
    const latitudes = rows.map(r => parseFloat(r.Latitude)).filter(v => !isNaN(v));
    const longitudes = rows.map(r => parseFloat(r.Longitude)).filter(v => !isNaN(v));
    const yaws = rows.map(r => parseFloat(r.Yaw)).filter(v => !isNaN(v));
        
    console.log('Altitudes:', altitudes.slice(0, 5)); // Debug
    console.log('Latitudes:', latitudes.slice(0, 5)); // Debug
    
    // Check if we have valid data
    if (altitudes.length === 0 || latitudes.length === 0 || longitudes.length === 0) {
      summaryContainer.innerHTML = '<p style="color: #e74c3c;">Unable to parse flight data.</p>';
      return;
    }
    
    const altMin = Math.min(...altitudes).toFixed(1);
    const altMax = Math.max(...altitudes).toFixed(1);
    const latMin = Math.min(...latitudes).toFixed(4);
    const latMax = Math.max(...latitudes).toFixed(4);
    const longMin = Math.min(...longitudes).toFixed(4);
    const longMax = Math.max(...longitudes).toFixed(4);
    
    let yawDisplay = 'N/A';
    if (yaws.length > 0) {
      const yawMin = Math.min(...yaws).toFixed(0);
      const yawMax = Math.max(...yaws).toFixed(0);
      yawDisplay = `${yawMin}-${yawMax}°`;
    }
    
    // Display summary
    summaryContainer.innerHTML = `
      <div class="data-row">
        <span class="data-label">Altitude:</span>
        <span>${altMin}-${altMax} m</span>
      </div>
      <div class="data-row">
        <span class="data-label">Latitude Range:</span>
        <span>${latMin}° - ${latMax}°</span>
      </div>
      <div class="data-row">
        <span class="data-label">Longitude Range:</span>
        <span>${longMin}° - ${longMax}°</span>
      </div>
      <div class="data-row">
        <span class="data-label">Yaw:</span>
        <span>${yawDisplay}</span>
      </div>
      <div class="data-row">
        <span class="data-label">Total Images:</span>
        <span>${rows.length}</span>
      </div>
    `;
    
  } catch (err) {
    console.error('Error loading flight data:', err);
    summaryContainer.innerHTML = '<p style="color: #e74c3c;">Error loading flight data.</p>';
  }
}

// Load flight plan image
function loadFlightPlanImage(folderPath) {
  const imageContainer = document.getElementById('flightPlanImage');
  if (!imageContainer) return;
  
  try {
    const imagePath = path.join(folderPath, 'result', 'flight_plan.png');
    
    if (!fs.existsSync(imagePath)) {
      imageContainer.innerHTML = '<p style="color: #7F8C8D;">Flight plan image not available.</p>';
      return;
    }
    
    const url = pathToFileURL(imagePath).href;
    imageContainer.innerHTML = `
      <img 
        src="${url}" 
        alt="Flight Plan" 
        tabindex="0"
        role="button"
        style="width: 100%; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); cursor: pointer;" 
      />
    `;
    
    // Add keyboard support
    const img = imageContainer.querySelector('img');
    img.addEventListener('click', () => openImageModal(url, 'Flight Plan'));
    img.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openImageModal(url, 'Flight Plan');
      }
    });
    
  } catch (err) {
    console.error('Error loading flight plan image:', err);
    imageContainer.innerHTML = '<p style="color: #e74c3c;">Error loading flight plan image.</p>';
  }
}

window.loadTrajectoryData = loadTrajectoryData;