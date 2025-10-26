// dashboard.js - Dashboard interactivity

// Store projects data - starts empty, users will add their own
let projects = [];

// For wireframe demo purposes only - add sample data
// TODO: Remove this in production - projects will come from actual user uploads
function loadSampleDataForDemo() {
    projects = [
        {
            id: 1,
            name: 'Algae Survey',
            method: 'Mobley Rho Method',
            dataSource: 'Algae_Survey',
            fullPath: '/user/Downloads/Algae_Survey/raw_images',
            dateCreated: '09/22/2025'
        },
        {
            id: 2,
            name: 'Coastal Water Quality',
            method: 'Black Pixel Method',
            dataSource: 'Coastal_Study',
            fullPath: '/user/Documents/Coastal_Study/multispectral_data',
            dateCreated: '09/15/2025'
        },
        {
            id: 3,
            name: 'Lake Michigan Study',
            method: 'Hedley Method',
            dataSource: 'Lake_Michigan',
            fullPath: '/user/Downloads/Lake_Michigan/hyperspectral_imgs',
            dateCreated: '09/08/2025'
        },
        {
            id: 4,
            name: 'Reef Monitoring 2025',
            method: 'Mobley Rho Method',
            dataSource: 'Reef_Data',
            fullPath: '/user/Downloads/Reef_Data/rgb_images',
            dateCreated: '08/30/2025'
        },
        {
            id: 5,
            name: 'Turbidity Assessment',
            method: 'Black Pixel Method',
            dataSource: 'Lake_Erie',
            fullPath: '/user/Downloads/Lake_Erie/raw_water_imgs',
            dateCreated: '08/22/2025'
        }
    ];
}

// Initialize dashboard when page loads
function initializeDashboard() {
    // Load sample data for demo - remove this in production
    loadSampleDataForDemo();
    
    renderProjects(projects);
    setupSearchListener();
}

// Make functions available globally
window.initializeDashboard = initializeDashboard;
window.deleteProject = deleteProject;

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
                <a href="#" class="project-link" onclick="navigate('results'); return false;">
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