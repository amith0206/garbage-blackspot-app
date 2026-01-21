// ============================
// MAP INITIALIZATION
// ============================

const map = L.map("map", {
    center: [12.9716, 77.5946], // Bengaluru
    zoom: 11,
    zoomControl: true
});

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);

// ============================
// ICONS
// ============================

const ICONS = {
    garbage: "/static/icons/garbage.png",
    broken_footpath: "/static/icons/broken.png",
    illegal_flex: "/static/icons/flex.png",
    pothole: "/static/icons/pothole.png"
};

function getMarkerIcon(type, status) {
    const color = status === "resolved" ? "green" : "red";

    return L.icon({
        iconUrl: ICONS[type] || ICONS.garbage,
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32],
        className: `marker-${color}`
    });
}

// ============================
// MODAL CONTROLS
// ============================

const modal = document.getElementById("modal");
const openBtn = document.getElementById("addSpotBtn");
const closeBtn = document.querySelector(".close");

openBtn.onclick = () => {
    modal.style.display = "block";
    disableMap();
};

closeBtn.onclick = closeModal;

modal.onclick = e => {
    if (e.target === modal) closeModal();
};

function closeModal() {
    modal.style.display = "none";
    document.getElementById("coordsDisplay").classList.remove("active");
    document.getElementById("coordsDisplay").innerText = "";
    if (tempMarker) {
        map.removeLayer(tempMarker);
        tempMarker = null;
    }
    selectedLatLng = null;
    enableMap();
}

// ============================
// MAP FREEZE / UNFREEZE
// ============================

function disableMap() {
    map.dragging.disable();
    map.scrollWheelZoom.disable();
    map.doubleClickZoom.disable();
    map.boxZoom.disable();
    map.keyboard.disable();
    if (map.tap) map.tap.disable();
}

function enableMap() {
    map.dragging.enable();
    map.scrollWheelZoom.enable();
    map.doubleClickZoom.enable();
    map.boxZoom.enable();
    map.keyboard.enable();
    if (map.tap) map.tap.enable();

    // CRITICAL FIX
    setTimeout(() => map.invalidateSize(), 200);
}

// ============================
// LOCATION PICKING
// ============================

let selectedLatLng = null;
let tempMarker = null;

document.getElementById("pickMapBtn").onclick = () => {
    alert("Click anywhere on the map to select location");
    closeModal();
    
    map.once("click", e => {
        selectedLatLng = e.latlng;

        if (tempMarker) map.removeLayer(tempMarker);
        tempMarker = L.marker(selectedLatLng, {
            icon: L.icon({
                iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png",
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            })
        }).addTo(map);

        // Reopen modal
        modal.style.display = "block";
        document.getElementById("coordsDisplay").innerText =
            `Lat: ${selectedLatLng.lat.toFixed(5)}, Lng: ${selectedLatLng.lng.toFixed(5)}`;
        document.getElementById("coordsDisplay").classList.add("active");
    });
};

document.getElementById("useGpsBtn").onclick = () => {
    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        pos => {
            selectedLatLng = {
                lat: pos.coords.latitude,
                lng: pos.coords.longitude
            };

            if (tempMarker) map.removeLayer(tempMarker);
            tempMarker = L.marker(selectedLatLng, {
                icon: L.icon({
                    iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png",
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41]
                })
            }).addTo(map);

            map.setView(selectedLatLng, 15);

            document.getElementById("coordsDisplay").innerText =
                `Lat: ${selectedLatLng.lat.toFixed(5)}, Lng: ${selectedLatLng.lng.toFixed(5)}`;
            document.getElementById("coordsDisplay").classList.add("active");
        },
        err => {
            alert("Unable to get your location: " + err.message);
        }
    );
};

// ============================
// IMAGE PREVIEW
// ============================

document.getElementById("image").addEventListener("change", e => {
    const preview = document.getElementById("imagePreview");
    preview.innerHTML = "";

    if (e.target.files && e.target.files[0]) {
        const img = document.createElement("img");
        img.src = URL.createObjectURL(e.target.files[0]);
        preview.appendChild(img);
    }
});

// ============================
// SUBMIT ISSUE
// ============================

document.getElementById("spotForm").onsubmit = async e => {
    e.preventDefault();

    if (!selectedLatLng) {
        alert("Please select a location using 'Pick on Map' or 'Use GPS'");
        return;
    }

    const formData = new FormData(e.target);
    formData.append("latitude", selectedLatLng.lat);
    formData.append("longitude", selectedLatLng.lng);

    document.getElementById("loadingOverlay").style.display = "flex";

    try {
        const res = await fetch("/api/issues", {
            method: "POST",
            body: formData
        });

        document.getElementById("loadingOverlay").style.display = "none";

        if (res.ok) {
            alert("Issue reported successfully!");
            closeModal();
            loadIssues();
            e.target.reset();
            document.getElementById("imagePreview").innerHTML = "";
        } else {
            const error = await res.json();
            alert("Error submitting issue: " + (error.error || "Unknown error"));
        }
    } catch (err) {
        document.getElementById("loadingOverlay").style.display = "none";
        alert("Network error: " + err.message);
    }
};

// ============================
// LOAD ISSUES
// ============================

let markersLayer = L.layerGroup().addTo(map);

async function loadIssues() {
    try {
        const res = await fetch("/api/issues");
        const issues = await res.json();

        // Clear existing markers
        markersLayer.clearLayers();

        issues.forEach(issue => {
            const icon = getMarkerIcon(issue.type, issue.status);

            const marker = L.marker([issue.latitude, issue.longitude], { icon })
                .bindPopup(`
                    <div class="popup-content">
                        <div class="popup-title">${issue.type.replace(/_/g, " ")}</div>
                        <img src="/${issue.image_path}" alt="Issue image">
                        <div class="popup-info">${issue.description || "No description provided"}</div>
                        <div class="popup-coords">${issue.latitude.toFixed(5)}, ${issue.longitude.toFixed(5)}</div>
                        <div>Status: <b>${issue.status}</b></div>
                        <small style="color: #999;">Reported: ${new Date(issue.created_at).toLocaleDateString()}</small>
                    </div>
                `);

            markersLayer.addLayer(marker);
        });
    } catch (err) {
        console.error("Error loading issues:", err);
    }
}

// Load issues on page load
loadIssues();
