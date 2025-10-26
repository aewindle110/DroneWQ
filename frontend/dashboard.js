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