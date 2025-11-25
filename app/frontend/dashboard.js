// dashboard.js - Dashboard interactivity

// Store projects data - starts empty, users will add their own
let projects = [];

async function loadProjectsFromBackend() {
  try {
    const res = await fetch("http://localhost:8889/api/projects");

    // If backend is down or returns 500 → return empty list
    if (!res.ok) {
      console.warn("Backend returned non-OK status");
      return [];
    }

    const backendProjects = await res.json();

    // Convert backend format → frontend format
    return backendProjects.map(p => ({
      id: p.id,
      name: p.name,
      fullPath: p.folder_path,
      dataSource: p.data_source ?? "N/A",
      method: p.lw_method ?? "Unknown",
      dateCreated: new Date(p.created_at).toLocaleDateString(
        "en-US",
        { month: "2-digit", day: "2-digit", year: "numeric" }
      )
    }));

  } catch (err) {
    console.error("Failed to load projects:", err);
    return []; // safe fallback
  }
}
// Initialize dashboard when page loads
async function initializeDashboard() {
  // Load projects from backend instead of sample/demo data
  projects = await loadProjectsFromBackend();

  // Render them
  renderProjects(projects);
}

function setupDashboardOnce() {
  // Search box
  setupSearchListener();  // run only once
}
// Make functions available globally
window.initializeDashboard = initializeDashboard;
window.setupDashboardOnce = setupDashboardOnce;
window.loadProjectsFromBackend = loadProjectsFromBackend;
window.deleteProject = deleteProject;
window.duplicateProject = duplicateProject;
window.exportProject = exportProject;
window.addProject = addProject;
window.viewProjectResults = viewProjectResults;


