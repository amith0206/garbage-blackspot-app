// Global variables
let mainMap;
let selectionMap;
let selectionMarker;
let selectedLat = null;
let selectedLng = null;

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initMainMap();
    loadBlackspots();
    initModal();
    initForm();
});

// Initialize the main map
function initMainMap() {
    mainMap = L.map('map').setView([20.5937, 78.9629], 5); // Center of India
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(mainMap);
}

// Load all blackspots from the API
function loadBlackspots() {
    fetch('/api/spots')
        .then(response => response.json())
        .then(spots => {
            spots.forEach(spot => {
                addMarkerToMap(spot);
            });
        })
        .catch(error => {
            console.error('Error loading blackspots:', error);
        });
}

// Add a marker to the main map
function addMarkerToMap(spot) {
    const marker = L.marker([spot.latitude, spot.longitude]).addTo(mainMap);
    
    const popupContent = createPopupContent(spot);
    marker.bindPopup(popupContent, {
        maxWidth: 320,
        className: 'custom-popup'
    });
}

// Create popup content HTML
function createPopupContent(spot) {
    const title = spot.title || 'Untitled Blackspot';
    const date = new Date(spot.created_at).toLocaleString();
    const imageUrl = `/static/uploads/${spot.image_filename}`;
    
    return `
        <div class="popup-content">
            <img src="${imageUrl}" alt="${title}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22300%22 height=%22200%22%3E%3Crect fill=%22%23ddd%22 width=%22300%22 height=%22200%22/%3E%3Ctext fill=%22%23999%22 x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22%3EImage not found%3C/text%3E%3C/svg%3E'">
            <div class="popup-title">${escapeHtml(title)}</div>
            <div class="popup-info">
                <div class="popup-coords">📍 ${spot.latitude.toFixed(6)}, ${spot.longitude.toFixed(6)}</div>
                <div>🕒 ${date}</div>
            </div>
        </div>
    `;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize modal functionality
function initModal() {
    const modal = document.getElementById('modal');
    const addSpotBtn = document.getElementById('addSpotBtn');
    const closeBtn = document.querySelector('.close');
    const cancelBtn = document.getElementById('cancelBtn');
    
    // Open modal
    addSpotBtn.addEventListener('click', function() {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    });
    
    // Close modal
    function closeModal() {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        resetForm();
    }
    
    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            closeModal();
        }
    });
}

// Initialize form functionality
function initForm() {
    const form = document.getElementById('spotForm');
    const imageInput = document.getElementById('image');
    const useGpsBtn = document.getElementById('useGpsBtn');
    const pickMapBtn = document.getElementById('pickMapBtn');
    
    // Image preview
    imageInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(event) {
                const preview = document.getElementById('imagePreview');
                preview.innerHTML = `<img src="${event.target.result}" alt="Preview">`;
            };
            reader.readAsDataURL(file);
        }
    });
    
    // Use GPS location
    useGpsBtn.addEventListener('click', function() {
        if (!navigator.geolocation) {
            showFormMessage('Geolocation is not supported by your browser', 'error');
            return;
        }
        
        useGpsBtn.textContent = '📍 Getting location...';
        useGpsBtn.disabled = true;
        
        navigator.geolocation.getCurrentPosition(
            function(position) {
                selectedLat = position.coords.latitude;
                selectedLng = position.coords.longitude;
                updateCoordsDisplay();
                useGpsBtn.textContent = '📍 Use My Location';
                useGpsBtn.disabled = false;
                useGpsBtn.classList.add('active');
                pickMapBtn.classList.remove('active');
                hideSelectionMap();
            },
            function(error) {
                showFormMessage('Unable to get your location: ' + error.message, 'error');
                useGpsBtn.textContent = '📍 Use My Location';
                useGpsBtn.disabled = false;
            }
        );
    });
    
    // Pick location on map
    pickMapBtn.addEventListener('click', function() {
        pickMapBtn.classList.add('active');
        useGpsBtn.classList.remove('active');
        showSelectionMap();
    });
    
    // Form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        submitForm();
    });
}

