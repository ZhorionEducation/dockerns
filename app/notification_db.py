import uuid
from datetime import datetime
import logging
from app.Conexion_Sql import get_notifications_connection

# Configuración de logging
logger = logging.getLogger(__name__)

class NotificationDB:
    @staticmethod
    def get_all_notifications():
        """
        Obtener todas las notificaciones de la base de datos
        """
        db_conn = get_notifications_connection()  # Usar la función específica
        query = """
        SELECT n.id, n.message, n.author, n.timestamp, n.for_user
        FROM notifications n
        ORDER BY n.timestamp DESC
        """
        notifications = db_conn.execute_query(query)
        
        # Para cada notificación, obtener los usuarios que la han leído
        for notification in notifications:
            read_query = """
            SELECT user_id FROM notification_reads 
            WHERE notification_id = ?
            """
            readers = db_conn.execute_query(read_query, (notification['id'],))
            notification['read_by'] = [reader['user_id'] for reader in readers]
        
        return notifications

    @staticmethod
    def create_notification(message, author, for_user=None):
        """
        Crear una nueva notificación en la base de datos
        """
        db_conn = get_notifications_connection()  # Usar la función específica
        notification_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        query = """
        INSERT INTO notifications (id, message, author, timestamp, for_user)
        VALUES (?, ?, ?, ?, ?)
        """
        
        db_conn.execute_non_query(query, (notification_id, message, author, timestamp, for_user))
        
        return {
            'id': notification_id,
            'message': message,
            'author': author,
            'timestamp': timestamp,
            'for_user': for_user,
            'read_by': []
        }
    
    @staticmethod
    def mark_notification_read(notification_id, user_id):
        """
        Marcar una notificación como leída por un usuario
        """
        db_conn = get_notifications_connection()  # Usar la función específica
        
        # Comprobar si ya está marcada como leída
        check_query = """
        SELECT COUNT(*) as count FROM notification_reads 
        WHERE notification_id = ? AND user_id = ?
        """
        result = db_conn.execute_query(check_query, (notification_id, user_id))
        
        if result[0]['count'] == 0:
            # Si no está marcada como leída, insertar registro
            insert_query = """
            INSERT INTO notification_reads (notification_id, user_id, read_at)
            VALUES (?, ?, ?)
            """
            read_at = datetime.now().isoformat()
            db_conn.execute_non_query(insert_query, (notification_id, user_id, read_at))
        
        # Obtener la cantidad de usuarios que han leído esta notificación
        readers_query = """
        SELECT COUNT(*) as count FROM notification_reads 
        WHERE notification_id = ?
        """
        readers_count = db_conn.execute_query(readers_query, (notification_id,))[0]['count']
        
        return readers_count
    
    @staticmethod
    def mark_all_read(user_id):
        """
        Marcar todas las notificaciones como leídas por un usuario
        """
        db_conn = get_notifications_connection()  # Usar la función específica
        
        # Obtener todas las notificaciones que el usuario no ha leído
        unread_query = """
        SELECT n.id FROM notifications n
        LEFT JOIN notification_reads nr ON n.id = nr.notification_id AND nr.user_id = ?
        WHERE nr.notification_id IS NULL AND (n.for_user IS NULL OR n.for_user = ?)
        """
        unread_notifications = db_conn.execute_query(unread_query, (user_id, user_id))
        
        # Marcar cada notificación como leída
        read_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Usar formato compatible
        for notification in unread_notifications:
            insert_query = """
            INSERT INTO notification_reads (notification_id, user_id, read_at)
            VALUES (?, ?, ?)
            """
            db_conn.execute_non_query(insert_query, (notification['id'], user_id, read_at))
        
        return len(unread_notifications)
    
    @staticmethod
    def delete_notification(notification_id):
            """
            Eliminar una notificación y sus lecturas asociadas
            """
            db_conn = get_notifications_connection()  # Usar la función específica
            
            # Definimos primero las consultas
            # Eliminar primero los registros de lectura (por la integridad referencial)
            delete_reads_query = """
            DELETE FROM notification_reads WHERE notification_id = ?
            """
            
            # Luego la consulta para eliminar la notificación
            delete_query = """
            DELETE FROM notifications WHERE id = ?
            """
            
            # Ahora ejecutamos en el orden correcto
            db_conn.execute_non_query(delete_reads_query, (notification_id,))
            db_conn.execute_non_query(delete_query, (notification_id,))
            
            return True