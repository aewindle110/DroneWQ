// frontend/mosaic_handler.js

function loadMosaicImage(folderPath) {
  const mosaicContainer = document.getElementById('mosaicContainer');
  if (!mosaicContainer) return;
  
  try {
    // Check for different possible file extensions
    const possibleFiles = ['mosaic.png', 'mosaic.jpg', 'mosaic.jpeg', 'mosaic.tif', 'mosaic.tiff'];
    let mosaicPath = null;
    
    const resultDir = path.join(folderPath, 'result');
    
    for (const filename of possibleFiles) {
      const testPath = path.join(resultDir, filename);
      if (fs.existsSync(testPath)) {
        mosaicPath = testPath;
        break;
      }
    }
    
    if (!mosaicPath) {
      mosaicContainer.innerHTML = `
        <div style="padding: 60px; text-align: center; color: #7F8C8D;">
          <p style="font-size: 18px; margin-bottom: 10px;">No mosaic available</p>
          <p style="font-size: 14px;">Mosaic will be generated if selected during processing.</p>
        </div>
      `;
      return;
    }
    
    const url = pathToFileURL(mosaicPath).href;
    mosaicContainer.innerHTML = `
      <img 
        src="${url}" 
        alt="Mosaic" 
        id="mosaicImage"
        tabindex="0"
        role="button"
        style="max-width: 100%; max-height: 70vh; object-fit: contain; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); display: block; margin: 0 auto; cursor: pointer;" 
      />
    `;
    
    // Add keyboard support
    const img = mosaicContainer.querySelector('img');
    img.addEventListener('click', () => openImageModal(url, 'Mosaic'));
    img.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openImageModal(url, 'Mosaic');
      }
    });
    
  } catch (err) {
    console.error('Error loading mosaic:', err);
    mosaicContainer.innerHTML = `
      <div style="padding: 60px; text-align: center; color: #e74c3c;">
        <p>Error loading mosaic image</p>
      </div>
    `;
  }
}

window.loadMosaicImage = loadMosaicImage;