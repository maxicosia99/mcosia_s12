import mysql.connector
from mysql.connector import Error

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'mcosia_s12'
}

def obtener_conexion():
    conexion = None
    try:
        conexion = mysql.connector.connect(**db_config)
        print("Conexión a MySQL exitosa")
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
    return conexion