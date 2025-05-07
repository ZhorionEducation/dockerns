import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.auth import authenticate_user  # Cambiar a importación absoluta
from app.Conexion_Sql import DatabaseConnection
from app.notification_db import NotificationDB
from app.models import OrderInfo
from app.queries_unified import get_unified_orders
from app.queries_unified_vendedores import get_unified_orders_vendedores
from functools import lru_cache
import time
import requests
from datetime import datetime
import uuid
import pytz

CACHE_TIMEOUT = 5000  # 10 minutos en segundos

cache = {}


main = Blueprint('main', __name__)

def order_in_date_range(order, start_date_obj, end_date_obj):
    # Get fecha_registro_pedido (creation date)
    fecha_registro_pedido = order.get('fecha_registro_pedido', '')
    
    # If we have a datetime object, use it directly
    if isinstance(fecha_registro_pedido, datetime):
        order_date = fecha_registro_pedido
    # If it's a string, try to parse it
    elif fecha_registro_pedido:
        try:
            # Try standard datetime format first
            order_date = datetime.strptime(fecha_registro_pedido, '%Y-%m-%d %H:%M:%S')
        except Exception:
            try:
                # Try alternative date format
                order_date = datetime.strptime(fecha_registro_pedido, '%Y-%m-%d')
            except Exception:
                # If parsing fails, this order doesn't match
                return False
    else:
        # No creation date available
        return False
    
    # Check if the date is in the requested range
    return start_date_obj <= order_date <= end_date_obj



def get_cache_key(start_date, end_date, guia=None, cliente=None, transportadora=None, pedido=None, vendedor=None, is_vendedor=False, factura=None, referencia=None):
    """
    Busca una clave de caché existente que contenga los datos necesarios o genera una nueva.
    Considera tanto el rango de fechas como los filtros aplicados.
    """
    # Si estamos en modo vendedor, simplemente usar el nombre del vendedor como clave
    if is_vendedor and vendedor:
        return f"vendedor_{vendedor}_{cliente or ''}_{pedido or ''}_{factura or ''}_{referencia or ''}"

    # Verificar si las fechas son None
    if start_date is None or end_date is None:
        # Si no hay fechas pero hay vendedor, usar el vendedor como clave
        if vendedor:
            return f"vendedor_{vendedor}_{cliente or ''}_{pedido or ''}_{factura or ''}_{referencia or ''}"
        # Para otros casos sin fechas, generar una clave con los filtros disponibles
        filters = '_'.join([f for f in [guia or '', cliente or '', transportadora or '', pedido or '', factura or '', referencia or ''] if f])
        return f"no_date_{filters}" if filters else "no_date"

    # Continuar con el procesamiento normal cuando hay fechas
    try:
        start_date_obj = datetime.strptime(start_date, '%Y%m')
        end_date_obj = datetime.strptime(end_date, '%Y%m')
    except ValueError:
        # Si no podemos convertir las fechas, usamos el formato directo
        return f"{start_date}_{end_date}_{'_'.join([guia or '', cliente or '', transportadora or '', pedido or '', vendedor or '', factura or '', referencia or ''])}" if any([guia, cliente, transportadora, pedido, vendedor, factura, referencia]) else f"{start_date}_{end_date}"

    # Primero intentamos encontrar una clave exacta (sin filtros)
    exact_key = f"{start_date}_{end_date}"
    if exact_key in cache and not any([guia, cliente, transportadora, pedido, vendedor, factura, referencia]):
        return exact_key

    # Si hay filtros, buscamos primero un caché que contenga exactamente nuestras fechas
    if any([guia, cliente, transportadora, pedido, vendedor, factura, referencia]) and exact_key in cache:
        return exact_key
    
    # Ahora buscamos un caché más amplio que contenga nuestro rango
    for cached_key in cache:
        cached_parts = cached_key.split('_')
        if len(cached_parts) < 2:
            continue
            
        cached_start, cached_end = cached_parts[0], cached_parts[1]
        
        # Ignoramos claves que tienen filtros adicionales
        if len(cached_parts) > 2:
            continue
            
        try:
            cached_start_date = datetime.strptime(cached_start, '%Y%m')
            cached_end_date = datetime.strptime(cached_end, '%Y%m')
        except ValueError:
            continue
        
        # Si encontramos un caché que contiene completamente nuestro rango de fechas, lo usamos
        if cached_start_date <= start_date_obj and cached_end_date >= end_date_obj:
            return cached_key
    
    # Si no encontramos nada, creamos una nueva clave
    if any([guia, cliente, transportadora, pedido, vendedor, factura, referencia]):
        filters = [guia or '', cliente or '', transportadora or '', pedido or '', vendedor or '', factura or '', referencia or '']
        return f"{start_date}_{end_date}_{'_'.join(filters)}"
    else:
        return f"{start_date}_{end_date}"

