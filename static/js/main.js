let map, selectedLatLng = null, tempMarker;

document.addEventListener("DOMContentLoaded", () => {
    map = L.map("map").setView([12.9716, 77.5946], 12);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap"
    }).addTo(map);

    map.on("click", e => {
        selectedLatLng = e.latlng;
        if (tempMarker) map.removeLayer(tempMarker);
        tempMarker = L.marker(e.latlng).addTo(map);
    });

    loadIssues();
});

function disableMap() {
    map.dragging.disable();
    map.scrollWheelZoom.disable();
    map.doubleClickZoom.disable();
}

function enableMap() {
    map.dragging.enable();
    map.scrollWheelZoom.enable();
    map.doubleClickZoom.enable();
}

function loadIssues() {
    fetch("/api/issues")
        .then(r => r.json())
        .then(data => {
            data.forEach(i => {
                const color = i.status === "resolved" ? "green" : "red";
                const icon = L.icon({
                    iconUrl: `https://maps.google.com/mapfiles/ms/icons/${color}-dot.png`,
                    iconSize: [32, 32]
                });

                const m = L.marker([i.latitude, i.longitude], { icon }).addTo(map);
                m.bindPopup(`
                    <b>${i.issue_type}</b><br>
                    ${i.description || ""}<br>
                    <img src="/${i.image_path}" width="200"><br>
                    Status: ${i.status}
                    ${i.status === "open" ?
                        `<br><button onclick="resolve(${i.id})">Mark Resolved</button>` : ""}
                `);
            });
        });
}

function resolve(id) {
    fetch(`/api/issues/${id}/resolve`, { method: "POST" })
        .then(() => location.reload());
}

/* MODAL */
const modal = document.getElementById("modal");
document.getElementById("openModal").onclick = () => {
    modal.style.display = "block";
    disableMap();
};

document.querySelector(".close").onclick = () => {
    modal.style.display = "none";
    enableMap();
};

document.getElementById("issueForm").onsubmit = e => {
    e.preventDefault();
    if (!selectedLatLng) {
        alert("Please click on the map to select location");
        return;
    }

    const data = new FormData(e.target);
    data.append("latitude", selectedLatLng.lat);
    data.append("longitude", selectedLatLng.lng);

    fetch("/api/issues", { method: "POST", body: data })
        .then(() => location.reload());
};

document.getElementById("imageInput").onchange = e => {
    const img = document.getElementById("preview");
    img.src = URL.createObjectURL(e.target.files[0]);
};