// Show selection map
function showSelectionMap() {
    const container = document.getElementById('selectionMapContainer');
    container.style.display = 'block';
    
    if (!selectionMap) {
        // Initialize selection map
        setTimeout(() => {
            selectionMap = L.map('selectionMap').setView([20.5937, 78.9629], 5);
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors',
                maxZoom: 19
            }).addTo(selectionMap);
            
            // Invalidate size to ensure proper rendering
            selectionMap.invalidateSize();
            
            // Add click handler
            selectionMap.on('click', function(e) {
                selectedLat = e.latlng.lat;
                selectedLng = e.latlng.lng;
                
                // Remove existing marker
                if (selectionMarker) {
                    selectionMap.removeLayer(selectionMarker);
                }
                
                // Add new marker
                selectionMarker = L.marker([selectedLat, selectedLng]).addTo(selectionMap);
                updateCoordsDisplay();
            });
        }, 100);
    } else {
        // Map already exists, just invalidate size
        setTimeout(() => {
            selectionMap.invalidateSize();
        }, 100);
    }
}

// Hide selection map
function hideSelectionMap() {
    const container = document.getElementById('selectionMapContainer');
    container.style.display = 'none';
}

// Update coordinates display
function updateCoordsDisplay() {
    const display = document.getElementById('coordsDisplay');
    if (selectedLat !== null && selectedLng !== null) {
        display.textContent = `Selected: ${selectedLat.toFixed(6)}, ${selectedLng.toFixed(6)}`;
        display.classList.add('active');
    } else {
        display.textContent = 'No location selected';
        display.classList.remove('active');
    }
}

// Submit form
function submitForm() {
    // Validate location
    if (selectedLat === null || selectedLng === null) {
        showFormMessage('Please select a location', 'error');
        return;
    }
    
    // Validate image
    const imageInput = document.getElementById('image');
    if (!imageInput.files || !imageInput.files[0]) {
        showFormMessage('Please select an image', 'error');
        return;
    }
    
    // Create FormData
    const formData = new FormData();
    formData.append('image', imageInput.files[0]);
    formData.append('title', document.getElementById('title').value);
    formData.append('latitude', selectedLat);
    formData.append('longitude', selectedLng);
    
    // Show loading overlay
    document.getElementById('loadingOverlay').style.display = 'flex';
    document.getElementById('submitBtn').disabled = true;
    
    // Submit to API
    fetch('/api/spots', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('loadingOverlay').style.display = 'none';
        document.getElementById('submitBtn').disabled = false;
        
        if (data.error) {
            showFormMessage('Error: ' + data.error, 'error');
        } else {
            showFormMessage('Blackspot added successfully!', 'success');
            addMarkerToMap(data);
            setTimeout(() => {
                document.getElementById('modal').style.display = 'none';
                document.body.style.overflow = 'auto';
                resetForm();
            }, 1500);
        }
    })
    .catch(error => {
        document.getElementById('loadingOverlay').style.display = 'none';
        document.getElementById('submitBtn').disabled = false;
        showFormMessage('Error submitting form: ' + error.message, 'error');
    });
}

// Show form message
function showFormMessage(message, type) {
    const messageDiv = document.getElementById('formMessage');
    messageDiv.textContent = message;
    messageDiv.className = 'form-message ' + type;
    
    setTimeout(() => {
        messageDiv.textContent = '';
        messageDiv.className = 'form-message';
    }, 5000);
}

// Reset form
function resetForm() {
    document.getElementById('spotForm').reset();
    document.getElementById('imagePreview').innerHTML = '';
    document.getElementById('coordsDisplay').textContent = 'No location selected';
    document.getElementById('coordsDisplay').classList.remove('active');
    document.getElementById('useGpsBtn').classList.remove('active');
    document.getElementById('pickMapBtn').classList.remove('active');
    document.getElementById('formMessage').textContent = '';
    document.getElementById('formMessage').className = 'form-message';
    
    selectedLat = null;
    selectedLng = null;
    
    if (selectionMarker) {
        selectionMap.removeLayer(selectionMarker);
        selectionMarker = null;
    }
    
    hideSelectionMap();
}