def fetch_combined_data(start_date=None, end_date=None, guia=None, cliente=None, transportadora=None, pedido=None, vendedor=None, is_vendedor=False, limit=10, offset=0, factura=None, referencia=None):
    try:
        cache_key = get_cache_key(start_date, end_date, guia, cliente, transportadora, pedido, vendedor, is_vendedor, factura, referencia)
        
        if cache_key in cache:
            cached_data, timestamp = cache[cache_key]
            if time.time() - timestamp < CACHE_TIMEOUT:
                # Para vista de vendedores, usar datos sin filtrar
                if is_vendedor:
                    filtered_data = cached_data
                    
                    # Apply filters
                    if cliente:
                        filtered_data = [order for order in filtered_data
                                         if str(order.get('cliente', '')).lower().find(str(cliente).lower()) != -1]
                    if pedido:
                        filtered_data = [order for order in filtered_data
                                         if str(order.get('numero_pedido', '')).lower().find(str(pedido).lower()) != -1]
                    if factura:
                        filtered_data = [order for order in filtered_data
                                         if str(order.get('numero_factura', '')).lower().find(str(factura).lower()) != -1]
                    if referencia:
                        filtered_data = [order for order in filtered_data
                                         if str(order.get('referencia', '')).lower().find(str(referencia).lower()) != -1]
                    
                    total_count = len(filtered_data)
                    paginated_data = filtered_data[offset:offset + limit]
                    return paginated_data, total_count

                filtered_data = cached_data
                
                # Filtrar por rango de fechas solicitado si es necesario
                if start_date and end_date:
                    # Convertir start_date (AAAAMM) a fecha con día 1
                    start_date_obj = datetime.strptime(start_date, '%Y%m')
                    # Convertir end_date y ajustar para obtener el último día del mes
                    import calendar
                    end_date_tmp = datetime.strptime(end_date, '%Y%m')
                    last_day = calendar.monthrange(end_date_tmp.year, end_date_tmp.month)[1]
                    end_date_obj = datetime(end_date_tmp.year, end_date_tmp.month, last_day)

                    # Filtrar datos cacheados para el rango solicitado
                    filtered_data = [
                        order for order in filtered_data
                        if order_in_date_range(order, start_date_obj, end_date_obj)
                    ]

                # Aplicar los demás filtros si existen
                if guia:
                    filtered_data = [order for order in filtered_data 
                                    if str(order.get('guia', '')).lower().find(str(guia).lower()) != -1]
                if cliente:
                    filtered_data = [order for order in filtered_data 
                                    if str(order.get('cliente', '')).lower().find(str(cliente).lower()) != -1]
                if transportadora:
                    filtered_data = [order for order in filtered_data 
                                    if str(order.get('transportadora', '')).lower().find(str(transportadora).lower()) != -1]
                if pedido:
                    filtered_data = [order for order in filtered_data 
                                    if str(order.get('numero_pedido', '')).lower().find(str(pedido).lower()) != -1]
                if vendedor:
                    filtered_data = [order for order in filtered_data 
                                    if str(order.get('razon_social_vendedor', '')).lower().find(str(vendedor).lower()) != -1]
                
                # Aplicar paginación
                total_count = len(filtered_data)
                paginated_data = filtered_data[offset:offset + limit]
                return paginated_data, total_count

        # Si no hay datos en caché o queremos recargarlos, consultamos la base de datos
        if is_vendedor:
            # Usar el nuevo query unificado para vendedores
            db_connection = DatabaseConnection('SGV_BKGENERICABASE1')
            query = get_unified_orders_vendedores(vendedor, cliente, pedido, factura, referencia)
            unified_data = db_connection.execute_query(query)
            
            # Transformar los datos al formato que espera la aplicación
            all_combined_data = []
            for item in unified_data:
                order_data = {
                    'Guia': item.get('Guia', 'Sin guía'),
                    'Transportador': item.get('Transportador', 'Sin transportador'),
                    'Razon social cliente': item.get('Razon social cliente', 'Desconocido'),
                    'Numero de pedido': item.get('Numero de pedido', ''),
                    'Numero de factura': item.get('Numero de factura', ''),
                    'Referencia': item.get('Referencia', ''),
                    'LINEA': item.get('LINEA', ''),
                    'GRUPO': item.get('GRUPO', ''),
                    'SUBGRUPO': item.get('SUBGRUPO', ''),
                    'Cantidad': item.get('Cantidad', ''),
                    'Fecha_Despacho': item.get('Fecha_Despacho', 'Pendiente'),
                    'Fecha_Picking': item.get('Fecha picking', 'Pendiente'),
                    'Fecha de alistamiento': item.get('Fecha de alistamiento', 'Pendiente'),
                    'Fecha aprobacion Cartera': item.get('Fecha aprobacion Cartera', 'Pendiente'),
                    'Razon social vendedor': item.get('Razon social vendedor', 'Desconocido'),
                    'Fecha Preparacion de pedido': item.get('Fecha Preparacion de pedido', 'Pendiente'),
                    'Estado del documento': item.get('Estado del documento', ''),
                    'Fecha Registro de pedido': item.get('Fecha Registro de pedido', ''),
                    'Extencion del item': item.get('Extencion del item', ''),
                    'RUTA': item.get('RUTA', item.get('Transportador', '')),
                    'Keypedido': item.get('Keypedido', '')
                }
                
                order_info = OrderInfo.from_dict(order_data)
                all_combined_data.append(order_info.__dict__)
        else:
            # Para el dashboard principal, usamos el nuevo query unificado
            db_connection = DatabaseConnection('SGV_BKGENERICABASE1')  # Usamos esta conexión porque la mayoría de las tablas están ahí
            
            # Obtener datos usando el query unificado
            query = get_unified_orders(start_date, end_date, guia, cliente, transportadora, pedido, vendedor, None, None)
            unified_data = db_connection.execute_query(query)
            
            # Transformar los datos al formato que espera la aplicación
            all_combined_data = []
            for item in unified_data:
                order_data = {
                    'Guia': item.get('Guia', 'Sin guía'),
                    'Transportador': item.get('Transportador', 'Sin transportador'),
                    'Razon social cliente': item.get('Razon social cliente', 'Desconocido'),
                    'Numero de pedido': item.get('Numero de pedido', ''),
                    'Numero de factura': item.get('Numero de factura', ''),
                    'Referencia': item.get('Referencia', ''),
                    'LINEA': '',  # No está en el nuevo query
                    'GRUPO': '',  # No está en el nuevo query
                    'SUBGRUPO': '',  # No está en el nuevo query
                    'Cantidad': item.get('Cantidad', ''),
                    'Fecha_Despacho': item.get('Fecha_Despacho', 'Pendiente'),
                    'Fecha_Picking': item.get('Fecha picking', 'Pendiente'),
                    'Fecha de alistamiento': item.get('Fecha de alistamiento', 'Pendiente'),
                    'Fecha aprobacion Cartera': item.get('Fecha aprobacion Cartera', 'Pendiente'),
                    'Razon social vendedor': item.get('Razon social vendedor', 'Desconocido'),
                    'Fecha Preparacion de pedido': item.get('Fecha Preparacion de pedido', 'Pendiente'),
                    'Estado del documento': item.get('Estado del documento', ''),
                    'Fecha Registro de pedido': item.get('Fecha Registro de pedido', ''),
                    'Extencion del item': item.get('Extencion del item', ''),
                    'RUTA': item.get('RUTA', item.get('Transportador', '')),
                    'Keypedido': item.get('Keypedido', '')
                }
                
                order_info = OrderInfo.from_dict(order_data)
                all_combined_data.append(order_info.__dict__)

        # Guardar en caché
        cache[cache_key] = (all_combined_data, time.time())

        # Retornar solo la porción solicitada
        total_count = len(all_combined_data)
        paginated_data = all_combined_data[offset:offset + limit]
        
        return paginated_data, total_count

    except Exception as e:
        logging.error(f'Error al obtener datos combinados: {e}')
        return [], 0
    
