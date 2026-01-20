const map = L.map('map').setView([20.6, 78.9], 5);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

const icons = {
  garbage: L.icon({ iconUrl: '/static/icons/garbage.png', iconSize: [32,32] }),
  broken_footpath: L.icon({ iconUrl: '/static/icons/broken.png', iconSize: [32,32] }),
  blocked_footpath: L.icon({ iconUrl: '/static/icons/blocked.png', iconSize: [32,32] })
};

fetch('/api/issues')
  .then(r => r.json())
  .then(data => {
    data.forEach(i => {
      L.marker([i.latitude, i.longitude], { icon: icons[i.issue_type] })
        .addTo(map)
        .bindPopup(i.title || i.issue_type);
    });
  });

navigator.geolocation.getCurrentPosition(pos => {
  map.setView([pos.coords.latitude, pos.coords.longitude], 14);
});
