import sys
import pandas as pd  
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl 
import folium  
import os
import math

# Obtener el día y la hora actual
def obtener_dia_hora_actual():
    now = datetime.now()
    current_day = now.strftime("%A")
    current_hour = now.hour
    return current_day, current_hour

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

# Definir los turnos
turnos = {
    "Mañana": range(0, 12),
    "Tarde": range(12, 18),
    "Noche": range(18, 24)
}

def cargar_datos(archivo):
    """Carga datos desde un archivo JSON usando pandas y maneja errores."""
    if not os.path.exists(archivo):
        print(f"Error: El archivo '{archivo}' no existe.")
        return pd.DataFrame()  # Retorna un DataFrame vacío en caso de error
    try:
        return pd.read_json(archivo)
    except ValueError as e:
        print(f"Error al cargar el archivo '{archivo}': {e}")
        return pd.DataFrame()  # Retorna un DataFrame vacío en caso de error

def filtrar_puntos(puntos, dia_actual, hora_actual):
    """Filtra los puntos según el día y la hora actuales."""
    return puntos[
        (puntos['dia'] == dia_actual) & 
        (puntos['turno'].isin(turnos.keys())) & 
        (puntos['turno'].apply(lambda x: hora_actual in turnos[x]))
    ]

def crear_mapa(puntos_recoleccion, vertederos):
    """Crea un mapa con puntos de recolección y vertederos."""
    if not puntos_recoleccion.empty:
        mapa = folium.Map(location=[puntos_recoleccion.iloc[0]['latitud'], puntos_recoleccion.iloc[0]['longitud']], zoom_start=12)
        
        for _, punto in puntos_recoleccion.iterrows():
            folium.Marker(
                location=[punto['latitud'], punto['longitud']],
                popup=punto['nombre'],
                icon=folium.Icon(color='blue')
            ).add_to(mapa)
        
        for _, vertedero in vertederos.iterrows():
            folium.Marker(
                location=[vertedero['latitud'], vertedero['longitud']],
                popup=vertedero['nombre'],
                icon=folium.Icon(color='red')
            ).add_to(mapa)
    else:
        print("No hay puntos de recolección filtrados. Usando coordenadas por defecto.")
        mapa = folium.Map(location=[-12.0464, -77.0428], zoom_start=12)  # Coordenadas por defecto
    
    return mapa

def guardar_mapa(mapa, ruta):
    """Guarda el mapa en un archivo HTML."""
    mapa.save(ruta)
    
    if os.path.exists(ruta):
        print("Mapa guardado correctamente.")
    else:
        print("Error: El mapa no se guardó.")

def calcular_distancia(lat1, lon1, lat2, lon2):
    """Calcula la distancia entre dos puntos usando la fórmula de Haversine."""
    R = 6371  # Radio de la Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distancia = R * c
    return distancia

class MapWindow(QMainWindow):
    def __init__(self, html_file_path):
        super().__init__()
        self.setWindowTitle('Mapa de Recolección de Residuos')
        self.setGeometry(100, 100, 800, 600)

        self.browser = QWebEngineView()
        
        if os.path.exists(html_file_path):
            self.browser.setUrl(QUrl.fromLocalFile(os.path.abspath(html_file_path)))  # Usar ruta absoluta
            print(f"Abriendo el archivo: {html_file_path}")
        else:
            self.mostrar_error("Error: El archivo HTML no existe. Asegúrate de que se haya guardado correctamente.")

        self.setCentralWidget(self.browser)

class DistanceCalculator(QWidget):
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout()
        
        self.label1 = QLabel('Coordenadas del Punto 1 (Latitud, Longitud):')
        self.input1 = QLineEdit()
        
        self.label2 = QLabel('Coordenadas del Punto 2 (Latitud, Longitud):')
        self.input2 = QLineEdit()
        
        self.calculate_button = QPushButton('Calcular Distancia')
        self.calculate_button.clicked.connect(self.calcular_distancia)
        
        self.result_label = QLabel('Distancia: ')
        
        layout.addWidget(self.label1)
        layout.addWidget(self.input1)
        layout.addWidget(self.label2)
        layout.addWidget(self.input2)
        layout.addWidget(self.calculate_button)
        layout.addWidget(self.result_label)

        self.setLayout(layout)

    def calcular_distancia(self):
        """Calcula y muestra la distancia entre dos puntos."""
        try:
            lat1, lon1 = map(float, self.input1.text().split(','))
            lat2, lon2 = map(float, self.input2.text().split(','))
            distancia = calcular_distancia(lat1, lon1, lat2, lon2)
            self.result_label.setText(f'Distancia: {distancia:.2f} km')
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Por favor ingrese coordenadas válidas.')

def main():
    # Obtener día y hora actual
    current_day_en, current_hour = obtener_dia_hora_actual()
    
    # Convertir el día al español
    current_day_es = dias_semana.get(current_day_en, "")
    
    # Cargar datos
    puntos_recoleccion = cargar_datos('puntos_recoleccion.json')
    vertederos = cargar_datos('vertederos.json')

    # Filtrar puntos de recolección y vertederos según el día y la hora
    filtered_puntos_recoleccion = filtrar_puntos(puntos_recoleccion, current_day_es, current_hour)
    filtered_vertederos = filtrar_puntos(vertederos, current_day_es, current_hour)

    print(f"Puntos de recolección filtrados: {filtered_puntos_recoleccion[['nombre', 'latitud', 'longitud']]}")
    print(f"Vertederos filtrados: {filtered_vertederos[['nombre', 'latitud', 'longitud']]}")

    # Crear el mapa
    mapa = crear_mapa(filtered_puntos_recoleccion, filtered_vertederos)

    # Guardar el mapa en un archivo HTML
    html_file_path = 'ruta_recoleccion_peru.html'
    guardar_mapa(mapa, html_file_path)

# Ejecutar la aplicación PyQt5
if __name__ == '__main__':
    
    app = QApplication(sys.argv)

    main()  # Ejecuta la lógica principal
    
    window = MapWindow('ruta_recoleccion_peru.html')
    
    distance_calculator = DistanceCalculator()
    
    # Mostrar ambas ventanas (mapa y calculadora de distancias) en un layout horizontal
    main_widget = QWidget()
    
    main_layout = QHBoxLayout()  # Cambiar a QHBoxLayout para disposición horizontal
    
    main_layout.addWidget(distance_calculator)  # Calculadora de distancias a la izquierda
    main_layout.addWidget(window)  # Mapa a la derecha
    
    # Ajustar el tamaño de los widgets
    main_layout.setStretch(0, 1)  
    main_layout.setStretch(1, 3) 
    
    main_widget.setLayout(main_layout)
    
    main_widget.show()

    
sys.exit(app.exec_())