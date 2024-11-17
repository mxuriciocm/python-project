var rutasLayerGroup;
var map; // Declare map variable in the global scope

document.addEventListener('DOMContentLoaded', function() {
    map = L.map('map').setView([-12.0464, -77.0428], 13);
    rutasLayerGroup = L.layerGroup().addTo(map);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    fetch('/api/data')
        .then(response => response.json())
        .then(data => {
            data.points.forEach(point => {
                L.marker([point.lat, point.lon]).addTo(map)
                    .bindPopup(point.nombre)
                    .openPopup();
            });

            window.pointsData = data.points;
        })
        .catch(error => console.error('Error fetching data:', error));

    // Fetch and display vertederos based on current day and time
    fetch('/api/vertederos')
        .then(response => response.json())
        .then(data => {
            const vertederoSelect = document.getElementById('vertedero');

            data.vertederos.forEach(vertedero => {
                L.circleMarker([vertedero.lat, vertedero.lon], {
                    color: 'red',
                    radius: 8
                }).addTo(map)
                    .bindPopup(`<b>${vertedero.nombre}</b><br>${vertedero.calle}`);

                const optionVertedero = document.createElement('option');
                optionVertedero.value = vertedero.nombre;
                optionVertedero.text = vertedero.nombre;
                vertederoSelect.add(optionVertedero);
            });

            window.vertederosData = data.vertederos;
        })
        .catch(error => console.error('Error fetching vertederos:', error));
});

function calcularDistancia(lat1, lon1, lat2, lon2) {
    const R = 6371; // Radius of the Earth in kilometers
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
        0.5 - Math.cos(dLat)/2 + 
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
        (1 - Math.cos(dLon))/2;

    return R * 2 * Math.asin(Math.sqrt(a));
}

function calcularRutas(vertedero, numPuntos) {
    limpiarRutas();

    const vertederoPunto = window.vertederosData.find(v => v.nombre === vertedero);
    if (!vertederoPunto) {
        alert('Vertedero no válido');
        return;
    }

    const puntosCercanos = window.pointsData
        .map(p => ({
            ...p,
            distancia: calcularDistancia(vertederoPunto.lat, vertederoPunto.lon, p.lat, p.lon)
        }))
        .sort((a, b) => a.distancia - b.distancia)
        .slice(0, numPuntos);

    const waypoints = [vertederoPunto, ...puntosCercanos, vertederoPunto];
    const osrmUrl = `http://router.project-osrm.org/route/v1/driving/${waypoints.map(p => `${p.lon},${p.lat}`).join(';')}?overview=full&geometries=geojson&alternatives=true`;

    fetch(osrmUrl)
        .then(response => response.json())
        .then(data => {
            if (data.routes && data.routes.length > 0) {
                const colors = ['red', 'blue', 'green'];
                data.routes.forEach((route, index) => {
                    const coordinates = route.geometry.coordinates.map(coord => [coord[1], coord[0]]);
                    const color = colors[index % colors.length];
                    L.polyline(coordinates, { color: color, weight: 2.5, opacity: 1 }).addTo(rutasLayerGroup);
                });
            } else {
                alert('No se encontraron rutas');
            }
        })
        .catch(error => console.error('Error fetching routes:', error));
}

function limpiarRutas() {
    rutasLayerGroup.clearLayers();
}