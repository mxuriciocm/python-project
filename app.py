import pandas as pd
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    dia_actual_en, hora_actual = obtener_dia_hora_actual()
    dia_actual_es = dias_semana.get(dia_actual_en, "")
    
    df_recoleccion, df_vertederos, df_camiones = cargar_datos([puntos_recoleccion_path, vertederos_path, camiones_path])
    
    puntos_recoleccion_filtrados = filtrar_puntos(df_recoleccion, dia_actual_es, hora_actual)
    puntos = puntos_recoleccion_filtrados.to_dict(orient='records')
    
    # Convert latitud and longitud to lat and lon for the frontend
    for punto in puntos:
        punto['lat'] = punto.pop('latitud')
        punto['lon'] = punto.pop('longitud')
    
    return jsonify({'points': puntos})

@app.route('/api/routes', methods=['POST'])
def get_routes():
    data = request.json
    vertedero_nombre = data['vertedero']
    num_puntos = int(data['num_puntos'])
    
    vertedero_punto = next((v for v in vertederos if v['nombre'] == vertedero_nombre), None)
    if not vertedero_punto:
        return jsonify({'error': 'Vertedero no válido'}), 400
    
    puntos_cercanos = sorted(
        points, 
        key=lambda p: calcular_distancia(vertedero_punto['lat'], vertedero_punto['lon'], p['lat'], p['lon'])
    )[:num_puntos]
    
    waypoints = [vertedero_punto] + puntos_cercanos + [vertedero_punto]
    rutas = bellman_ford(nodos, waypoints)
    
    return jsonify({'routes': rutas})

@app.route('/api/vertederos')
def get_vertederos():
    dia_actual_en, hora_actual = obtener_dia_hora_actual()
    dia_actual_es = dias_semana.get(dia_actual_en, "")
    
    df_vertederos = pd.read_json(vertederos_path)
    vertederos_filtrados = filtrar_puntos(df_vertederos, dia_actual_es, hora_actual)
    vertederos = vertederos_filtrados.to_dict(orient='records')
    
    # Convert latitud and longitud to lat and lon for the frontend
    for vertedero in vertederos:
        vertedero['lat'] = vertedero.pop('latitud')
        vertedero['lon'] = vertedero.pop('longitud')
    
    return jsonify({'vertederos': vertederos})

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

def bellman_ford(nodos, waypoints):
    distancias = {nodo: float('inf') for nodo in nodos}
    distancias[waypoints[0]['nombre']] = 0
    predecesores = {nodo: None for nodo in nodos}
    
    for _ in range(len(nodos) - 1):
        for nodo in nodos.values():
            for vecino, peso in nodo.vecinos:
                if distancias[nodo.nombre] + peso < distancias[vecino.nombre]:
                    distancias[vecino.nombre] = distancias[nodo.nombre] + peso
                    predecesores[vecino.nombre] = nodo.nombre
    
    rutas = []
    for _ in range(3):  # Obtener hasta 3 rutas
        ruta = []
        nodo = waypoints[-1]['nombre']
        while nodo:
            ruta.append(nodo)
            nodo = predecesores[nodo]
        rutas.append(ruta[::-1])
    
    return rutas

def obtener_dia_hora_actual():
    from datetime import datetime
    ahora = datetime.now()
    dia_actual_en = ahora.strftime("%A")
    hora_actual = ahora.hour
    return dia_actual_en, hora_actual

if __name__ == '__main__':
    dia_actual_en, hora_actual = obtener_dia_hora_actual()
    dia_actual_es = dias_semana.get(dia_actual_en, "")
    
    df_recoleccion, df_vertederos, df_camiones = cargar_datos([puntos_recoleccion_path, vertederos_path, camiones_path])

    puntos_recoleccion_filtrados = filtrar_puntos(df_recoleccion, dia_actual_es, hora_actual)
    
    vertederos_filtrados = filtrar_puntos(df_vertederos, dia_actual_es, hora_actual)

    global nodos 
    nodos = construir_grafo(puntos_recoleccion_filtrados, vertederos_filtrados)

    app.run(debug=True, host='0.0.0.0', port=8080)