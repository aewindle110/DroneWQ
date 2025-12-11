/**
 * app_ui.js
 * Author: Nidhi Khiantani
 * Description: Main navigation controller that manages screen transitions and coordinates between different modules
 */

// Masking input Logic 
document.addEventListener("DOMContentLoaded", function () {
  const maskingSelect = document.getElementById("maskingSelect");
  if (maskingSelect) {
    maskingSelect.addEventListener("change", function () {
      const valueThresholdInputs = document.getElementById("valueThresholdInputs");
      const stdThresholdInputs = document.getElementById("stdThresholdInputs");
      if (!valueThresholdInputs || !stdThresholdInputs) return;

      valueThresholdInputs.style.display = "none";
      stdThresholdInputs.style.display = "none";

      if (this.value === "value_threshold") {
        valueThresholdInputs.style.display = "block";
      } else if (this.value === "std_threshold") {
        stdThresholdInputs.style.display = "block";
      }
    });
  }
});


// Navigation
function navigate(screen, fromScreen) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.getElementById(screen).classList.add("active");

  if (screen === "home") {
    if (fromScreen !== "results") {
      if (typeof clearProjectData === "function") {
        clearProjectData();
        console.log("[Dashboard] All project data cleared");
      }
    }
    if (typeof initializeDashboard === "function") {
      initializeDashboard();
      console.log("[Dashboard] Projects reloaded");
    }
  }

  if (screen === "project-name") {
    setTimeout(() => {
      if (typeof initializeProjectName === "function") {
        initializeProjectName();
        console.log("[ProjectName] initialized");
      }
    }, 100);
  }

  if (screen === "upload") {
    setTimeout(() => {
      if (typeof initializeUpload === "function") {
        initializeUpload();
        console.log("[Upload] initialized");
      }
    }, 100);
  }

  if (screen === "method") {
    setTimeout(() => {
      if (typeof initializeProjectSettings === "function") {
        initializeProjectSettings();
        console.log("[Method] initialized with validation");
      }
    }, 100);
  }

  if (screen === "outputs") {
    setTimeout(() => {
      if (typeof initializeProjectSettings === "function") {
        initializeProjectSettings();
        console.log("[Outputs] initialized");
      }
    }, 100);
  }

  if (screen === "results") {
    setTimeout(async () => {
      const projectId = sessionStorage.getItem("currentProjectId");
      if (!projectId) {
        console.error("No project ID found");
        return;
      }

      try {
        const response = await fetch(`http://localhost:8889/api/projects/${projectId}`);
        if (!response.ok) throw new Error("Failed to fetch project");

        const project = await response.json();
        if (!project) {
          console.error("Project not found in database");
          return;
        }

        const dateCreated = new Date(project.created_at).toLocaleDateString(
          "en-US",
          { month: "2-digit", day: "2-digit", year: "numeric" }
        );

        document.getElementById("resultsProjectName").textContent = project.name;
        document.getElementById("resultsProjectSettings").textContent =
          `${dateCreated} | Sky Glint: ${project.lw_method} | Irradiance: ${project.ed_method} | Masking: ${project.mask_method || "None"}`;

        if (typeof buildOverviewFromFolder === "function") {
          console.log("DEBUG folder_path:", project.folder_path);
          console.log("DEBUG wq_algs:", project.wq_algs);
          buildOverviewFromFolder(project.folder_path, project.wq_algs || []);
          console.log("[Results] Charts built");
        }

        if (typeof loadCSVData === "function") {
          loadCSVData(project.folder_path);
          console.log("[Results] CSV data loaded");
        }

        if (typeof loadImages === "function") {
          loadImages(project.folder_path);
          console.log("[Results] Images loaded");
        }

        if (typeof loadTrajectoryData === "function") {
          loadTrajectoryData(project.folder_path);
          console.log("[Results] Trajectory data loaded");
        }

        // Initialize mosaic cards
            if (typeof renderMosaicCards === 'function') {
            renderMosaicCards();
            console.log('[Results] Mosaic cards loaded');
            }


      } catch (err) {
        console.error("Failed to load project:", err);
      }
    }, 100);
  }
}


//Menu and Tabs 
function toggleMenu(e) {
  e.stopPropagation();
  const menu = e.currentTarget.querySelector(".actions-menu");
  document.querySelectorAll(".actions-menu").forEach((m) => {
    if (m !== menu) m.classList.remove("show");
  });
  menu.classList.toggle("show");
}

function switchTab(e, tab) {
  document.querySelectorAll(".tab-content").forEach((t) =>
    t.classList.remove("active")
  );
  document.querySelectorAll(".tab").forEach((t) =>
    t.classList.remove("active")
  );
  document.getElementById(tab).classList.add("active");
  if (e && e.currentTarget) e.currentTarget.classList.add("active");
}

document.addEventListener("click", function () {
  document
    .querySelectorAll(".actions-menu")
    .forEach((m) => m.classList.remove("show"));
});


