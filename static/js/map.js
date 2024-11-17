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

    // Update this fetch for trucks
    fetch('/api/camiones')
        .then(response => response.json())
        .then(data => {
            console.log('Camiones recibidos:', data.camiones); // Debug log
            const camionesContainer = document.getElementById('camiones-list');
            
            if (!camionesContainer) {
                console.error('Container camiones-list not found');
                return;
            }
            
            camionesContainer.innerHTML = ''; // Clear previous content
            
            if (data.camiones && data.camiones.length > 0) {
                data.camiones.forEach(camion => {
                    const camionDiv = document.createElement('div');
                    camionDiv.className = 'camion-item';
                    camionDiv.innerHTML = `
                        <strong>${camion.matricula}</strong><br>
                        ${camion.capacidad_toneladas}t - ${camion.horario}
                    `;
                    camionDiv.title = `Capacidad: ${camion.capacidad_toneladas} toneladas
Horario: ${camion.horario}
Rango: ${camion.rango_operacion} km`;
                    camionesContainer.appendChild(camionDiv);
                });
            } else {
                camionesContainer.innerHTML = '<div>No hay camiones disponibles</div>';
            }
        })
        .catch(error => {
            console.error('Error fetching camiones:', error);
            document.getElementById('camiones-list').innerHTML = 
                '<div>Error al cargar camiones</div>';
        });
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

    const now = new Date();
    const currentHour = now.getHours();

    fetch('/api/routes', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            vertedero: vertedero,
            num_puntos: numPuntos,
            hour: currentHour
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Routes data:', data);
        if (data.routes && data.routes.length > 0) {
            const colors = ['red', 'blue', 'green'];
            const route = data.routes[0];
            
            // Asegurarse de que las coordenadas estén en el formato correcto
            const coordinates = route.coordinates.map(coord => {
                return [parseFloat(coord[1]), parseFloat(coord[0])];
            });
            
            console.log('Processed coordinates:', coordinates);

            if (coordinates.length > 1) {
                const color = colors[0];
                const polyline = L.polyline(coordinates, { 
                    color: color, 
                    weight: 2.5, 
                    opacity: 1 
                }).addTo(rutasLayerGroup);
                
                // Ajustar el zoom del mapa para mostrar toda la ruta
                map.fitBounds(polyline.getBounds());
                
                console.log('Polyline added:', polyline);
            } else {
                console.error('Invalid coordinates for polyline:', coordinates);
                alert('No se encontraron suficientes puntos para generar una ruta');
            }
        } else {
            alert('No se encontraron rutas');
        }
    })
    .catch(error => console.error('Error fetching routes:', error));
}

function limpiarRutas() {
    rutasLayerGroup.clearLayers();
}

