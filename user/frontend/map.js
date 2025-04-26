const map = L.map('map').setView([52.370216, 4.883977], 13);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19
}).addTo(map);

let userLocation = null;
let placedMarker = null;
let routingControl = null;

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
  },
  err => {
    alert("Geolocation permission denied.");
  }
);

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
  window.location.href = "chat.html";
}