@main.route('/')  # Agregar ruta raíz
def index():
    return redirect(url_for('main.login'))

@main.route('/acceso_denegado')
def acceso_denegado():
    return render_template('acceso_denegado.html'), 403

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Autenticación del usuario
        success, user_info, account_status, error_message = authenticate_user(username, password)
        
        if success:
            session['user_info'] = user_info  # Establecer la sesión del usuario con el diccionario de información
            
            # Imprimir los datos del usuario
            print(f"Usuario logueado: {user_info}")
            
            # Redirigir según el área del usuario
            if user_info['displayName'] == 'Alejandro Moreno Jimenez':  # Reemplaza con el nombre exacto del usuario
                return redirect(url_for('main.dashboard'))
            elif user_info['department'] == 'Planeacion y Riesgos':
                return redirect(url_for('main.dashboard'))
            elif user_info['department'] == 'Soluciones Dentales':
                return redirect(url_for('main.dashboard_vendedores'))
            else:
                # Redirigir a un dashboard genérico o mostrar un mensaje de error
                return redirect(url_for('main.acceso_denegado'))
        else:
            # Manejar error de autenticación
            flash(error_message, 'danger')
            
            return redirect(url_for('main.login'))

    return render_template('login.html')

def normalize_name(name):
    parts = name.split()
    if len(parts) >= 2:
        # Asumimos que las últimas dos palabras son los apellidos
        last_two_parts = parts[-2:]
        return " ".join(last_two_parts).lower()
    return name.lower()

