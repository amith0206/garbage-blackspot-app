let mainMap, selectionMap, selectionMarker;
let selectedLat = null;
let selectedLng = null;

/* ---------------- MAIN MAP ---------------- */
mainMap = L.map('map').setView([12.9716, 77.5946], 13);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19
}).addTo(mainMap);

/* ---------------- LOAD ISSUES (FAIL-SAFE) ---------------- */
fetch('/api/issues')
    .then(res => res.json())
    .then(data => {
        data.forEach(issue => {
            L.marker([issue.latitude, issue.longitude])
                .addTo(mainMap)
                .bindPopup(issue.title || issue.issue_type);
        });
    })
    .catch(() => console.warn("Issues API failed, map still loaded"));

/* ---------------- MODAL ---------------- */
const modal = document.getElementById('modal');
const openBtn = document.getElementById('addSpotBtn');
const closeBtn = document.querySelector('.close');
const cancelBtn = document.getElementById('cancelBtn');

openBtn.onclick = () => modal.style.display = 'block';
closeBtn.onclick = cancelBtn.onclick = () => closeModal();

function closeModal() {
    modal.style.display = 'none';
    resetForm();
}

/* ---------------- IMAGE PREVIEW ---------------- */
document.getElementById('image').addEventListener('change', e => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
        document.getElementById('imagePreview').innerHTML =
            `<img src="${ev.target.result}">`;
    };
    reader.readAsDataURL(file);
    validateForm();
});

/* ---------------- LOCATION ---------------- */
document.getElementById('useGpsBtn').onclick = () => {
    navigator.geolocation.getCurrentPosition(pos => {
        selectedLat = pos.coords.latitude;
        selectedLng = pos.coords.longitude;
        updateCoords();
        hideSelectionMap();
    });
};

document.getElementById('pickMapBtn').onclick = () => showSelectionMap();

function showSelectionMap() {
    document.getElementById('selectionMapContainer').style.display = 'block';

    if (!selectionMap) {
        selectionMap = L.map('selectionMap').setView([12.9716, 77.5946], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png')
            .addTo(selectionMap);

        selectionMap.on('click', e => {
            selectedLat = e.latlng.lat;
            selectedLng = e.latlng.lng;

            if (selectionMarker) selectionMap.removeLayer(selectionMarker);
            selectionMarker = L.marker([selectedLat, selectedLng])
                .addTo(selectionMap);

            updateCoords();
        });
    }
    setTimeout(() => selectionMap.invalidateSize(), 200);
}

function hideSelectionMap() {
    document.getElementById('selectionMapContainer').style.display = 'none';
}

function updateCoords() {
    const el = document.getElementById('coordsDisplay');
    el.textContent = `Selected: ${selectedLat.toFixed(6)}, ${selectedLng.toFixed(6)}`;
    el.classList.add('active');
    validateForm();
}

/* ---------------- VALIDATION ---------------- */
function validateForm() {
    const imageOk = document.getElementById('image').files.length > 0;
    const locationOk = selectedLat !== null && selectedLng !== null;
    document.getElementById('submitBtn').disabled = !(imageOk && locationOk);
}

/* ---------------- SUBMIT ---------------- */
document.getElementById('spotForm').addEventListener('submit', e => {
    e.preventDefault();
    if (!selectedLat || !selectedLng) return;

    document.getElementById('loadingOverlay').style.display = 'flex';

    const fd = new FormData();
    fd.append('issue_type', document.getElementById('issueType').value);
    fd.append('title', document.getElementById('title').value);
    fd.append('latitude', selectedLat);
    fd.append('longitude', selectedLng);
    fd.append('image', document.getElementById('image').files[0]);

    fetch('/api/issues', { method: 'POST', body: fd })
        .then(() => location.reload());
});

/* ---------------- RESET ---------------- */
function resetForm() {
    selectedLat = selectedLng = null;
    document.getElementById('spotForm').reset();
    document.getElementById('imagePreview').innerHTML = '';
    document.getElementById('coordsDisplay').textContent = 'No location selected';
    document.getElementById('coordsDisplay').classList.remove('active');
    document.getElementById('submitBtn').disabled = true;
    hideSelectionMap();
}
