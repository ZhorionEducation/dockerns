document.addEventListener('DOMContentLoaded', function() {
    // Referencias a elementos DOM
    const notificationIcon = document.getElementById('notificationIcon');
    const notificationDropdown = document.getElementById('notificationDropdown');
    const notificationList = document.getElementById('notificationList');
    const notificationCount = document.getElementById('notificationCount');
    const markAllReadBtn = document.getElementById('markAllRead');
    
    // Obtener el nombre de usuario del DOM
    const userInfoElement = document.querySelector('.user-info span');
    const user_id = userInfoElement ? userInfoElement.textContent.trim() : 'Usuario';
    
    console.log("Usuario actual:", user_id); // Para depuración
    
    // Estado de las notificaciones
    let notifications = [];
    
    // Evento para mostrar/ocultar el dropdown de notificaciones
    notificationIcon.addEventListener('click', function() {
        notificationDropdown.classList.toggle('show');
    });
    
    // Cerrar dropdown si se hace click fuera
    document.addEventListener('click', function(event) {
        if (!notificationIcon.contains(event.target) && !notificationDropdown.contains(event.target)) {
            notificationDropdown.classList.remove('show');
        }
    });
    
    // Marcar todas como leídas
    markAllReadBtn.addEventListener('click', function() {
        markAllNotificationsAsRead();
    });
    
    // Fetch para obtener las notificaciones
    function fetchNotifications() {
        fetch('/api/notifications')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Error al obtener notificaciones');
                }
                return response.json();
            })
            .then(data => {
                notifications = data.notifications;
                updateNotificationUI();
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }
    
    // Actualizar la interfaz con las notificaciones
    function updateNotificationUI() {
        // Limpiar la lista
        notificationList.innerHTML = '';
        
        // Contar notificaciones no leídas
        const unreadCount = notifications.filter(notification => 
            !notification.read_by || !notification.read_by.includes(user_id)
        ).length;
        
        console.log("Notificaciones totales:", notifications.length);
        console.log("Notificaciones no leídas:", unreadCount);
        
        // Actualizar contador visual
        if (unreadCount > 0) {
            notificationCount.textContent = unreadCount;
            notificationCount.classList.add('show');
        } else {
            notificationCount.classList.remove('show');
        }
        
        // Si no hay notificaciones, mostrar mensaje
        if (notifications.length === 0) {
            notificationList.innerHTML = `
                <div class="empty-notification">
                    <p>No tienes notificaciones</p>
                </div>
            `;
            return;
        }
        
        // Renderizar cada notificación
        notifications.forEach(notification => {
            const notificationItem = document.createElement('div');
            // Determinar si el usuario actual ha leído esta notificación
            const isRead = notification.read_by && notification.read_by.includes(user_id);
            notificationItem.className = `notification-item${isRead ? '' : ' unread'}`;
            notificationItem.dataset.id = notification.id;
            
            // Calcular tiempo relativo
            const timeAgo = getTimeAgo(new Date(notification.timestamp));
            
            // Obtener conteo de lectores
            const readersCount = notification.read_by ? notification.read_by.length : 0;
            
            notificationItem.innerHTML = `
                <div class="notification-content">
                    <p class="notification-message">${notification.message}</p>
                </div>
                <div class="notification-meta">
                    <span class="notification-author">${notification.author}</span>
                    <span class="notification-time">${timeAgo}</span>
                </div>
                
            `;
            
            // Evento para marcar como leída al hacer click
            notificationItem.addEventListener('click', function() {
                markNotificationAsRead(notification.id);
            });
            
            notificationList.appendChild(notificationItem);
        });
    }
    
    // Marcar una notificación como leída
    function markNotificationAsRead(id) {
        fetch(`/api/notifications/${id}/read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Error al marcar como leída');
            }
            return response.json();
        })
        .then(data => {
            // Actualizar el estado localmente
            fetchNotifications(); // Recargar para tener datos actualizados
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
    
    // Marcar todas las notificaciones como leídas
    function markAllNotificationsAsRead() {
        fetch('/api/notifications/read-all', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Error al marcar todas como leídas');
            }
            return response.json();
        })
        .then(data => {
            fetchNotifications(); // Recargar para tener datos actualizados
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
    
    // Función para obtener tiempo relativo
    function getTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        
        let interval = Math.floor(seconds / 31536000);
        if (interval > 1) return interval + ' años atrás';
        if (interval === 1) return 'hace 1 año';
        
        interval = Math.floor(seconds / 2592000);
        if (interval > 1) return interval + ' meses atrás';
        if (interval === 1) return 'hace 1 mes';
        
        interval = Math.floor(seconds / 86400);
        if (interval > 1) return interval + ' días atrás';
        if (interval === 1) return 'ayer';
        
        interval = Math.floor(seconds / 3600);
        if (interval > 1) return interval + ' horas atrás';
        if (interval === 1) return 'hace 1 hora';
        
        interval = Math.floor(seconds / 60);
        if (interval > 1) return interval + ' minutos atrás';
        if (interval === 1) return 'hace 1 minuto';
        
        return 'hace un momento';
    }
    
    // Polling para verificar nuevas notificaciones (cada 30 segundos)
    function startNotificationPolling() {
        fetchNotifications(); // Primera carga
        
        // Verificar notificaciones periódicamente
        setInterval(fetchNotifications, 30000);
    }
    
    // Iniciar el sistema de notificaciones
    startNotificationPolling();
});