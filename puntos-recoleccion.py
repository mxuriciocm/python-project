import folium
import sys
import json
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView

# Obtener el día y la hora actual
now = datetime.now()
current_day = now.strftime("%A")
current_hour = now.hour
print(f"Día actual (inglés): {current_day}, Hora actual: {current_hour}")

# Mapeo de días de inglés a español
dias_semana = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo"
}

# Convertir el día al español
current_day_es = dias_semana.get(current_day, "")
print(f"Día actual (español): {current_day_es}")

# Definir los turnos
turnos = {
    "Mañana": range(6, 12),
    "Tarde": range(12, 18),
    "Noche": range(18, 24)
}

# Cargar puntos de recolección desde un archivo JSON
with open('puntos_recoleccion.json', 'r') as f:
    puntos_recoleccion = json.load(f)

# Cargar vertederos desde un archivo JSON
# with open('vertederos_100.json', 'r') as f:
#     vertederos = json.load(f)

# Filtrar puntos de recolección según el día y la hora
filtered_puntos_recoleccion = [
    punto for punto in puntos_recoleccion
    if punto['dia'] == current_day_es and current_hour in turnos.get(punto['turno'], [])
]

print(f"Puntos de recolección filtrados: {filtered_puntos_recoleccion}")

# Crear un mapa con folium centrado en el primer punto de recolección filtrado
if filtered_puntos_recoleccion:
    mapa = folium.Map(location=[filtered_puntos_recoleccion[0]['latitud'], filtered_puntos_recoleccion[0]['longitud']], zoom_start=12)
else:
    mapa = folium.Map(location=[-12.0464, -77.0428], zoom_start=12)  # Coordenadas de Lima, Perú

# Añadir puntos de recolección filtrados al mapa
for punto in filtered_puntos_recoleccion:
    folium.Marker(
        location=[punto['latitud'], punto['longitud']],
        popup=punto['nombre'],
        icon=folium.Icon(color='blue')
    ).add_to(mapa)

# Añadir vertederos al mapa
# for vertedero in vertederos:
#     folium.Marker(
#         location=vertedero['coordenadas'],
#         popup=vertedero['nombre'],
#         icon=folium.Icon(color='red')
#     ).add_to(mapa)

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