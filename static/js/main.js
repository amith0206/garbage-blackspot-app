let map;
let selectedLatLng = null;

document.addEventListener("DOMContentLoaded", () => {
    map = L.map("map").setView([12.9716, 77.5946], 12);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap"
    }).addTo(map);

    map.on("click", e => {
        selectedLatLng = e.latlng;
    });

    loadIssues();
});

function loadIssues() {
    fetch("/api/issues")
        .then(res => res.json())
        .then(data => {
            data.forEach(issue => {
                const color = issue.status === "resolved" ? "green" : "red";

                const icon = L.icon({
                    iconUrl: `https://maps.google.com/mapfiles/ms/icons/${color}-dot.png`,
                    iconSize: [32, 32]
                });

                const marker = L.marker([issue.latitude, issue.longitude], { icon }).addTo(map);

                marker.bindPopup(`
                    <strong>${issue.issue_type}</strong><br>
                    ${issue.description || ""}<br>
                    <img src="/${issue.image_path}" width="200"><br>
                    Status: ${issue.status}
                    ${issue.status === "open"
                        ? `<br><button onclick="resolveIssue(${issue.id})">Mark Resolved</button>`
                        : ""}
                `);
            });
        });
}

function resolveIssue(id) {
    fetch(`/api/issues/${id}/resolve`, { method: "POST" })
        .then(() => location.reload());
}

// MODAL LOGIC
const modal = document.getElementById("modal");
document.getElementById("openModal").onclick = () => modal.style.display = "block";
document.querySelector(".close").onclick = () => modal.style.display = "none";

document.getElementById("issueForm").onsubmit = e => {
    e.preventDefault();
    if (!selectedLatLng) {
        alert("Click on map to select location");
        return;
    }

    const form = e.target;
    const data = new FormData(form);
    data.append("latitude", selectedLatLng.lat);
    data.append("longitude", selectedLatLng.lng);

    fetch("/api/issues", {
        method: "POST",
        body: data
    }).then(() => location.reload());
};

// IMAGE PREVIEW FIX
document.getElementById("imageInput").onchange = e => {
    const img = document.getElementById("preview");
    img.src = URL.createObjectURL(e.target.files[0]);
    img.style.maxHeight = "200px";
};
