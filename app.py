import pandas as pd
import folium
import heapq
import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

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

def calcular_distancia(lat1, lon1, lat2, lon2):
    """Calcula la distancia entre dos puntos geográficos."""
    from geopy.distance import geodesic
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers

class Nodo:
    def __init__(self, nombre, latitud, longitud):
        self.nombre = nombre
        self.latitud = latitud
        self.longitud = longitud
        self.vecinos = []

    def agregar_vecino(self, vecino, distancia):
        self.vecinos.append((vecino, distancia))

def construir_grafo(puntos_recoleccion, vertederos):
    nodos = {}
    
    # Crear nodos para puntos de recolección
    for _, punto in puntos_recoleccion.iterrows():
        nodos[punto['nombre']] = Nodo(punto['nombre'], punto['latitud'], punto['longitud'])
    
    # Crear nodos para vertederos
    for _, vertedero in vertederos.iterrows():
        nodos[vertedero['nombre']] = Nodo(vertedero['nombre'], vertedero['latitud'], vertedero['longitud'])
    
    # Conectar nodos con distancias
    for nodo1 in nodos.values():
        for nodo2 in nodos.values():
            if nodo1 != nodo2:
                distancia = calcular_distancia(nodo1.latitud, nodo1.longitud, nodo2.latitud, nodo2.longitud)
                nodo1.agregar_vecino(nodo2, distancia)
    
    return nodos

def dijkstra(nodos, inicio_nombre, fin_nombre):
    distancias = {nodo: float('inf') for nodo in nodos}
    distancias[inicio_nombre] = 0
    prioridad = [(0, inicio_nombre)]
    camino = {}
    
    while prioridad:
        distancia_actual, nodo_actual = heapq.heappop(prioridad)
        
        if distancia_actual > distancias[nodo_actual]:
            continue
        
        for vecino, peso in nodos[nodo_actual].vecinos:
            distancia = distancia_actual + peso
            
            if distancia < distancias[vecino.nombre]:
                distancias[vecino.nombre] = distancia
                camino[vecino.nombre] = nodo_actual
                heapq.heappush(prioridad, (distancia, vecino.nombre))
    
    ruta = []
    nodo = fin_nombre
    while nodo:
        ruta.append(nodo)
        nodo = camino.get(nodo)
    
    return ruta[::-1]

def crear_mapa_con_ruta(puntos_recoleccion, vertederos):
    """Crea un mapa con los puntos de recolección y vertederos."""
    
    mapa = folium.Map(location=[-12.0464, -77.0428], zoom_start=12)  # Coordenadas por defecto
    
    # Agregar marcadores para puntos de recolección
    for _, punto in puntos_recoleccion.iterrows():
        folium.Marker(
            location=[punto['latitud'], punto['longitud']],
            popup=punto['nombre'],
            icon=folium.Icon(color='blue')
        ).add_to(mapa)
    
    # Agregar marcadores para vertederos
    for _, vertedero in vertederos.iterrows():
        folium.Marker(
            location=[vertedero['latitud'], vertedero['longitud']],
            popup=vertedero['nombre'],
            icon=folium.Icon(color='red')
        ).add_to(mapa)

    return mapa

def guardar_mapa(mapa, ruta_archivo_html):
    mapa.save(ruta_archivo_html)

def obtener_dia_hora_actual():
    from datetime import datetime
    ahora = datetime.now()
    dia_actual_en = ahora.strftime("%A")
    hora_actual = ahora.hour
    return dia_actual_en, hora_actual

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
            self.mostrar_error("Error: El archivo HTML no existe.")

        self.setCentralWidget(self.browser)

    def mostrar_error(self, mensaje):
        QMessageBox.warning(self, 'Error', mensaje)