@main.route('/dashboard_vendedores')
def dashboard_vendedores():
    if 'user_info' not in session:
        flash('Debe iniciar sesión primero', 'warning')
        return redirect(url_for('main.login'))
    
    displayName = session['user_info']['displayName']
    normalized_displayName = normalize_name(displayName)

    cliente = request.args.get('cliente', '')
    pedido = request.args.get('pedido', '')
    factura = request.args.get('factura', '')
    referencia = request.args.get('referencia', '')
    
    # Pasar is_vendedor=True
    orders, total_count = fetch_combined_data(
        vendedor=normalized_displayName, 
        is_vendedor=True,
        limit=10,
        offset=0,
        cliente=cliente,
        pedido=pedido,
        factura=factura,
        referencia=referencia
    )
    
    if not orders:
        flash('No se encontraron datos para mostrar', 'warning')
    
    # Pasar el nombre normalizado como una variable separada
    return render_template('dashboard_Vendedores.html', 
                          displayName=displayName, 
                          normalized_displayName=normalized_displayName,
                          orders=orders, 
                          total_count=total_count,
                          cliente=cliente,
                          pedido=pedido,
                          factura=factura,
                          referencia=referencia)

@main.route('/dashboard')
def dashboard():
    if 'user_info' not in session:
        flash('Debe iniciar sesión primero', 'warning')
        return redirect(url_for('main.login'))
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    orders = fetch_combined_data(start_date=start_date, end_date=end_date)
    
    return render_template('dashboard.html', 
                         displayName=session['user_info']['displayName'],
                         orders=orders)

@main.route('/api/orders', methods=['GET'])
def get_orders():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    guia = request.args.get('guia')
    cliente = request.args.get('cliente')
    transportadora = request.args.get('transportadora')
    pedido = request.args.get('pedido')
    vendedor = request.args.get('vendedor')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    offset = (page - 1) * limit

    if not start_date or not end_date:
        return jsonify({'error': 'Fechas no proporcionadas'}), 400

    combined_data, total_count = fetch_combined_data(
        start_date=start_date, 
        end_date=end_date, 
        guia=guia, 
        cliente=cliente, 
        transportadora=transportadora, 
        pedido=pedido, 
        vendedor=vendedor, 
        limit=limit, 
        offset=offset
    )
    
    if combined_data is None:
        return jsonify({'error': 'Error al obtener datos combinados'}), 500

    total_pages = (total_count + limit - 1) // limit

    return jsonify({
        'orders': combined_data,
        'totalPages': total_pages,
        'currentPage': page,
        'totalItems': total_count
    })

@main.route('/api/vendedor_orders', methods=['GET'])
def get_vendedor_orders():
    vendedor = request.args.get('vendedor')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    offset = (page - 1) * limit
    cliente = request.args.get('cliente', '')
    pedido = request.args.get('pedido', '')
    factura = request.args.get('factura', '')
    referencia = request.args.get('referencia', '')
    
    if not vendedor:
        return jsonify({'error': 'Vendedor no especificado'}), 400
    
    combined_data, total_count = fetch_combined_data(
        vendedor=vendedor,
        is_vendedor=True,
        limit=limit,
        offset=offset,
        cliente=cliente,
        pedido=pedido,
        factura=factura,
        referencia=referencia
    )
    
    if combined_data is None:
        return jsonify({'error': 'Error al obtener datos del vendedor'}), 500

    total_pages = (total_count + limit - 1) // limit

    return jsonify({
        'orders': combined_data,
        'totalPages': total_pages,
        'currentPage': page,
        'totalItems': total_count
    })

