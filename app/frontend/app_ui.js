/****************************************************
 * MASKING INPUT LOGIC
 ****************************************************/
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


/****************************************************
 * NAVIGATION
 ****************************************************/
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

        if (typeof loadMosaicImage === "function") {
          loadMosaicImage(project.folder_path);
          console.log("[Results] Mosaic loaded");
        }

      } catch (err) {
        console.error("Failed to load project:", err);
      }
    }, 100);
  }
}


/****************************************************
 * MENU AND TABS
 ****************************************************/
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


/****************************************************
 * PROJECT OPTIONS DIALOG
 ****************************************************/
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

function applyProjectChanges() {
  const selectedOption = document.querySelector(
    'input[name="projectOption"]:checked'
  ).value;

  if (typeof applySettingsChanges === "function") {
    applySettingsChanges();
  }

  if (selectedOption === "new") {
    const newName = document.getElementById("newProjectName").value.trim();
    if (!newName) {
      alert("Please enter a project name");
      return;
    }
    console.log("Creating new project:", newName);
  } else {
    console.log("Updating existing project");
  }

  closeProjectOptionsDialog();
  navigate("loading");
}


/****************************************************
 * MOSAIC TOOLS (unchanged)
 ****************************************************/
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


/****************************************************
 * PAGE LOAD INITIALIZATION
 ****************************************************/
document.addEventListener("DOMContentLoaded", function () {
  setupDashboardOnce();

  const currentProjectId = sessionStorage.getItem("currentProjectId");

  if (currentProjectId) {
    navigate("results");
  } else {
    initializeDashboard();
  }
});
