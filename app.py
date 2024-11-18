import mysql.connector
from mysql.connector import Error
from flask import Flask, render_template, jsonify, request
from datetime import datetime
from sqlalchemy import create_engine
import requests
import polyline

app = Flask(__name__)

db_config = {
    'host': 'autorack.proxy.rlwy.net',  
    'user': 'root',  
    'password': 'gvdXiRmqgoBYEwMjwcxXEJfvuwNqBook',  
    'database': 'db_routes',  
    'port': 24304  
}
db_uri = f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection   
    except Error as e:
        print(f"Error conectando a MySQL: {e}")
        return None

def cargar_datos():
    connection = get_db_connection()
    if not connection:
        return [], [], []

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT nombre, latitud, longitud, dia, turno
            FROM puntos_recoleccion
        """)
        puntos_recoleccion = cursor.fetchall()

        cursor.execute("""
            SELECT nombre, latitud, longitud, dia, turno
            FROM vertederos
        """)
        vertederos = cursor.fetchall()

        cursor.execute("""
            SELECT id, matricula, capacidad_toneladas, consumo_combustible,
                   velocidad_maxima, rango_operacion, horario, disponibilidad
            FROM camiones_basura
        """)
        camiones = cursor.fetchall()

        return puntos_recoleccion, vertederos, camiones

    except Error as e:
        print(f"Error consultando datos: {e}")
        return [], [], []
    finally:
        connection.close()

dias_semana = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miercoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sabado",
    "Sunday": "Domingo"
}

turnos = {
    "manana": range(0, 12),
    "tarde": range(12, 18),
    "noche": range(18, 24)
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    dia_actual_en, hora_actual = obtener_dia_hora_actual()
    dia_actual_es = dias_semana.get(dia_actual_en, "")
  
    puntos_recoleccion, vertederos, camiones = cargar_datos()
  
    puntos_recoleccion_filtrados = filtrar_puntos(puntos_recoleccion, dia_actual_es, hora_actual)
  
    for punto in puntos_recoleccion_filtrados:
        punto['lat'] = punto.pop('latitud')
        punto['lon'] = punto.pop('longitud')
  
    return jsonify({'points': puntos_recoleccion_filtrados})

def filtrar_camiones(camiones, hora_actual):
    return [camion for camion in camiones if camion['disponibilidad'] == 'Disponible']

@app.route('/api/camiones')
def get_camiones():
    dia_actual_en, hora_actual = obtener_dia_hora_actual()
    _, _, camiones = cargar_datos()
    
    camiones_filtrados = filtrar_camiones(camiones, hora_actual)
    return jsonify({'camiones': camiones_filtrados})  

def bellman_ford(nodos, origen, destino):
    distancias = {nodo: float('inf') for nodo in nodos}
    predecesores = {nodo: None for nodo in nodos}
    distancias[origen] = 0

    for _ in range(len(nodos) - 1):
        for nodo in nodos:
            for vecino, peso in nodos[nodo].vecinos:
                if distancias[nodo] != float('inf') and distancias[nodo] + peso < distancias[vecino.nombre]:
                    distancias[vecino.nombre] = distancias[nodo] + peso
                    predecesores[vecino.nombre] = nodo

    for nodo in nodos:
        for vecino, peso in nodos[nodo].vecinos:
            if distancias[nodo] != float('inf') and distancias[nodo] + peso < distancias[vecino.nombre]:
                raise ValueError("El grafo contiene un ciclo negativo")

    ruta = []
    actual = destino
    while actual is not None:
        ruta.append(actual)
        actual = predecesores[actual]
    ruta.reverse()

    return ruta if ruta[0] == origen else []

def seleccionar_mejor_camion(camiones, distancia_total):
    mejor_camion = None
    margen_minimo = float('inf')
    
    for camion in camiones:
        if camion['disponibilidad'] == 'Disponible':
            rango = float(camion['rango_operacion'])
            if rango >= distancia_total:
                margen = rango - distancia_total
                if margen < margen_minimo:
                    margen_minimo = margen
                    mejor_camion = camion
    
    return mejor_camion

def get_osrm_route(start_coords, end_coords):
    url = f"http://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}"
    params = {
        "overview": "full",
        "geometries": "polyline",
        "steps": "true"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data["code"] == "Ok":
            return {
                "geometry": data["routes"][0]["geometry"],
                "distance": data["routes"][0]["distance"] / 1000, 
                "duration": data["routes"][0]["duration"]
            }
    return None

@app.route('/api/routes', methods=['POST'])
def get_routes():
    try:
        data = request.json
        vertedero_nombre = data['vertedero']
        num_puntos = int(data['num_puntos'])
        hora_actual = int(data.get('hour', datetime.now().hour))
        
        puntos_recoleccion, vertederos, _ = cargar_datos()
        vertedero_punto = next((v for v in vertederos if v['nombre'] == vertedero_nombre), None)
        
        if not vertedero_punto:
            return jsonify({'error': 'Vertedero no válido'}), 400

        dia_actual_en, _ = obtener_dia_hora_actual()
        dia_actual_es = dias_semana.get(dia_actual_en, "")
        puntos_filtrados = filtrar_puntos(puntos_recoleccion, dia_actual_es, hora_actual)
        
        if not puntos_filtrados:
            return jsonify({'error': 'No hay puntos disponibles'}), 400

        if len(puntos_filtrados) < num_puntos:
            return jsonify({'error': f'Solo hay {len(puntos_filtrados)} puntos disponibles'}), 400

        # 1. Usar Bellman-Ford para determinar el orden óptimo
        nodos = construir_grafo(puntos_filtrados, [vertedero_punto])
        punto_actual = vertedero_punto['nombre']
        puntos_pendientes = [p['nombre'] for p in puntos_filtrados[:num_puntos]]
        ruta_optima = [punto_actual]
        
        while puntos_pendientes:
            mejor_distancia = float('inf')
            mejor_punto = None
            
            for punto in puntos_pendientes:
                try:
                    ruta = bellman_ford(nodos, punto_actual, punto)
                    if ruta:
                        distancia = sum(
                            calcular_distancia(
                                nodos[ruta[i]].latitud,
                                nodos[ruta[i]].longitud,
                                nodos[ruta[i+1]].latitud,
                                nodos[ruta[i+1]].longitud
                            )
                            for i in range(len(ruta)-1)
                        )
                        if distancia < mejor_distancia:
                            mejor_distancia = distancia
                            mejor_punto = punto
                except Exception as e:
                    print(f"Error calculando ruta para punto {punto}: {str(e)}")
                    continue
            
            if mejor_punto:
                ruta_optima.append(mejor_punto)
                punto_actual = mejor_punto
                puntos_pendientes.remove(mejor_punto)
            else:
                return jsonify({'error': 'No se pudo encontrar una ruta válida'}), 400
        
        ruta_optima.append(vertedero_punto['nombre'])

        # 2. Usar OSRM para obtener las rutas reales
        ruta_completa = []
        distancia_total = 0
        waypoints = []
        
        for i in range(len(ruta_optima) - 1):
            punto_actual = next(p for p in [vertedero_punto] + puntos_filtrados if p['nombre'] == ruta_optima[i])
            punto_siguiente = next(p for p in [vertedero_punto] + puntos_filtrados if p['nombre'] == ruta_optima[i + 1])
            
            waypoints.append({
                "lat": punto_actual['latitud'],
                "lon": punto_actual['longitud'],
                "name": punto_actual['nombre']
            })
            
            route = get_osrm_route(
                (punto_actual['latitud'], punto_actual['longitud']),
                (punto_siguiente['latitud'], punto_siguiente['longitud'])
            )
            if route:
                ruta_completa.append(route['geometry'])
                distancia_total += route['distance']
            else:
                return jsonify({'error': 'No se pudo obtener la ruta entre algunos puntos'}), 400

        if not ruta_completa:
            return jsonify({'error': 'No se pudo generar la ruta completa'}), 400

        # Seleccionar camión - Modificado para usar solo camiones filtrados
        _, _, todos_camiones = cargar_datos()
        camiones_filtrados = filtrar_camiones(todos_camiones, hora_actual)
        mejor_camion = seleccionar_mejor_camion(camiones_filtrados, distancia_total)

        if not mejor_camion:
            return jsonify({'error': 'No hay camiones disponibles en este horario para esta ruta'}), 400

        # Combinar geometrías
        try:
            geometria_completa = ruta_completa[0]
            for geometry in ruta_completa[1:]:
                decoded = polyline.decode(geometry)
                geometria_completa = polyline.encode(polyline.decode(geometria_completa) + decoded[1:])

            return jsonify({
                'routes': [{
                    'geometry': geometria_completa,
                    'waypoints': waypoints,
                    'distancia_total': round(distancia_total, 2),
                    'camion': {
                        'matricula': mejor_camion['matricula'],
                        'capacidad': mejor_camion['capacidad_toneladas'],
                        'rango': mejor_camion['rango_operacion'],
                        'horario': mejor_camion['horario']
                    }
                }]
            })
        except Exception as e:
            print(f"Error generando respuesta final: {str(e)}")
            return jsonify({'error': 'Error al generar la ruta final'}), 500

    except Exception as e:
        print(f"Error general en get_routes: {str(e)}")
        return jsonify({'error': f'Error inesperado: {str(e)}'}, 500)

@app.route('/api/vertederos')
def get_vertederos():
    dia_actual_en, hora_actual = obtener_dia_hora_actual()
    dia_actual_es = dias_semana.get(dia_actual_en, "")
  
    _, vertederos, _ = cargar_datos()
    vertederos_filtrados = filtrar_puntos(vertederos, dia_actual_es, hora_actual)
  
    for vertedero in vertederos_filtrados:
        vertedero['lat'] = vertedero.pop('latitud')
        vertedero['lon'] = vertedero.pop('longitud')
  
    return jsonify({'vertederos': vertederos_filtrados})

def filtrar_puntos(puntos, dia_actual, hora_actual):
    puntos_filtrados = [
        punto for punto in puntos
        if punto['dia'] == dia_actual and punto['turno'].lower() in turnos and hora_actual in turnos[punto['turno'].lower()]
    ]
    return puntos_filtrados

def calcular_distancia(lat1, lon1, lat2, lon2):
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
  
    for punto in puntos_recoleccion:
        nodos[punto['nombre']] = Nodo(punto['nombre'], punto['latitud'], punto['longitud'])
  
    for vertedero in vertederos:
        nodos[vertedero['nombre']] = Nodo(vertedero['nombre'], vertedero['latitud'], vertedero['longitud'])

    for nodo1 in nodos.values():
        for nodo2 in nodos.values():
            if nodo1 != nodo2:
                distancia = calcular_distancia(nodo1.latitud, nodo1.longitud, nodo2.latitud, nodo2.longitud)
                nodo1.agregar_vecino(nodo2, distancia)
  
    return nodos

def obtener_dia_hora_actual():
    from datetime import datetime
    ahora = datetime.now()
    dia_actual_en = ahora.strftime("%A")
    hora_actual = ahora.hour
    return dia_actual_en, hora_actual

if __name__ == '__main__':
    dia_actual_en, hora_actual = obtener_dia_hora_actual()
    dia_actual_es = dias_semana.get(dia_actual_en, "")
  
    df_recoleccion, df_vertederos, df_camiones = cargar_datos()

    puntos_recoleccion_filtrados = filtrar_puntos(df_recoleccion, dia_actual_es, hora_actual)
  
    vertederos_filtrados = filtrar_puntos(df_vertederos, dia_actual_es, hora_actual)

    global nodos
    nodos = construir_grafo(puntos_recoleccion_filtrados, vertederos_filtrados)

    app.run(debug=True, host='0.0.0.0', port=8081)