@main.route('/logout')
def logout():
    session.clear()  # Limpiar toda la sesión
    flash('Sesión cerrada correctamente' , 'info')
    return redirect(url_for('main.login'))

# Lista de notificaciones (en producción, esto debería estar en una base de datos)
# notifications_db = [
#     {
#         'id': '1',
#         'message': 'Bienvenido al nuevo sistema de seguimiento de pedidos',
#         'author': 'Sistema',
#         'timestamp': '2025-05-01T12:00:00',
#         'read_by': [],  # Lista de usuarios que han leído esta notificación
#         'for_user': None  # None significa para todos los usuarios
#     }
# ]

# Verificar si un usuario es administrador
def is_admin(username):
    # Lista de usuarios administradores que pueden publicar notificaciones
    admin_users = ['Practicante TIC', 'Alejandro Moreno Jimenez']
    return username in admin_users

@main.route('/api/notifications', methods=['GET'])
def get_notifications():
    if 'user_info' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    user_id = session['user_info']['displayName']
    
    # Verificar si el usuario es administrador
    if is_admin(user_id):
        # Obtener todas las notificaciones sin filtrar
        notifications = NotificationDB.get_all_notifications()
    else:
        # Filtrar notificaciones para este usuario (o para todos)
        notifications = NotificationDB.get_all_notifications()
        notifications = [
            n for n in notifications 
            if n['for_user'] is None or n['for_user'] == user_id
        ]
    
    return jsonify({'notifications': notifications})
    
@main.route('/api/notifications', methods=['POST'])
def create_notification():
    if 'user_info' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    user_id = session['user_info']['displayName']
    
    # Verificar si el usuario es administrador
    if not is_admin(user_id):
        return jsonify({'error': 'No tienes permisos para crear notificaciones'}), 403
    
    # Obtener datos de la solicitud
    data = request.json
    if not data or 'message' not in data:
        return jsonify({'error': 'Mensaje requerido'}), 400
    
    # Crear nueva notificación en la base de datos
    new_notification = NotificationDB.create_notification(
        message=data['message'],
        author=user_id,
        for_user=data.get('for_user')
    )
    
    return jsonify({
        'success': True,
        'notification': new_notification
    }), 201

@main.route('/api/notifications/<notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    if 'user_info' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    user_id = session['user_info']['displayName']
    
    # Marcar notificación como leída en la base de datos
    readers_count = NotificationDB.mark_notification_read(notification_id, user_id)
    
    return jsonify({'success': True, 'readers_count': readers_count})

@main.route('/api/notifications/read-all', methods=['POST'])
def mark_all_read():
    if 'user_info' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    user_id = session['user_info']['displayName']
    
    # Marcar todas las notificaciones como leídas
    marked_count = NotificationDB.mark_all_read(user_id)
    
    return jsonify({'success': True, 'marked_count': marked_count})

@main.route('/admin/notifications')
def admin_notifications():
    if 'user_info' not in session:
        flash('Debe iniciar sesión primero', 'warning')
        return redirect(url_for('main.login'))
    
    user_id = session['user_info']['displayName']
    
    # Verificar si el usuario es administrador
    if not is_admin(user_id):
        flash('No tienes permisos para acceder a esta página', 'danger')
        return redirect(url_for('main.dashboard'))
    
    return render_template('admin_notifications.html', displayName=user_id)

@main.route('/api/notifications/<notification_id>', methods=['DELETE'])
def delete_notification(notification_id):
    if 'user_info' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    user_id = session['user_info']['displayName']
    
    # Verificar si el usuario es administrador
    if not is_admin(user_id):
        return jsonify({'error': 'No tienes permisos para eliminar notificaciones'}), 403
    
    # Eliminar la notificación
    success = NotificationDB.delete_notification(notification_id)
    
    if not success:
        return jsonify({'error': 'Notificación no encontrada'}), 404
    
    return jsonify({'success': True})
    