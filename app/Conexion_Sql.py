import pyodbc
from typing import List, Dict, Any
import logging
from cryptography.fernet import Fernet
from dotenv import dotenv_values
import os
import io  # Importar io para manejar streams de texto

# Ruta al archivo de clave
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
key_path = os.path.join(base_dir, "Key_Encryptation(NO_BORRAR)", "encryption.key")
encrypted_env_path = os.path.join(base_dir, "credentials.env.encrypted")

# Cargar la clave desde el archivo
with open(key_path, "rb") as key_file:
    key = key_file.read()

# Crear el objeto Fernet
cipher_suite = Fernet(key)

# Leer y desencriptar el archivo encriptado
with open(encrypted_env_path, "rb") as encrypted_file:
    encrypted_data = encrypted_file.read()

decrypted_data = cipher_suite.decrypt(encrypted_data)

# Cargar las variables de entorno desde el contenido desencriptado
env_variables = dotenv_values(stream=io.StringIO(decrypted_data.decode("utf-8")))

class DatabaseConnection:
    def __init__(self, database: str):
        self.database = database
        self.connection_string = (
            f"Driver={{SQL Server}};"
            f"Server={env_variables.get('DB_SERVER')};"
            f"Database={database};"
            f"UID={env_variables.get('DB_USER')};"
            f"PWD={env_variables.get('DB_PASSWORD')};"
            "TrustServerCertificate=yes;"
            f"Timeout={env_variables.get('DB_TIMEOUT')};"
        )

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

   

    def test_connection(self) -> bool:
        """Test database connection before executing queries"""
        try:
            with pyodbc.connect(self.connection_string, timeout=5) as connection:
                return True
        except pyodbc.Error as e:
            self.logger.error(f"Connection test failed for database {self.database}: {str(e)}")
            return False

    def execute_query(self, query: str, params: tuple = None) -> List[Dict[Any, Any]]:
        """
        Ejecuta una consulta SQL y retorna los resultados como lista de diccionarios
        """
        if not self.test_connection():
            raise ConnectionError(f"Cannot connect to database: {self.database}")

        try:
            with pyodbc.connect(self.connection_string) as connection:
                cursor = connection.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
 
                # Obtener nombres de columnas
                columns = [column[0] for column in cursor.description]
                
                # Convertir resultados a lista de diccionarios
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
          
                return results

        except pyodbc.Error as e:
            self.logger.error(f"Database error in {self.database}: {str(e)}")
            raise
        except Exception as ex:
            self.logger.error(f"Unexpected error in {self.database}: {str(ex)}")
            raise

    def execute_non_query(self, query: str, params: tuple = None) -> int:
        """
        Ejecuta una consulta SQL que no devuelve resultados (INSERT, UPDATE, DELETE)
        Retorna el número de filas afectadas
        """
        if not self.test_connection():
            raise ConnectionError(f"Cannot connect to database: {self.database}")

        try:
            with pyodbc.connect(self.connection_string) as connection:
                cursor = connection.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # Confirmar cambios
                connection.commit()
                
                # Retornar número de filas afectadas
                return cursor.rowcount

        except pyodbc.Error as e:
            self.logger.error(f"Database error in {self.database}: {str(e)}")
            raise
        except Exception as ex:
            self.logger.error(f"Unexpected error in {self.database}: {str(ex)}")
            raise
    
def get_notifications_connection():
    """
    Retorna una conexión específica para la base de datos de notificaciones
    con credenciales específicas
    """
    # Creamos una instancia de la conexión
    db_conn = DatabaseConnection('NotificacionesTrackingNS')
    
    # Sobreescribimos la cadena de conexión con las credenciales específicas
    db_conn.connection_string = (
        "Driver={SQL Server};"
        "Server=newsbd;"  # Servidor específico
        "Database=NotificacionesTrackingNS;"
        "UID=sa;"         # Usuario específico
        "PWD=NSnet200;"   # Contraseña específica
        "TrustServerCertificate=yes;"
        f"Timeout={env_variables.get('DB_TIMEOUT')};"
    )
    
    return db_conn
