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
    garbage: "static/icons/garbage.png",
    broken_footpath: "static/icons/broken.png",
    illegal_flex: "static/icons/flex.png",
    pothole: "static/icons/pothole.png"
};

function getMarkerIcon(type, status) {
    const color = status === "resolved" ? "green" : "red";

    return L.icon({
        iconUrl: ICONS[type],
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
    document.getElementById("selectionMapContainer").style.display = "block";

    map.once("click", e => {
        selectedLatLng = e.latlng;

        if (tempMarker) map.removeLayer(tempMarker);
        tempMarker = L.marker(selectedLatLng).addTo(map);

        document.getElementById("coordsDisplay").innerText =
            `Lat: ${selectedLatLng.lat.toFixed(5)}, Lng: ${selectedLatLng.lng.toFixed(5)}`;
        document.getElementById("coordsDisplay").classList.add("active");
    });
};

document.getElementById("useGpsBtn").onclick = () => {
    navigator.geolocation.getCurrentPosition(pos => {
        selectedLatLng = {
            lat: pos.coords.latitude,
            lng: pos.coords.longitude
        };

        if (tempMarker) map.removeLayer(tempMarker);
        tempMarker = L.marker(selectedLatLng).addTo(map);

        document.getElementById("coordsDisplay").innerText =
            `Lat: ${selectedLatLng.lat.toFixed(5)}, Lng: ${selectedLatLng.lng.toFixed(5)}`;
        document.getElementById("coordsDisplay").classList.add("active");
    });
};

// ============================
// IMAGE PREVIEW (FIXED SIZE)
// ============================

document.getElementById("image").addEventListener("change", e => {
    const preview = document.getElementById("imagePreview");
    preview.innerHTML = "";

    const img = document.createElement("img");
    img.src = URL.createObjectURL(e.target.files[0]);
    preview.appendChild(img);
});

// ============================
// SUBMIT ISSUE
// ============================

document.getElementById("spotForm").onsubmit = async e => {
    e.preventDefault();

    if (!selectedLatLng) {
        alert("Please select a location");
        return;
    }

    const formData = new FormData(e.target);
    formData.append("lat", selectedLatLng.lat);
    formData.append("lng", selectedLatLng.lng);

    document.getElementById("loadingOverlay").style.display = "flex";

    const res = await fetch("/api/issues", {
        method: "POST",
        body: formData
    });

    document.getElementById("loadingOverlay").style.display = "none";

    if (res.ok) {
        closeModal();
        loadIssues();
        e.target.reset();
        document.getElementById("imagePreview").innerHTML = "";
    } else {
        alert("Error submitting issue");
    }
};

// ============================
// LOAD ISSUES
// ============================

async function loadIssues() {
    const res = await fetch("/api/issues");
    const issues = await res.json();

    issues.forEach(issue => {
        const icon = getMarkerIcon(issue.type, issue.status);

        L.marker([issue.lat, issue.lng], { icon })
            .addTo(map)
            .bindPopup(`
                <div class="popup-content">
                    <div class="popup-title">${issue.type.replace("_", " ")}</div>
                    <img src="${issue.image_url}">
                    <div class="popup-info">${issue.description || ""}</div>
                    <div class="popup-coords">${issue.lat}, ${issue.lng}</div>
                    <div>Status: <b>${issue.status}</b></div>
                </div>
            `);
    });
}

loadIssues();
