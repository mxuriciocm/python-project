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

var truckMarker = null;

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

// ...existing code...

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
            const route = data.routes[0];
            
            try {
                // Decodificar usando mapbox polyline
                const coordinates = window.polyline.decode(route.geometry);
                
                // Las coordenadas ya vienen en el formato correcto [lat, lng]
                if (coordinates.length > 1) {
                    // Dibujar la ruta siguiendo las calles
                    const routePolyline = L.polyline(coordinates, { 
                        color: 'blue', 
                        weight: 2.5, 
                        opacity: 1 
                    }).addTo(rutasLayerGroup);
                    
                    map.fitBounds(routePolyline.getBounds());

                    // Agregar marcadores en los puntos de parada
                    route.waypoints.forEach(waypoint => {
                        L.circleMarker([waypoint.lat, waypoint.lon], {
                            color: 'green',
                            radius: 5
                        }).addTo(rutasLayerGroup)
                        .bindPopup(waypoint.name);
                    });

                    // Colocar el camión en el primer punto de la ruta
                    displayStaticTruck(coordinates[0], route.camion, route.distancia_total);
                }
            } catch (e) {
                console.error('Error decodificando ruta:', e);
                alert('Error al decodificar la ruta');
            }
        } else {
            alert('No se encontraron rutas');
        }
    })
    .catch(error => {
        console.error('Error fetching routes:', error);
        alert('Error al obtener la ruta');
    });
}

// ...existing code...

function displayStaticTruck(position, truckInfo, distanciaTotal) {
    if (truckMarker) {
        truckMarker.remove();
    }

    const truckIcon = L.divIcon({
        html: '🚛',
        className: 'truck-icon',
        iconSize: [25, 25],
        iconAnchor: [12, 12]
    });

    truckMarker = L.marker(position, {
        icon: truckIcon
    }).addTo(map);

    // Agregar popup con información detallada
    const popupContent = `
        <div style="font-size: 14px;">
            <h4 style="margin: 0 0 8px 0;">Camión Asignado</h4>
            <strong>Matrícula:</strong> ${truckInfo.matricula}<br>
            <strong>Capacidad:</strong> ${truckInfo.capacidad} ton<br>
            <strong>Rango:</strong> ${truckInfo.rango} km<br>
            <strong>Horario:</strong> ${truckInfo.horario}<br>
            <strong>Distancia de ruta:</strong> ${distanciaTotal} km
        </div>
    `;

    truckMarker.bindPopup(popupContent);
    truckMarker.openPopup(); // Mostrar el popup inmediatamente
}

function limpiarRutas() {
    if (truckMarker) {
        truckMarker.remove();
    }
    rutasLayerGroup.clearLayers();
}

