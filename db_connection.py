import os
import mysql.connector
from mysql.connector import Error

ssl_ca = None
for path in ['/etc/ssl/cert.pem', '/etc/ssl/certs/ca-certificates.crt', '/etc/pki/tls/certs/ca-bundle.crt']:
    if os.path.exists(path):
        ssl_ca = path
        break

db_config = {
    'host': os.environ.get('DB_HOST', 'gateway01.sa-east-1.prod.aws.tidbcloud.com'),
    'port': int(os.environ.get('DB_PORT', 4000)),
    'user': os.environ.get('DB_USER', 'LDeCrEwcxCXM3W7.root'),
    'password': os.environ.get('DB_PASSWORD', 'c57uT99CtBhr4B7s'),
    'database': os.environ.get('DB_NAME', 'test'),
    'ssl_ca': ssl_ca,
    'ssl_verify_cert': True,
    'ssl_verify_identity': True
}

def obtener_conexion():
    conexion = None
    try:
        conexion = mysql.connector.connect(**db_config)
        print("Conexión a MySQL exitosa")
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
    return conexion