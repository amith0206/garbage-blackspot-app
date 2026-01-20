// ---------------- MAP ----------------
const map = L.map('map').setView([12.9716, 77.5946], 13);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19
}).addTo(map);

// Icons
const icons = {
  garbage: L.icon({ iconUrl: '/static/icons/garbage.png', iconSize: [32,32] }),
  broken_footpath: L.icon({ iconUrl: '/static/icons/broken.png', iconSize: [32,32] }),
  blocked_footpath: L.icon({ iconUrl: '/static/icons/blocked.png', iconSize: [32,32] })
};

// Load existing issues
fetch('/api/issues')
  .then(res => res.json())
  .then(data => {
    data.forEach(issue => {
      L.marker(
        [issue.latitude, issue.longitude],
        { icon: icons[issue.issue_type] }
      )
      .addTo(map)
      .bindPopup(issue.title || issue.issue_type);
    });
  });

// ---------------- MODAL LOGIC ----------------
const modal = document.getElementById('issueModal');
const openBtn = document.getElementById('reportBtn');
const closeBtn = document.getElementById('closeModal');

openBtn.onclick = () => modal.style.display = 'block';
closeBtn.onclick = () => modal.style.display = 'none';

window.onclick = (e) => {
  if (e.target === modal) modal.style.display = 'none';
};

// ---------------- FORM SUBMIT ----------------
let userLat = null;
let userLng = null;

// Get location
navigator.geolocation.getCurrentPosition(
  pos => {
    userLat = pos.coords.latitude;
    userLng = pos.coords.longitude;
  },
  () => alert("Location permission is required")
);

document.getElementById('issueForm').addEventListener('submit', function(e) {
  e.preventDefault();

  if (!userLat || !userLng) {
    alert("Location not available");
    return;
  }

  const formData = new FormData();
  formData.append('issue_type', document.getElementById('issueType').value);
  formData.append('title', document.getElementById('title').value);
  formData.append('latitude', userLat);
  formData.append('longitude', userLng);
  formData.append('image', document.getElementById('image').files[0]);

  fetch('/api/issues', {
    method: 'POST',
    body: formData
  })
  .then(res => res.json())
  .then(() => {
    alert('Issue reported successfully!');
    location.reload();
  })
  .catch(() => alert('Error submitting issue'));
});
