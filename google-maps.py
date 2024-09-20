import googlemaps
import folium
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView

# Configurar la clave de API de Google Maps
API_KEY = ''
gmaps = googlemaps.Client(key=API_KEY)

# Definir puntos de recolección en Lima, Perú (coordenadas)
puntos_recoleccion = [
    {'nombre': 'Punto 1', 'coordenadas': (-12.0464, -77.0428)},  # Plaza Mayor de Lima
    {'nombre': 'Punto 2', 'coordenadas': (-12.0453, -77.0311)},  # Parque de la Reserva
    {'nombre': 'Punto 3', 'coordenadas': (-12.0433, -77.0283)},  # Estadio Nacional del Perú
    {'nombre': 'Punto 4', 'coordenadas': (-12.0400, -77.0300)},  # Museo de Arte de Lima
    {'nombre': 'Punto 5', 'coordenadas': (-12.0500, -77.0400)},  # Otro punto de recolección
    # Añade más puntos según sea necesario
]

# Definir destinos de disposición en Lima, Perú (coordenadas)
destinos_disposicion = [
    {'nombre': 'Vertedero 1', 'coordenadas': (-12.0600, -77.0500)},  # Ejemplo de vertedero
    {'nombre': 'Planta de Reciclaje 1', 'coordenadas': (-12.0700, -77.0600)},  # Ejemplo de planta de reciclaje
    # Añade más destinos según sea necesario
]

# Obtener la ruta óptima usando la API de Google Maps Directions
origen = puntos_recoleccion[0]['coordenadas']
destino = destinos_disposicion[0]['coordenadas']
waypoints = [p['coordenadas'] for p in puntos_recoleccion[1:]]

directions_result = gmaps.directions(
    origin=origen,
    destination=destino,
    waypoints=waypoints,
    optimize_waypoints=True,
    mode="driving"
)

# Crear un mapa con folium centrado en Lima, Perú
mapa = folium.Map(location=origen, zoom_start=14)

# Añadir puntos de recolección al mapa
for punto in puntos_recoleccion:
    folium.Marker(
        location=punto['coordenadas'],
        popup=punto['nombre'],
        icon=folium.Icon(color='blue')
    ).add_to(mapa)

# Añadir destinos de disposición al mapa
for destino in destinos_disposicion:
    folium.Marker(
        location=destino['coordenadas'],
        popup=destino['nombre'],
        icon=folium.Icon(color='green')
    ).add_to(mapa)

# Añadir la ruta al mapa
for leg in directions_result[0]['legs']:
    for step in leg['steps']:
        start_location = step['start_location']
        end_location = step['end_location']
        folium.PolyLine(
            locations=[(start_location['lat'], start_location['lng']),
                       (end_location['lat'], end_location['lng'])],
            color='red',
            weight=5,
            opacity=0.7
        ).add_to(mapa)

# Guardar el mapa en un archivo HTML
mapa.save('ruta_recoleccion_peru.html')

# Crear una aplicación PyQt5
class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Mapa de Recolección de Residuos')
        self.setGeometry(100, 100, 800, 600)
        self.browser = QWebEngineView()
        self.browser.setHtml(open('ruta_recoleccion_peru.html').read())
        self.setCentralWidget(self.browser)

# Ejecutar la aplicación PyQt5
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MapWindow()
    window.show()
    sys.exit(app.exec_())