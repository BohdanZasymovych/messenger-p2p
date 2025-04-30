// map.js - updated version
const map = L.map('map').setView([52.370216, 4.883977], 13);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19
}).addTo(map);

let userLocation = null;
let placedMarker = null;
let routingControl = null;
let socket = null;

// Connect to WebSocket
function connectWebSocket() {
  socket = new WebSocket(`ws://${window.location.host}/ws`);
  
  socket.onopen = () => {
    console.log("WebSocket connection established");
  };
  
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "marker") {
      handleIncomingMarker(message);
    }
  };
  
  socket.onclose = () => {
    console.log("WebSocket connection closed");
  };
}

// Handle incoming marker
function handleIncomingMarker(message) {
  const markerData = JSON.parse(message.content);
  const marker = L.marker([markerData.lat, markerData.lon])
    .addTo(map)
    .bindPopup(`📍 ${markerData.label || "Marker from friend"}`)
    .openPopup();
}

// When opening the map from chat
function openMapWithFriend(targetUserId) {
  window.currentUserId = getCurrentUserId(); // You need to implement this
  window.targetUserId = targetUserId;
  window.location.href = "/map.html";
}
// Get current position and set up map
navigator.geolocation.getCurrentPosition(
  pos => {
    userLocation = L.latLng(pos.coords.latitude, pos.coords.longitude);
    map.setView(userLocation, 14);
    L.circleMarker(userLocation, {
      radius: 8,
      color: 'blue',
      fillColor: '#30f',
      fillOpacity: 0.8
    }).addTo(map).bindPopup("📍 You are here").openPopup();
    
    // Connect WebSocket after getting location
    connectWebSocket();
  },
  err => {
    alert("Geolocation permission denied.");
    // Still connect WebSocket even if location is denied
    connectWebSocket();
  }
);

// Map click handler
map.on("click", function (e) {
  if (placedMarker) map.removeLayer(placedMarker);
  placedMarker = L.marker(e.latlng).addTo(map).bindPopup("📍 Marker placed").openPopup();
});

// Send marker button handler
document.getElementById('send-marker').addEventListener('click', function() {
  if (!placedMarker) {
    alert("Please place a marker on the map first!");
    return;
  }

  const position = placedMarker.getLatLng();
  const markerData = {
    lat: position.lat,
    lon: position.lng,
    label: "Check this location!"
  };

  const message = {
    type: "marker",
    content: JSON.stringify(markerData),
    user_id: window.currentUserId, // Should be set when loading the page
    target_user_id: window.targetUserId, // Should be set when loading the page
    sending_time: new Date().toISOString()
  };

  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(message));
    alert("Marker sent successfully!");
  } else {
    alert("Connection not ready. Please try again.");
  }
});

// Rest of the existing functions (setRoute, clearAll, searchPlace, goHome) remain the same

map.on("click", function (e) {
  if (placedMarker) map.removeLayer(placedMarker);
  placedMarker = L.marker(e.latlng).addTo(map).bindPopup("📍 Marker placed").openPopup();
});

function setRoute() {
  if (!userLocation) return alert("User location not available.");
  if (!placedMarker) return alert("Place a marker first!");

  const destination = placedMarker.getLatLng();

  if (routingControl) map.removeControl(routingControl);

  routingControl = L.Routing.control({
    waypoints: [userLocation, destination],
    routeWhileDragging: false
  }).addTo(map);
}

function clearAll() {
  if (placedMarker) {
    map.removeLayer(placedMarker);
    placedMarker = null;
  }
  if (routingControl) {
    map.removeControl(routingControl);
    routingControl = null;
  }
}

function searchPlace() {
  const query = document.getElementById('search-input').value;
  if (!query) return;

  fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`)
    .then(res => res.json())
    .then(data => {
      if (data.length === 0) return alert("Place not found.");

      const { lat, lon } = data[0];
      map.setView([parseFloat(lat), parseFloat(lon)], 14);
    })
    .catch(() => alert("Search failed."));
}

function goHome() {
  window.location.href = "/chat/chat.html";
}
