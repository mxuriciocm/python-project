var rutasLayerGroup;

document.addEventListener('DOMContentLoaded', function() {
    var map = L.map('map').setView([-12.0464, -77.0428], 13);
    rutasLayerGroup = L.layerGroup().addTo(map);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    fetch('/api/data')
        .then(response => response.json())
        .then(data => {
            const inicioSelect = document.getElementById('inicio');
            const finSelect = document.getElementById('fin');

            data.points.forEach(point => {
                L.marker([point.lat, point.lon]).addTo(map)
                    .bindPopup(point.nombre)
                    .openPopup();

                const optionInicio = document.createElement('option');
                optionInicio.value = point.nombre;
                optionInicio.text = point.nombre;
                inicioSelect.add(optionInicio);

                const optionFin = document.createElement('option');
                optionFin.value = point.nombre;
                optionFin.text = point.nombre;
                finSelect.add(optionFin);
            });

            window.pointsData = data.points;
        });

    // Fetch and display vertederos based on current day and time
    fetch('/api/vertederos')
        .then(response => response.json())
        .then(data => {
            data.vertederos.forEach(vertedero => {
                L.circleMarker([vertedero.lat, vertedero.lon], {
                    color: 'red',
                    radius: 8
                }).addTo(map)
                    .bindPopup(`<b>${vertedero.nombre}</b><br>${vertedero.calle}`);
            });
        })
        .catch(error => console.error('Error fetching vertederos:', error));
});

function calcularRutas(inicio, fin) {
    limpiarRutas(); 

    const inicioPunto = window.pointsData.find(p => p.nombre === inicio);
    const finPunto = window.pointsData.find(p => p.nombre === fin);

    if (!inicioPunto || !finPunto) {
        alert('Puntos de inicio o fin no válidos');
        return;
    }

    const osrmUrl = `http://router.project-osrm.org/route/v1/driving/${inicioPunto.lon},${inicioPunto.lat};${finPunto.lon},${finPunto.lat}?overview=full&geometries=geojson&alternatives=true`;

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

                // Add legend
                const legend = L.control({ position: 'bottomright' });
                legend.onAdd = function () {
                    const div = L.DomUtil.create('div', 'info legend');
                    div.innerHTML += '<i style="background: red"></i> Ruta más corta<br>';
                    div.innerHTML += '<i style="background: blue"></i> Ruta alternativa 1<br>';
                    div.innerHTML += '<i style="background: green"></i> Ruta alternativa 2<br>';
                    return div;
                };
                legend.addTo(map); // Ensure the map instance is passed here
            } else {
                alert('No se encontraron rutas');
            }
        })
        .catch(error => console.error('Error fetching routes:', error));
}

function limpiarRutas() {
    rutasLayerGroup.clearLayers();
}