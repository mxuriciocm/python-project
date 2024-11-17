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

def actualizar_disponibilidad_camion(camion_id, disponibilidad):
    connection = get_db_connection()
    if not connection:
        return False

    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE camiones_basura
            SET disponibilidad = %s
            WHERE id = %s
        """, (disponibilidad, camion_id))
        connection.commit()
        return True
    except Error as e:
        print(f"Error actualizando disponibilidad: {e}")
        return False
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
    
    # Generate route
    waypoints = [vertedero_punto] + puntos_cercanos + [vertedero_punto]
    print('Waypoints:', waypoints)

    nodos = construir_grafo(puntos_cercanos, [vertedero_punto])
    rutas = bellman_ford(nodos, waypoints)
    print('Rutas calculadas:', rutas)

    if not rutas:
        return jsonify({'error': 'No se encontraron rutas'}), 400

    # Generate response with coordinates
    response_routes = []
    for ruta in rutas:
        coordinates = []
        for punto in ruta:
            nodo = nodos[punto]
            coordinates.append([nodo.longitud, nodo.latitud])
            print(f"Adding coordinates for {punto}: [{nodo.longitud}, {nodo.latitud}]")
      
        response_routes.append({
            'coordinates': coordinates
        })
  
    return jsonify({'routes': response_routes})

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

def bellman_ford(nodos, waypoints):
    """Generate a route that visits all waypoints in order"""
    if len(waypoints) < 2:
        return []
        
    # Create a single route visiting all waypoints in sequence
    ruta = []
    for i in range(len(waypoints)):
        ruta.append(waypoints[i]['nombre'])
        
    print('Ruta generada:', ruta)  # Debugging statement
    return [ruta]  # Return a list containing a single route

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