// Render projects table
function renderProjects(projectsToRender) {
  const tbody = document.querySelector('.data-table tbody');

  if (projectsToRender.length === 0) {
    tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 40px; color: #7F8C8D;">
                    No projects found. Create a new project to get started!
                </td>
            </tr>
        `;
    return;
  }

  tbody.innerHTML = projectsToRender.map(project => `
        <tr data-project-id="${project.id}">
            <td>
                <a href="#" class="project-link" onclick="viewProjectResults(${project.id}); return false;">
                    ${project.name}
                </a>
            </td>
            <td>${project.method}</td>
            <td>
                <span class="data-source">
                    ${project.dataSource}
                    <span class="tooltip">${project.fullPath}</span>
                </span>
            </td>
            <td>${project.dateCreated}</td>
            <td style="text-align: center;">
                <span class="three-dots" onclick="toggleMenu(event)">⋮
                    <div class="actions-menu">
                        <div class="menu-item" onclick="event.stopPropagation(); exportProject(${project.id})">Export</div>
                        <div class="menu-item" onclick="event.stopPropagation(); deleteProject(${project.id})">Delete</div>
                        <div class="menu-item" onclick="event.stopPropagation(); duplicateProject(${project.id})">Duplicate</div>
                        <div class="menu-item" onclick="event.stopPropagation(); navigate('settings')">Project Settings</div>
                    </div>
                </span>
            </td>
        </tr>
    `).join('');
}

// Search functionality
function setupSearchListener() {
  const searchInput = document.querySelector('.search-input');

  searchInput.addEventListener('input', (e) => {
    const searchTerm = e.target.value.toLowerCase();

    const filteredProjects = projects.filter(project => {
      return project.name.toLowerCase().includes(searchTerm) ||
        project.method.toLowerCase().includes(searchTerm) ||
        project.dataSource.toLowerCase().includes(searchTerm);
    });

    renderProjects(filteredProjects);
  });
}

// Delete project
function deleteProject(projectId) {
  const project = projects.find(p => p.id === projectId);

  if (!project) return;

  // Show confirmation dialog
  if (confirm(`Are you sure you want to delete "${project.name}"?\n\nThis action cannot be undone.`)) {
    // Remove from array
    projects = projects.filter(p => p.id !== projectId);

    // Re-render table
    renderProjects(projects);

    // Show success message
    showNotification(`Project "${project.name}" deleted successfully`, 'success');
  }
}

// Duplicate project
function duplicateProject(projectId) {
  const project = projects.find(p => p.id === projectId);

  if (!project) return;

  // Create custom input dialog instead of prompt()
  createInputDialog(
    'Duplicate Project',
    'Enter a name for the duplicated project:',
    `${project.name} (Copy)`,
    (newName) => {
      if (!newName || newName.trim() === '') {
        return;
      }

      // Create new project with new ID
      const newProject = {
        ...project,
        id: Math.max(...projects.map(p => p.id)) + 1,
        name: newName.trim(),
        dateCreated: new Date().toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' })
      };

      // Add to array
      projects.push(newProject);

      // Re-render table
      renderProjects(projects);

      // Show success message
      showNotification(`Project "${newName}" created successfully`, 'success');
    }
  );
}

// Create custom input dialog
function createInputDialog(title, message, defaultValue, callback) {
  // Create dialog HTML
  const dialog = document.createElement('div');
  dialog.style.cssText = `
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
    `;

  dialog.innerHTML = `
        <div style="background: white; padding: 30px; border-radius: 8px; max-width: 400px; width: 90%;">
            <h3 style="margin-bottom: 15px; color: #2C3E50;">${title}</h3>
            <p style="margin-bottom: 20px; color: #7F8C8D;">${message}</p>
            <input type="text" id="inputDialogValue" value="${defaultValue}" style="width: 100%; padding: 10px; border: 1px solid #CED4DA; border-radius: 4px; margin-bottom: 20px;">
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button id="inputDialogCancel" class="btn btn-secondary">Cancel</button>
                <button id="inputDialogOK" class="btn btn-primary">OK</button>
            </div>
        </div>
    `;

  // Add to page
  document.body.appendChild(dialog);

  // Focus input and select text
  const input = dialog.querySelector('#inputDialogValue');
  input.focus();
  input.select();

  // Handle buttons
  dialog.querySelector('#inputDialogCancel').onclick = () => {
    document.body.removeChild(dialog);
  };

  dialog.querySelector('#inputDialogOK').onclick = () => {
    const value = input.value;
    document.body.removeChild(dialog);
    callback(value);
  };

  // Handle Enter key
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      const value = input.value;
      document.body.removeChild(dialog);
      callback(value);
    }
  });

  // Handle Escape key
  dialog.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.body.removeChild(dialog);
    }
  });
}

// Export project
function exportProject(projectId) {
  const project = projects.find(p => p.id === projectId);

  if (!project) return;

  // TODO: Implement real export functionality
  showNotification(`Exporting "${project.name}"... (Feature coming soon!)`, 'info');
  console.log('Export project:', project);
}

// Show notification
function showNotification(message, type = 'info') {
  // Create notification element
  const notification = document.createElement('div');
  notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: ${type === 'success' ? '#27ae60' : type === 'error' ? '#e74c3c' : '#3498DB'};
        color: white;
        padding: 15px 20px;
        border-radius: 4px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: slideIn 0.3s ease;
        max-width: 400px;
    `;
  notification.textContent = message;

  // Add animation
  const style = document.createElement('style');
  style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
    `;
  document.head.appendChild(style);

  // Add to page
  document.body.appendChild(notification);

  // Remove after 3 seconds
  setTimeout(() => {
    notification.style.animation = 'slideIn 0.3s ease reverse';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}
// Add a new project (will be called when user completes processing)
function addProject(projectData) {
  const newProject = {
    id: projects.length > 0 ? Math.max(...projects.map(p => p.id)) + 1 : 1,
    name: projectData.name,
    method: projectData.method,
    dataSource: projectData.dataSource,
    fullPath: projectData.fullPath,
    dateCreated: new Date().toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' })
  };

  projects.push(newProject);
  renderProjects(projects);
  showNotification(`Project "${newProject.name}" created successfully!`, 'success');

  return newProject.id;
}

function viewProjectResults(projectId) {
  const project = projects.find(p => p.id === projectId);
  if (!project) {
    console.error('Project not found:', projectId);
    return;
  }
  
  // Set project data in sessionStorage
  sessionStorage.setItem('projectFolder', project.fullPath);
  sessionStorage.setItem('projectName', project.name);
  
  // Navigate to results
  navigate('results');
}
