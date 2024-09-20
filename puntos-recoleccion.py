import folium
import sys
import json
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView

# Cargar puntos de recolección desde un archivo JSON
with open('puntos_recoleccion_v500.json', 'r') as f:
    puntos_recoleccion = json.load(f)

# Crear un mapa con folium centrado en el primer punto de recolección
mapa = folium.Map(location=puntos_recoleccion[0]['coordenadas'], zoom_start=12)

# Añadir puntos de recolección al mapa
for punto in puntos_recoleccion:
    folium.Marker(
        location=punto['coordenadas'],
        popup=punto['nombre'],
        icon=folium.Icon(color='blue')
    ).add_to(mapa)

# Guardar el mapa en un archivo HTML
mapa.save('ruta_recoleccion_peru.html')
print("Mapa guardado en ruta_recoleccion_peru.html")

# Crear una aplicación PyQt5
class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Mapa de Recolección de Residuos')
        self.setGeometry(100, 100, 800, 600)
        self.browser = QWebEngineView()
        with open('ruta_recoleccion_peru.html', 'r') as f:
            html_content = f.read()
        print("Contenido HTML cargado")
        self.browser.setHtml(html_content)
        self.setCentralWidget(self.browser)

# Ejecutar la aplicación PyQt5
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MapWindow()
    window.show()
    sys.exit(app.exec_())