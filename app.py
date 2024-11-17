import mysql.connector
from mysql.connector import Error
from flask import Flask, render_template, jsonify, request
from datetime import datetime
from sqlalchemy import create_engine

app = Flask(__name__)

db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'mauricio',
    'database': 'optimizacion_rutas'
}
db_uri = f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}/{db_config['database']}"

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
    """
    Filtra los camiones según disponibilidad solamente
    """
    print(f"Hora actual: {hora_actual}")
    camiones_filtrados = []
    
    for camion in camiones:
        print(f"Verificando camión {camion['matricula']}: disponibilidad {camion['disponibilidad']}")
        
        # Solo verificar disponibilidad
        if camion['disponibilidad'] == 'Disponible':
            camiones_filtrados.append(camion)
            print(f"Camión {camion['matricula']} agregado (disponible)")
    
    print(f"Total de camiones filtrados: {len(camiones_filtrados)}")
    return camiones_filtrados

@app.route('/api/camiones')
def get_camiones():
    dia_actual_en, hora_actual = obtener_dia_hora_actual()
    _, _, camiones = cargar_datos()
    
    camiones_filtrados = filtrar_camiones(camiones, hora_actual)
    print(f'Hora actual: {hora_actual}')  # Debug print
    print('Camiones filtrados por turno y disponibilidad:', camiones_filtrados)
    
    return jsonify({'camiones': camiones_filtrados})  # Return only filtered trucks

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
    """
    Selecciona el mejor camión disponible basado en el rango de operación y la distancia total
    """
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

@app.route('/api/routes', methods=['POST'])
def get_routes():
    data = request.json
    vertedero_nombre = data['vertedero']
    num_puntos = int(data['num_puntos'])
    hora_actual = int(data.get('hour', datetime.now().hour))
    
    # Get current day and shift
    dia_actual_en, _ = obtener_dia_hora_actual()
    dia_actual_es = dias_semana.get(dia_actual_en, "")

    # Get points and landfills
    puntos_recoleccion, vertederos, _ = cargar_datos()
    vertedero_punto = next((v for v in vertederos if v['nombre'] == vertedero_nombre), None)
  
    if not vertedero_punto:
        return jsonify({'error': 'Vertedero no válido'}), 400

    # Filter and sort collection points
    puntos_recoleccion_filtrados = filtrar_puntos(puntos_recoleccion, dia_actual_es, hora_actual)
    puntos_cercanos = sorted(puntos_recoleccion_filtrados, key=lambda x: calcular_distancia(
        vertedero_punto['latitud'], vertedero_punto['longitud'], x['latitud'], x['longitud']))[:num_puntos]
    
    if not puntos_cercanos:
        return jsonify({'error': 'No hay puntos de recolección disponibles'}), 400

    # Generate route
    waypoints = [vertedero_punto] + puntos_cercanos
    print('Waypoints:', waypoints)

    nodos = construir_grafo(puntos_cercanos, [vertedero_punto])
    
    # Generar ruta completa
    ruta_completa = []
    punto_actual = vertedero_punto['nombre']
    
    # Crear una copia de puntos_cercanos para ir eliminando los visitados
    puntos_pendientes = [p['nombre'] for p in puntos_cercanos]
    
    while puntos_pendientes:
        mejor_distancia = float('inf')
        mejor_punto = None
        mejor_ruta = []
        
        # Encontrar el punto más cercano no visitado
        for punto in puntos_pendientes:
            ruta_actual = bellman_ford(nodos, punto_actual, punto)
            if ruta_actual:
                distancia_total = sum(
                    calcular_distancia(
                        nodos[ruta_actual[i]].latitud,
                        nodos[ruta_actual[i]].longitud,
                        nodos[ruta_actual[i+1]].latitud,
                        nodos[ruta_actual[i+1]].longitud
                    )
                    for i in range(len(ruta_actual)-1)
                )
                if distancia_total < mejor_distancia:
                    mejor_distancia = distancia_total
                    mejor_punto = punto
                    mejor_ruta = ruta_actual

        if mejor_punto is None:
            break
            
        # Agregar la mejor ruta encontrada
        if mejor_ruta:
            ruta_completa.extend(mejor_ruta[:-1])  # Evitar duplicar puntos
            punto_actual = mejor_punto
            puntos_pendientes.remove(mejor_punto)

    # Agregar ruta de regreso al vertedero
    ruta_regreso = bellman_ford(nodos, punto_actual, vertedero_punto['nombre'])
    if ruta_regreso:
        ruta_completa.extend(ruta_regreso)

    print('Ruta completa generada:', ruta_completa)

    if not ruta_completa:
        return jsonify({'error': 'No se encontraron rutas'}), 400

    # Calcular distancia total de la ruta
    distancia_total = 0
    for i in range(len(ruta_completa) - 1):
        nodo_actual = nodos[ruta_completa[i]]
        nodo_siguiente = nodos[ruta_completa[i + 1]]
        distancia_total += calcular_distancia(
            nodo_actual.latitud, nodo_actual.longitud,
            nodo_siguiente.latitud, nodo_siguiente.longitud
        )

    # Seleccionar el mejor camión
    _, _, camiones = cargar_datos()
    mejor_camion = seleccionar_mejor_camion(camiones, distancia_total)

    if not mejor_camion:
        return jsonify({'error': 'No hay camiones disponibles para esta ruta'}), 400

    coordinates = []
    for punto in ruta_completa:
        nodo = nodos[punto]
        coordinates.append([float(nodo.longitud), float(nodo.latitud)])
    
    return jsonify({
        'routes': [{
            'coordinates': coordinates,
            'distancia_total': round(distancia_total, 2),
            'camion': {
                'matricula': mejor_camion['matricula'],
                'capacidad': mejor_camion['capacidad_toneladas'],
                'rango': mejor_camion['rango_operacion'],
                'horario': mejor_camion['horario']
            }
        }]
    })

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

    app.run(debug=True, host='0.0.0.0', port=8080)