from ldap3 import Server, Connection, ALL, SIMPLE, SUBTREE
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

def authenticate_user(username, password):
    AD_SERVER = env_variables.get('LDAP_SERVER')
    DOMAIN = env_variables.get('LDAP_DOMAIN')
    BASE_DN = env_variables.get('LDAP_BASE_DN')
    
    try:
        user_dn = f"{username}@{DOMAIN}.local"
        server = Server(AD_SERVER, port=389, get_info=ALL)
        conn = Connection(server,
                         user=user_dn,
                         password=password,
                         authentication=SIMPLE)
        
        if conn.bind():
            search_filter = f'(&(objectClass=user)(sAMAccountName={username}))'
            conn.search(BASE_DN,
                    search_filter,
                    search_scope=SUBTREE,
                    attributes=[
                        'displayName', 'badPwdCount', 'lockoutTime', 'department',
                        'cn', 'sn', 'givenName', 'mail', 'telephoneNumber', 'employeeID'
                    ])
    
            if len(conn.entries) > 0:
                user_entry = conn.entries[0]
                bad_pwd_count = user_entry.badPwdCount.value
                department = str(user_entry.department) if hasattr(user_entry, 'department') else 'No especificado'
                print(f"Área del usuario: {department}")
                
                account_status = {
                    'badPwdCount': bad_pwd_count,
                    'lockoutTime': user_entry.lockoutTime.value
                }
                
                # Si está bloqueado
                if bad_pwd_count >= 3:
                    return False, None, account_status, 'Usuario bloqueado. Comuníquese con la mesa de ayuda.'
                    
                # Si la autenticación es exitosa
                user_info = {
                    'displayName': user_entry.displayName.value if hasattr(user_entry, 'displayName') else username,
                    'username': username,
                    'department': department,
                    'cn': user_entry.cn.value if hasattr(user_entry, 'cn') else '',
                    'sn': user_entry.sn.value if hasattr(user_entry, 'sn') else '',
                    'givenName': user_entry.givenName.value if hasattr(user_entry, 'givenName') else '',
                    'mail': user_entry.mail.value if hasattr(user_entry, 'mail') else '',
                    'telephoneNumber': user_entry.telephoneNumber.value if hasattr(user_entry, 'telephoneNumber') else '',
                    'employeeID': user_entry.employeeID.value if hasattr(user_entry, 'employeeID') else ''
                }
                
                # Imprimir toda la información del usuario
                print(f"Información del usuario: {user_entry.entry_to_json()}")
                
                return True, user_info, account_status, None  # Retorna True para autenticación exitosa
            
        return False, None, {'badPwdCount': 0, 'lockoutTime': None}, 'Usuario o contraseña incorrectos.'

    except Exception as e:
        print(f"Error de conexión AD: {str(e)}")
        return False, None, {'badPwdCount': 0, 'lockoutTime': None}, 'Error de conexión con el servidor de autenticación.'