class CalculadoraDistancia(QWidget):
    def mostrar_ruta_en_mapa(self, ruta):
        """Muestra la ruta más corta en el mapa."""
        # Crear un mapa nuevo
        mapa = folium.Map(location=[-12.0464, -77.0428], zoom_start=12)
        
        # Agregar marcadores para cada punto en la ruta
        for nombre in ruta:
            nodo = nodos[nombre]
            folium.Marker(
                location=[nodo.latitud, nodo.longitud],
                popup=nodo.nombre,
                icon=folium.Icon(color='blue')
            ).add_to(mapa)
        
        # Dibujar la ruta
        puntos = [(nodos[nombre].latitud, nodos[nombre].longitud) for nombre in ruta]
        folium.PolyLine(puntos, color='green', weight=2.5, opacity=1).add_to(mapa)
        
        # Guardar el mapa en un archivo temporal y mostrarlo en el navegador
        ruta_archivo_html = 'ruta_mas_corta.html'
        guardar_mapa(mapa, ruta_archivo_html)
        self.parent().findChild(QWebEngineView).setUrl(QUrl.fromLocalFile(os.path.abspath(ruta_archivo_html)))
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout()
        
        self.label_inicio = QLabel('Selecciona el Punto de Inicio:')
        self.combo_inicio = QComboBox()
        
        self.label_fin = QLabel('Selecciona el Punto de Fin:')
        self.combo_fin = QComboBox()
        
        self.boton_calcular = QPushButton('Calcular Distancia y Ruta')
        self.boton_calcular.clicked.connect(self.calcular_distancia_y_ruta)
        
        self.resultado_label = QLabel('Distancia: ')
        
        layout.addWidget(self.label_inicio)
        layout.addWidget(self.combo_inicio)
        
        layout.addWidget(self.label_fin)
        layout.addWidget(self.combo_fin)
        
        layout.addWidget(self.boton_calcular)
        layout.addWidget(self.resultado_label)

        self.setLayout(layout)

    def cargar_puntos(self, puntos_recoleccion_filtrados, vertederos_filtrados):
        """Carga los nombres de los puntos en los combo boxes."""
        
        # Limpiar las listas antes de agregar nuevos elementos
        self.combo_inicio.clear()
        self.combo_fin.clear()

        # Agregar nombres a los combo boxes
        for _, punto in puntos_recoleccion_filtrados.iterrows():
            self.combo_inicio.addItem(punto['nombre'])
            self.combo_fin.addItem(punto['nombre'])

        for _, vertedero in vertederos_filtrados.iterrows():
            self.combo_inicio.addItem(vertedero['nombre'])
            self.combo_fin.addItem(vertedero['nombre'])

    def calcular_distancia_y_ruta(self):
       punto_inicio_nombre = self.combo_inicio.currentText()
       punto_fin_nombre = self.combo_fin.currentText()

       # Obtener las coordenadas usando el nombre seleccionado del grafo.
       lat1 , lon1= None , None 
       lat2 , lon2= None , None 

       for nodo in nodos.values():
           if nodo.nombre == punto_inicio_nombre:
               lat1 , lon1= nodo.latitud , nodo.longitud 
           if nodo.nombre == punto_fin_nombre:
               lat2 , lon2= nodo.latitud , nodo.longitud 

       if lat1 is not None and lat2 is not None:
           distancia= calcular_distancia(lat1 , lon1 , lat2 , lon2)
           self.resultado_label.setText(f'Distancia: {distancia:.2f} km')

           # Calcular la ruta más corta usando Dijkstra.
           ruta_mas_corta= dijkstra(nodos , punto_inicio_nombre , punto_fin_nombre)

           # Mostrar la ruta en el mapa.
           self.mostrar_ruta_en_mapa(ruta_mas_corta)

       else:
           QMessageBox.warning(self , 'Error' , 'No se encontraron las coordenadas.')

