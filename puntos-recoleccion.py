import sys
import pandas as pd  
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl 
import folium  
import os  

def obtener_dia_hora_actual():
    now = datetime.now()
    current_day = now.strftime("%A")
    current_hour = now.hour
    return current_day, current_hour

dias_semana = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo"
}

turnos = {
    "Mañana": range(0, 12),
    "Tarde": range(12, 18),
    "Noche": range(18, 24)
}

def cargar_datos(archivo):
    if not os.path.exists(archivo):
        print(f"Error: El archivo '{archivo}' no existe.")
        return pd.DataFrame()
    try:
        return pd.read_json(archivo)
    except ValueError as e:
        print(f"Error al cargar el archivo '{archivo}': {e}")
        return pd.DataFrame()

def filtrar_puntos(puntos, dia_actual, hora_actual):
    return puntos[
        (puntos['dia'] == dia_actual) & 
        (puntos['turno'].isin(turnos.keys())) &
        (puntos['turno'].apply(lambda x: hora_actual in turnos[x]))
    ]

def crear_mapa(puntos_recoleccion, vertederos):
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
        mapa = folium.Map(location=[-12.0464, -77.0428], zoom_start=12)
    
    return mapa

def guardar_mapa(mapa, ruta):
    mapa.save(ruta)
    
    if os.path.exists(ruta):
        print("Mapa guardado correctamente.")
    else:
        print("Error: El mapa no se guardó.")

class MapWindow(QMainWindow):
    def __init__(self, html_file_path):
        super().__init__()
        self.setWindowTitle('Mapa de Recolección de Residuos')
        self.setGeometry(100, 100, 800, 600)
        
        self.browser = QWebEngineView()
        
        if os.path.exists(html_file_path):
            self.browser.setUrl(QUrl.fromLocalFile(os.path.abspath(html_file_path)))
            print(f"Abriendo el archivo: {html_file_path}")
        else:
            self.mostrar_error("Error: El archivo HTML no existe. Asegúrate de que se haya guardado correctamente.")

        self.setCentralWidget(self.browser)

    def mostrar_error(self, mensaje):
        QMessageBox.critical(self, 'Error', mensaje)

def main():
    current_day_en, current_hour = obtener_dia_hora_actual()
    
    current_day_es = dias_semana.get(current_day_en, "")
    
    puntos_recoleccion = cargar_datos('puntos_recoleccion.json')
    vertederos = cargar_datos('vertederos.json')

    filtered_puntos_recoleccion = filtrar_puntos(puntos_recoleccion, current_day_es, current_hour)
    filtered_vertederos = filtrar_puntos(vertederos, current_day_es, current_hour)

    print(f"Puntos de recolección filtrados: {filtered_puntos_recoleccion[['nombre', 'latitud', 'longitud']]}")
    print(f"Vertederos filtrados: {filtered_vertederos[['nombre', 'latitud', 'longitud']]}")

    mapa = crear_mapa(filtered_puntos_recoleccion, filtered_vertederos)

    html_file_path = 'ruta_recoleccion_peru.html'
    guardar_mapa(mapa, html_file_path)

# Ejecutar la aplicación PyQt5
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    main()  # Ejecuta la lógica principal
    
    window = MapWindow('ruta_recoleccion_peru.html')
    
    window.show()
    
    sys.exit(app.exec_())