import sys
import pandas as pd  
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl 
import folium  
import os
import math

def obtener_dia_hora_actual():
    ahora = datetime.now()
    dia_actual = ahora.strftime("%A")
    hora_actual = ahora.hour
    return dia_actual, hora_actual

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

puntos_recoleccion_path = 'datasets/puntos_recoleccion.json'
vertederos_path = 'datasets/vertederos.json'
camiones_path = 'datasets/camiones_basura.json'

def cargar_datos(rutas):
    try:
        df_recoleccion = pd.read_json(rutas[0])
        df_vertederos = pd.read_json(rutas[1])
        df_camiones = pd.read_json(rutas[2])
        return df_recoleccion, df_vertederos, df_camiones
    except ValueError as e:
        print(f"Error al cargar los datos: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def filtrar_puntos(puntos, dia_actual, hora_actual):
    """Filtra los puntos de recolección según el día y la hora actuales."""
    return puntos[
        (puntos['dia'] == dia_actual) & 
        (puntos['turno'].isin(turnos.keys())) & 
        (puntos['turno'].apply(lambda x: hora_actual in turnos[x]))
    ]

def crear_mapa(puntos_recoleccion, vertederos):
    """Crea un mapa con los puntos de recolección y vertederos."""
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
    """Calcula la distancia entre dos puntos geográficos."""
    R = 6371  # Radio de la Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distancia = R * c
    return distancia

class VentanaMapa(QMainWindow):
    def __init__(self, ruta_archivo_html):
        super().__init__()
        self.setWindowTitle('Mapa de Recolección de Residuos')
        self.setGeometry(100, 100, 800, 600)

        self.browser = QWebEngineView()
        
        if os.path.exists(ruta_archivo_html):
            self.browser.setUrl(QUrl.fromLocalFile(os.path.abspath(ruta_archivo_html))) 
            print(f"Abriendo el archivo: {ruta_archivo_html}")
        else:
            self.mostrar_error("Error: El archivo HTML no existe. Asegúrate de que se haya guardado correctamente.")

        self.setCentralWidget(self.browser)

    def mostrar_error(self, mensaje):
        """Muestra un mensaje de error."""
        QMessageBox.warning(self, 'Error', mensaje)

class CalculadoraDistancia(QWidget):
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout()
        
        self.label1 = QLabel('Coordenadas del Punto 1 (Latitud, Longitud):')
        self.input1 = QLineEdit()
        
        self.label2 = QLabel('Coordenadas del Punto 2 (Latitud, Longitud):')
        self.input2 = QLineEdit()
        
        self.boton_calcular = QPushButton('Calcular Distancia')
        self.boton_calcular.clicked.connect(self.calcular_distancia)
        
        self.resultado_label = QLabel('Distancia: ')
        
        layout.addWidget(self.label1)
        layout.addWidget(self.input1)
        layout.addWidget(self.label2)
        layout.addWidget(self.input2)
        layout.addWidget(self.boton_calcular)
        layout.addWidget(self.resultado_label)

        self.setLayout(layout)

    def calcular_distancia(self):
        """Calcula y muestra la distancia entre dos puntos."""
        try:
            lat1, lon1 = map(float, self.input1.text().split(','))
            lat2, lon2 = map(float, self.input2.text().split(','))
            distancia = calcular_distancia(lat1, lon1, lat2, lon2)
            self.resultado_label.setText(f'Distancia: {distancia:.2f} km')
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Por favor ingrese coordenadas válidas.')

def main():
    dia_actual_en, hora_actual = obtener_dia_hora_actual()
    dia_actual_es = dias_semana.get(dia_actual_en, "")
    df_recoleccion, df_vertederos, df_camiones = cargar_datos([puntos_recoleccion_path, vertederos_path, camiones_path])
    
    # Filtrar puntos de recolección y vertederos
    puntos_recoleccion_filtrados = filtrar_puntos(df_recoleccion, dia_actual_es, hora_actual)
    vertederos_filtrados = filtrar_puntos(df_vertederos, dia_actual_es, hora_actual)

    print(f"Puntos de recolección filtrados: {puntos_recoleccion_filtrados[['nombre', 'latitud', 'longitud']]}")
    print(f"Vertederos filtrados: {vertederos_filtrados[['nombre', 'latitud', 'longitud']]}")
    
    mapa = crear_mapa(puntos_recoleccion_filtrados, vertederos_filtrados)
    ruta_archivo_html = 'ruta_recoleccion_peru.html'
    guardar_mapa(mapa, ruta_archivo_html)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    main()     
    ventana_mapa = VentanaMapa('ruta_recoleccion_peru.html')
    calculadora_distancia = CalculadoraDistancia()    
    
    widget_principal = QWidget()
    layout_principal = QHBoxLayout() 
    layout_principal.addWidget(calculadora_distancia) 
    layout_principal.addWidget(ventana_mapa) 
    layout_principal.setStretch(0, 1)  
    layout_principal.setStretch(1, 3) 
    widget_principal.setLayout(layout_principal)    
    widget_principal.show()

    sys.exit(app.exec_())