def crear_mapa_con_ruta(puntos_recoleccion, vertederos):
    """Crea un mapa con los puntos de recolección y vertederos, y dibuja las conexiones entre nodos."""
    
    mapa = folium.Map(location=[-12.0464, -77.0428], zoom_start=12)  # Coordenadas por defecto
    
    # Agregar marcadores para puntos de recolección
    for _, punto in puntos_recoleccion.iterrows():
        folium.Marker(
            location=[punto['latitud'], punto['longitud']],
            popup=punto['nombre'],
            icon=folium.Icon(color='blue')
        ).add_to(mapa)
    
    # Agregar marcadores para vertederos
    for _, vertedero in vertederos.iterrows():
        folium.Marker(
            location=[vertedero['latitud'], vertedero['longitud']],
            popup=vertedero['nombre'],
            icon=folium.Icon(color='red')
        ).add_to(mapa)

    # Dibujar las conexiones entre los nodos
    # for nodo in nodos.values():
    #     for vecino, distancia in nodo.vecinos:
    #         folium.PolyLine(
    #             locations=[(nodo.latitud, nodo.longitud), (vecino.latitud, vecino.longitud)],
    #             color='green',  # Color de la línea
    #             weight=2,  # Grosor de la línea
    #             opacity=0.6  # Opacidad de la línea
    #         ).add_to(mapa)

    return mapa

def main():
   dia_actual_en , hora_actual= obtener_dia_hora_actual()
   dia_actual_es= dias_semana.get(dia_actual_en , "")
   
   df_recoleccion , df_vertederos , df_camiones= cargar_datos([puntos_recoleccion_path,
                                                               vertederos_path,
                                                               camiones_path])
   
   # Filtrar puntos de recolección y vertederos.
   puntos_recoleccion_filtrados= filtrar_puntos(df_recoleccion,
                                                 dia_actual_es,
                                                 hora_actual)
   
   vertederos_filtrados= filtrar_puntos(df_vertederos,
                                         dia_actual_es,
                                         hora_actual)

   # Construir el grafo con todos los nodos y sus conexiones.
   global nodos  # Hacer que la variable nodos sea global para accederla en CalculadoraDistancia.
   nodos= construir_grafo(puntos_recoleccion_filtrados,
                           vertederos_filtrados)

   # Crear el mapa con los puntos filtrados.
   mapa = crear_mapa_con_ruta(puntos_recoleccion_filtrados,
                             vertederos_filtrados,
                             nodos)
   ruta_archivo_html= 'ruta_recoleccion_peru.html'
   guardar_mapa(mapa,ruta_archivo_html)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    dia_actual_en, hora_actual = obtener_dia_hora_actual()
    dia_actual_es = dias_semana.get(dia_actual_en, "")
    
    df_recoleccion, df_vertederos, df_camiones = cargar_datos([puntos_recoleccion_path,
                                                               vertederos_path,
                                                               camiones_path])
    
    # Filtrar puntos de recolección y vertederos.
    puntos_recoleccion_filtrados = filtrar_puntos(df_recoleccion,
                                                  dia_actual_es,
                                                  hora_actual)
    
    vertederos_filtrados = filtrar_puntos(df_vertederos,
                                          dia_actual_es,
                                          hora_actual)

    global nodos 
    nodos = construir_grafo(puntos_recoleccion_filtrados,
                            vertederos_filtrados)

    # Crear el mapa con los puntos filtrados y el grafo.
    mapa = crear_mapa_con_ruta(puntos_recoleccion_filtrados,
                               vertederos_filtrados)
    ruta_archivo_html = 'ruta_recoleccion_peru.html'
    guardar_mapa(mapa, ruta_archivo_html)

    ventana_mapa = VentanaMapa('ruta_recoleccion_peru.html')
    calculadora_distancia = CalculadoraDistancia()    
    
    widget_principal = QWidget()
    layout_principal = QHBoxLayout() 
    layout_principal.addWidget(calculadora_distancia) 
    layout_principal.addWidget(ventana_mapa) 
    
    calculadora_distancia.cargar_puntos(puntos_recoleccion_filtrados,
                                        vertederos_filtrados)

    widget_principal.setLayout(layout_principal)    
    widget_principal.show()

    sys.exit(app.exec_())