//Project Options Dialog 
function showProjectOptionsDialog() {
  document.getElementById("projectOptionsDialog").style.display = "flex";

  document
    .querySelectorAll('input[name="projectOption"]')
    .forEach((radio) => {
      radio.addEventListener("change", function () {
        const newNameField = document.getElementById("newProjectNameField");
        if (this.value === "new") {
          newNameField.style.display = "block";
        } else {
          newNameField.style.display = "none";
        }
      });
    });
}

function closeProjectOptionsDialog() {
  document.getElementById("projectOptionsDialog").style.display = "none";
}


async function applySettingsChanges() {
  console.log("[Settings] Collecting changes...");

  const projectId = sessionStorage.getItem("currentProjectId");
  if (!projectId) {
    alert("No project selected.");
    return;
  }

  const renameField = document.getElementById("settingsProjectRename");
  const rrsField = document.getElementById("settingsRrsCount");

  const name = renameField ? renameField.value.trim() : "";
  const rrs_count = rrsField ? parseInt(rrsField.value) : 25;

  if (!name) {
    alert("Please enter a project name before applying changes.");
    return;
  }

  const outputIds = {
    "chl_hu": "settings-output-chl-hu",
    "chl_ocx": "settings-output-chl-ocx",
    "chl_hu_ocx": "settings-output-chl-hu-ocx",
    "chl_gitelson": "settings-output-chl-gitelson",
    "tsm_nechad": "settings-output-tsm",
    "mosaics": "settings-output-mosaics"
  };

  const wq_algs = [];
  Object.entries(outputIds).forEach(([key, id]) => {
    const el = document.getElementById(id);
    if (el && el.checked) wq_algs.push(key);
  });

  const payload = {
    projectId: projectId,
    name: name,
    rrs_count,
    wq_algs
  };

  console.log("[Settings] Sending payload:", payload);

  try {
    const res = await fetch(`http://localhost:8889/api/projects/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      console.error("Update error:", await res.text());
      alert("Failed to update project.");
      return;
    }

    console.log("[Settings] Project updated. Now reprocessing…");

    const processRes = await fetch(`http://localhost:8889/api/process/updated/${projectId}`);

    if (!processRes.ok) {
      console.error("Process error:", await processRes.text());
      alert("Project updated but reprocessing failed.");
      return;
    }

    alert("Project updated and reprocessed successfully!");
    navigate("results");

  } catch (err) {
    console.error("Update request failed:", err);
    alert("Failed to update project. See console for details.");
  }
}

//Mosaic Tools 
let mosaicEditMode = false;
let currentRotation = 0;
let isDragging = false;
let startX, startY, translateX = 0, translateY = 0;

function toggleMosaicEditMode() {
  mosaicEditMode = !mosaicEditMode;
  const controls = document.getElementById("mosaicEditControls");
  const container = document.getElementById("mosaicContainer");

  if (mosaicEditMode) {
    controls.style.display = "block";
    container.style.cursor = "grab";
    enableDragging();
  } else {
    controls.style.display = "none";
    container.style.cursor = "default";
    disableDragging();
  }
}

function enableDragging() {
  const container = document.getElementById("mosaicContainer");

  container.addEventListener("mousedown", startDrag);
  container.addEventListener("mousemove", drag);
  container.addEventListener("mouseup", endDrag);
  container.addEventListener("mouseleave", endDrag);
}

function disableDragging() {
  const container = document.getElementById("mosaicContainer");
  container.removeEventListener("mousedown", startDrag);
  container.removeEventListener("mousemove", drag);
  container.removeEventListener("mouseup", endDrag);
  container.removeEventListener("mouseleave", endDrag);
}

function startDrag(e) {
  if (!mosaicEditMode) return;
  isDragging = true;
  startX = e.clientX - translateX;
  startY = e.clientY - translateY;
  document.getElementById("mosaicContainer").style.cursor = "grabbing";
}

function drag(e) {
  if (!isDragging || !mosaicEditMode) return;
  e.preventDefault();
  translateX = e.clientX - startX;
  translateY = e.clientY - startY;
  updateMosaicTransform();
}

function endDrag() {
  isDragging = false;
  if (mosaicEditMode) {
    document.getElementById("mosaicContainer").style.cursor = "grab";
  }
}

function rotateMosaic(degrees) {
  currentRotation += degrees;
  document.getElementById("rotationValue").value = currentRotation;
  updateMosaicTransform();
}

function updateMosaicTransform() {
  const image = document.getElementById("mosaicImage");
  image.style.transform = `translate(${translateX}px, ${translateY}px) rotate(${currentRotation}deg)`;
}

function saveMosaicPosition() {
  console.log("Saving mosaic position:", {
    translateX,
    translateY,
    rotation: currentRotation,
  });
  alert(
    `Mosaic position saved!\nX: ${translateX}px, Y: ${translateY}px, Rotation: ${currentRotation}°`
  );
  toggleMosaicEditMode();
}

//Open Project Settings (loads screen + saves ID)
async function openProjectSettings() {
  console.log("[Settings] Opening project settings");

  const projectId = sessionStorage.getItem("currentProjectId");
  console.log("ID:", projectId);

  try {
    const res = await fetch(`http://localhost:8889/api/projects/${projectId}`);
    if (!res.ok) throw new Error("Failed to fetch project");

    const project = await res.json();
    console.log("[Settings] Loaded project data:", project);

    // Fill name + info
    document.getElementById("settingsProjectName").textContent = project.name;
    document.getElementById("settingsProjectInfo").textContent =
      `${project.created_at} | Data Source: ${project.data_source} | Sky Glint: ${project.lw_method} | Irradiance: ${project.ed_method} | Masking: ${project.mask_method || "None"}`;

    // Pre-fill rename
    const renameField = document.getElementById("settingsProjectRename");
    if (renameField) renameField.value = project.name;

    // Pre-fill rrs_count
    const rrsField = document.getElementById("settingsRrsCount");
    if (rrsField) rrsField.value = project.rrs_count || 25;

    // Pre-check outputs if present
    const outputMap = {
      "chl_hu": "settings-output-chl-hu",
      "chl_ocx": "settings-output-chl-ocx",
      "chl_hu_ocx": "settings-output-chl-hu-ocx",
      "chl_gitelson": "settings-output-chl-gitelson",
      "tsm_nechad": "settings-output-tsm",
      "mosaics": "settings-output-mosaics"
    };

    (project.wq_algs || []).forEach(key => {
      const id = outputMap[key];
      const checkbox = document.getElementById(id);
      if (checkbox) checkbox.checked = true;
    });

    navigate("settings");
  } catch (err) {
    console.error("[Settings] Failed to load project:", err);
  }
}

function openProjectSettingsFromDashboard(projectId) {
  if (!projectId) {
    console.error("[Settings] No project ID provided!");
    return;
  }

  console.log("[Settings] Opening from dashboard, ID:", projectId);

  sessionStorage.setItem("currentProjectId", projectId);

  openProjectSettings();   // now it loads correctly
}

window.openProjectSettingsFromDashboard = openProjectSettingsFromDashboard;


//Load Project into settings screen 
async function loadSettingsScreen(projectId) {
  try {
    const res = await fetch(`http://localhost:8889/api/projects/${projectId}`);
    if (!res.ok) throw new Error("Failed to fetch project");

    const project = await res.json();

    // 1. Update headers
    const nameEl = document.getElementById("settingsProjectName");
    const infoEl = document.getElementById("settingsProjectInfo");
    const renameInput = document.getElementById("settingsProjectNameInput");

    if (nameEl) nameEl.textContent = project.name;
    if (renameInput) renameInput.value = project.name;

    const dateCreated = new Date(project.created_at).toLocaleDateString(
      "en-US",
      { month: "2-digit", day: "2-digit", year: "numeric" }
    );

    if (infoEl) {
      infoEl.textContent =
        `${dateCreated} | Data Source: ${project.data_source} | ` +
        `Sky Glint: ${project.lw_method} | ` +
        `Irradiance: ${project.ed_method} | ` +
        `Masking: ${project.mask_method || "None"}`;
    }

    // 2. Populate dropdowns
    const glintSel = document.getElementById("settingsGlintSelect");
    const irrSel = document.getElementById("settingsIrradianceSelect");
    const maskSel = document.getElementById("settingsMaskingSelect");

    if (glintSel && project.lw_method) glintSel.value = project.lw_method;
    if (irrSel && project.ed_method) irrSel.value = project.ed_method;
    if (maskSel) maskSel.value = project.mask_method || "";

    // 3. Populate output checkboxes
    const wq = project.wq_algs || [];

    document.getElementById("settings-output-chl-hu").checked =
      wq.includes("chl_hu");
    document.getElementById("settings-output-chl-ocx").checked =
      wq.includes("chl_ocx");
    document.getElementById("settings-output-chl-hu-ocx").checked =
      wq.includes("chl_hu_ocx");
    document.getElementById("settings-output-chl-gitelson").checked =
      wq.includes("chl_gitelson");
    document.getElementById("settings-output-tsm").checked =
      wq.includes("tsm_nechad");

    // Mosaic toggle
    document.getElementById("settings-output-mosaics").checked =
      project.mosaic === 1 || project.mosaic === true;

    console.log("[Settings] Loaded project data:", project);

  } catch (err) {
    console.error("[Settings] Failed to load project:", err);
    alert("Could not load project settings. See console for details.");
  }
}

//Page Load Initialization
document.addEventListener("DOMContentLoaded", function () {
  setupDashboardOnce();

  const currentProjectId = sessionStorage.getItem("currentProjectId");

  if (currentProjectId) {
    navigate("results");
  } else {
    initializeDashboard();
  }
});

window.openProjectSettings = openProjectSettings;
window.loadSettingsScreen = loadSettingsScreen;


