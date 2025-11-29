// frontend/images_handler.js

// Load and display ALL images from lt_thumbnails folder
function loadImages(folderPath) {
  const imagesContainer = document.querySelector('.images-grid');
  if (!imagesContainer) return;
  
  // Clear existing images
  imagesContainer.innerHTML = '<p style="color: #7F8C8D; padding: 40px; text-align: center;">Loading images...</p>';
  
  try {
    const imagesDir = path.join(folderPath, 'lt_thumbnails');
    
    // Check if directory exists
    if (!fs.existsSync(imagesDir)) {
      imagesContainer.innerHTML = `
        <div style="padding: 40px; text-align: center; color: #7F8C8D;">
          <p>No images found.</p>
          <p style="font-size: 13px; margin-top: 10px;">Images should be in: lt_thumbnails/</p>
        </div>
      `;
      return;
    }
    
    // Read all image files
    const files = fs.readdirSync(imagesDir);
    const imageFiles = files.filter(f => 
      f.toLowerCase().endsWith('.jpg') || 
      f.toLowerCase().endsWith('.jpeg') || 
      f.toLowerCase().endsWith('.png') || 
      f.toLowerCase().endsWith('.tif') || 
      f.toLowerCase().endsWith('.tiff') ||
      f.toLowerCase().endsWith('.webp')
    );
    
    console.log(`Found ${imageFiles.length} images`);
    
    if (imageFiles.length === 0) {
      imagesContainer.innerHTML = `
        <div style="padding: 40px; text-align: center; color: #7F8C8D;">
          <p>No image files found in lt_thumbnails/</p>
        </div>
      `;
      return;
    }
    
    // Clear container
    imagesContainer.innerHTML = '';
    
    // Variables for arrow key navigation
    let currentFocusIndex = 0;
    const imageBoxes = [];
    
    // Load ALL images with keyboard support
    imageFiles.forEach((filename, index) => {
      const imagePath = path.join(imagesDir, filename);
      const url = pathToFileURL(imagePath).href;
      
      const imageBox = document.createElement('div');
      imageBox.className = 'image-box';
      imageBox.tabIndex = index === 0 ? 0 : -1; // Only first is tabbable
      imageBox.dataset.index = index;
      
      imageBox.innerHTML = `
        <img 
          src="${url}" 
          alt="${filename}"
          class="image-thumbnail"
        />
        <div class="image-filename">${filename}</div>
      `;
      
      imageBox.addEventListener('click', () => openImageModal(url, filename));
      imageBox.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          openImageModal(url, filename);
        }
      });
      
      imagesContainer.appendChild(imageBox);
      imageBoxes.push(imageBox);
    });
    
    // Arrow key navigation
    imagesContainer.addEventListener('keydown', (e) => {
      const cols = 6; // 6 images per row
      
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
        e.preventDefault();
        
        let newIndex = currentFocusIndex;
        
        if (e.key === 'ArrowRight') newIndex++;
        if (e.key === 'ArrowLeft') newIndex--;
        if (e.key === 'ArrowDown') newIndex += cols;
        if (e.key === 'ArrowUp') newIndex -= cols;
        
        // Bounds check
        if (newIndex >= 0 && newIndex < imageBoxes.length) {
          imageBoxes[currentFocusIndex].tabIndex = -1;
          currentFocusIndex = newIndex;
          imageBoxes[currentFocusIndex].tabIndex = 0;
          imageBoxes[currentFocusIndex].focus();
        }
      }
    });
    
    // Add count display
    const countDisplay = document.createElement('div');
    countDisplay.style.cssText = 'text-align: center; padding: 20px; color: #7F8C8D; font-size: 14px; grid-column: 1 / -1;';
    countDisplay.textContent = `${imageFiles.length} images loaded`;
    imagesContainer.appendChild(countDisplay);
    
  } catch (err) {
    console.error('Error loading images:', err);
    imagesContainer.innerHTML = `
      <div style="padding: 40px; text-align: center; color: #e74c3c;">
        <p>Error loading images: ${err.message}</p>
      </div>
    `;
  }
}

// Open image in modal
function openImageModal(imageUrl, filename) {
  const modal = document.createElement('div');
  modal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.9);
    z-index: 10000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px;
  `;
  
  modal.innerHTML = `
    <div style="position: relative; max-width: 90%; max-height: 90%; display: flex; flex-direction: column; align-items: center;">
      <div style="position: absolute; top: -40px; right: 0; display: flex; gap: 15px; align-items: center;">
        <span style="color: white; font-size: 14px;">${filename}</span>
        <button onclick="this.closest('div').parentElement.parentElement.remove()" 
                style="background: white; border: none; border-radius: 50%; width: 36px; height: 36px; font-size: 24px; cursor: pointer; color: #333;">
          &times;
        </button>
      </div>
      <img src="${imageUrl}" style="max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 4px;" />
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Close on background click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.remove();
  });
  
  // Close on Escape key
  const escapeHandler = (e) => {
    if (e.key === 'Escape') {
      modal.remove();
      document.removeEventListener('keydown', escapeHandler);
    }
  };
  document.addEventListener('keydown', escapeHandler);
}

window.loadImages = loadImages;
window.openImageModal = openImageModal;