let orders = [];
const itemsPerPage = 10;
let currentPage = 1;
let totalPages = 1;
let filteredOrders = null;

document.getElementById('dateFilterForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    currentPage = 1; // Reset to first page on new filter
    await fetchOrders();
});

async function fetchOrders() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const guia = document.getElementById('guia').value;
    const cliente = document.getElementById('cliente').value;
    const transportadora = document.getElementById('transportadora').value;
    const pedido = document.getElementById('pedido').value;
    const vendedor = document.getElementById('vendedor').value;

    if (!startDate || !endDate) return;

    const startDateFilter = startDate.split('-').join('');
    const endDateFilter = endDate.split('-').join('');

    document.getElementById('loadingPopup').style.display = 'flex';

    try {
        // Aumentar el límite a un número mucho mayor para asegurar que se traigan todos los pedidos
        // Usar 100000 como un valor muy alto que probablemente nunca se alcanzará
        const response = await fetch(
            `/api/orders?start_date=${startDateFilter}&end_date=${endDateFilter}&guia=${guia}&cliente=${cliente}&transportadora=${transportadora}&pedido=${pedido}&vendedor=${vendedor}&page=1&limit=800000`
        );
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error al cargar los datos');
        }

        const data = await response.json();
        
        // Guardar todos los pedidos sin procesar
        const allOrders = data.orders;
        
        console.log(`Total de pedidos cargados: ${allOrders.length}`); // Log para verificar cuántos pedidos se están cargando
        
        // Definir el orden de prioridad de los estados
        const estadoPrioridad = {
            'en elaboración': 1,
            'aprobado': 2,
            'comprometido': 3,
            'retenido': 4,
            'cumplido': 5,
            'anulado': 6
        };
        
        // Ordenar todos los pedidos por la prioridad de estados
        allOrders.sort((a, b) => {
            const estadoA = (a.estado_documento || '').toLowerCase();
            const estadoB = (b.estado_documento || '').toLowerCase();
            
            // Asignar valores de prioridad (si no está en la lista, darle un valor alto)
            const prioridadA = estadoPrioridad[estadoA] || 999;
            const prioridadB = estadoPrioridad[estadoB] || 999;
            
            return prioridadA - prioridadB;
        });
        
        // Actualizar la paginación con los pedidos ya ordenados
        filteredOrders = allOrders;
        totalPages = Math.ceil(filteredOrders.length / itemsPerPage);
        currentPage = 1; // Reiniciar a la primera página
        
        // Actualizar orders con los elementos de la página actual
        paginateFilteredData(currentPage);

        document.querySelector('.table-container').style.display = 'block';
        document.getElementById('initialMessage').style.display = 'none';

        // No necesitas ordenar los pedidos en renderTable() ya que ya están ordenados
        renderTable();
        
        // Actualizar estado de los botones de paginación
        document.getElementById('prevPage').disabled = currentPage <= 1;
        document.getElementById('nextPage').disabled = currentPage >= totalPages;
        
        // Mostrar el número total de pedidos en la información de paginación
        document.getElementById('pageInfo').textContent = `Página ${currentPage} de ${totalPages} (Total: ${filteredOrders.length} pedidos)`;
        
    } catch (error) {
        console.error('Error:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: error.message || 'Error al cargar los datos',
            confirmButtonColor: '#00a3b4'
        });
    } finally {
        document.getElementById('loadingPopup').style.display = 'none';
    }
}

function formatearFecha(fechaStr) {
    if (!fechaStr || fechaStr === 'No disponible') return 'No disponible';
    
    try {
        // Parse the input date
        const fecha = new Date(fechaStr);
        if (isNaN(fecha.getTime())) return 'No disponible';
        
        // Add 5 hours to adjust for timezone
        fecha.setHours(fecha.getHours() + 5);
        
        return fecha.toLocaleString('es-CO', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            timeZone: 'America/Bogota'
        });
    } catch (e) {
        return 'No disponible';
    }
}


function showEstadoFilter() {
    const filterDiv = document.getElementById('estadoFilter');
    const filterButton = document.querySelector('.filter-button i');
    const isVisible = filterDiv.classList.contains('show');
    
    if (isVisible) {
        filterDiv.classList.remove('show');
        filterButton.style.transform = 'rotate(0deg)';
    } else {
        filterDiv.classList.add('show');
        filterButton.style.transform = 'rotate(180deg)';
    }
}


document.addEventListener('click', function(event) {
    const filterDiv = document.getElementById('estadoFilter');
    const filterButton = document.querySelector('.filter-button');
    
    if (!filterButton.contains(event.target) && !filterDiv.contains(event.target)) {
        filterDiv.classList.remove('show');
        document.querySelector('.filter-button i').style.transform = 'rotate(0deg)';
    }
});

async function sortTableByEstado(estado) {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const guia = document.getElementById('guia').value;
    const cliente = document.getElementById('cliente').value;
    const transportadora = document.getElementById('transportadora').value;
    const pedido = document.getElementById('pedido').value;
    const vendedor = document.getElementById('vendedor').value;

    if (!startDate || !endDate) return;

    const startDateFilter = startDate.split('-').join('');
    const endDateFilter = endDate.split('-').join('');

    document.getElementById('loadingPopup').style.display = 'flex';

    try {
        const response = await fetch(
            `/api/orders?start_date=${startDateFilter}&end_date=${endDateFilter}&guia=${guia}&cliente=${cliente}&transportadora=${transportadora}&pedido=${pedido}&vendedor=${vendedor}&page=1&limit=800000`
        );
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error al cargar los datos');
        }

        const data = await response.json();
        const allOrders = data.orders;

        // Filtrar por estado y guardar en la variable global filteredOrders
        filteredOrders = allOrders.filter(order => {
            const orderEstado = order.estado_documento ? order.estado_documento.toLowerCase() : '';
            return orderEstado === estado.toLowerCase();
        });

        if (filteredOrders.length === 0) {
            alert('No hay pedidos con el estado: ' + estado);
            return;
        }

        // Calcular la paginación para los datos filtrados
        currentPage = 1;
        totalPages = Math.ceil(filteredOrders.length / itemsPerPage);

        // Mostrar solo los items de la página actual
        const startIndex = (currentPage - 1) * itemsPerPage;
        const endIndex = startIndex + itemsPerPage;
        orders = filteredOrders.slice(startIndex, endIndex);
        
        // Renderizar tabla con los datos paginados
        renderTable();
        
        // Actualizar información de paginación
        document.getElementById('pageInfo').textContent = `Página ${currentPage} de ${totalPages} (${filteredOrders.length} pedidos con estado ${estado})`;
        
        // Actualizar estado de botones de paginación
        document.getElementById('prevPage').style.display = 'block';
        document.getElementById('nextPage').style.display = 'block';
        document.getElementById('prevPage').disabled = currentPage <= 1;
        document.getElementById('nextPage').disabled = currentPage >= totalPages;

    } catch (error) {
        console.error('Error:', error);
        alert(error.message);
    } finally {
        document.getElementById('loadingPopup').style.display = 'none';
        showEstadoFilter();
    }
}

function paginateFilteredData(page) {
    const startIndex = (page - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    orders = filteredOrders.slice(startIndex, endIndex);
    currentPage = page;
    renderTable();
    
    // Actualizar estado de botones
    document.getElementById('prevPage').disabled = currentPage <= 1;
    document.getElementById('nextPage').disabled = currentPage >= totalPages;
    document.getElementById('pageInfo').textContent = `Página ${currentPage} de ${totalPages}`;
}

function renderTable() {
    const tableBody = document.getElementById('ordersTableBody');
    tableBody.innerHTML = '';

    orders.forEach(order => {
        const row = document.createElement('tr');
        
        // Determinar la clase del estado
        let estadoClass = 'estado-default-row';
        const estado = (order.estado_documento || '').toLowerCase();
        if (estado.includes('facturado') || estado.includes('despachado')) {
            estadoClass = 'estado-ok-row';
        
        } else if (estado.includes('anulado')) {
            estadoClass = 'estado-anulado-row';
        } else if (estado.includes('aprobado')) {
            estadoClass = 'estado-aprobado-row';
        } else if (estado.includes('comprometido')) {
            estadoClass = 'estado-comprometido-row';
        } else if (estado.includes('cumplido')) {
            estadoClass = 'estado-cumplido-row';
        } else if (estado.includes('en elaboración')) {
            estadoClass = 'estado-elaboracion-row';
        } else if (estado.includes('retenido')) {
            estadoClass = 'estado-retenido-row';
        } 

        // Aplicar la clase al fondo de la fila
        row.className = estadoClass;

        // Crear la estructura de la fila
        row.innerHTML = `
            <td>
                <div class="pedido-circle ${estadoClass}" onclick='showTraceModal(${JSON.stringify(order).replace(/'/g, "&#39;")})'>
                    ${order.numero_pedido || 'No disponible'}
                </div>
            </td>
            <td>${order.estado_documento || 'No disponible'}</td>
            <td>${formatearFecha(order.fecha_aprobacion_cartera)}</td>
            <td>${order.cliente || 'No disponible'}</td>
            <td>${order.numero_factura || 'No disponible'}</td>
            <td>${order.razon_social_vendedor || 'No disponible'}</td>
        `;

        tableBody.appendChild(row);
    });

    document.getElementById('pageInfo').textContent = `Página ${currentPage} de ${totalPages}`;
}

document.getElementById('prevPage').addEventListener('click', async () => {
    if (currentPage > 1) {
        currentPage--;
        if (filteredOrders) {
            paginateFilteredData(currentPage);
        } else {
            await fetchOrders();
        }
    }
});

document.getElementById('nextPage').addEventListener('click', async () => {
    if (currentPage < totalPages) {
        currentPage++;
        if (filteredOrders) {
            paginateFilteredData(currentPage);
        } else {
            await fetchOrders();
        }
    }
});


//LIMITE CALENDARIO
document.addEventListener('DOMContentLoaded', function() {
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');

    // Get the current date
    const currentDate = new Date();
    const currentYear = currentDate.getFullYear();
    const currentMonth = String(currentDate.getMonth() + 1).padStart(2, '0'); // Month is 0-indexed
    const currentDateFormatted = `${currentYear}-${currentMonth}`;

    // Calculate the date one year prior
    const oneYearAgo = new Date();
    oneYearAgo.setFullYear(currentYear - 1);
    const oneYearAgoYear = oneYearAgo.getFullYear();
    const oneYearAgoMonth = String(oneYearAgo.getMonth() + 1).padStart(2, '0');
    const oneYearAgoFormatted = `${oneYearAgoYear}-${oneYearAgoMonth}`;

    // Set the max and min attributes for the date inputs
    startDateInput.max = currentDateFormatted;
    endDateInput.max = currentDateFormatted;
    startDateInput.min = oneYearAgoFormatted;
    endDateInput.min = oneYearAgoFormatted;
});



// Agregar después del código existente
function showTraceModal(order) {
    const modal = document.getElementById('traceModal');
    const timeline = document.getElementById('pedidoTimeline');
    const modalPedidoNumero = document.getElementById('modalPedidoNumero');
    
    modalPedidoNumero.textContent = order.numero_pedido;
    timeline.innerHTML = '';
    
    // Actualizar información de envío en el modal
    document.getElementById('modalGuia').textContent = order.guia || 'No disponible';
    
    // Crear el contenido de transportador con enlaces según sea necesario
    const transportadorOriginal = order.transportadora || 'Sin transportador';
    let transportadorContent = transportadorOriginal;
    if (transportadorOriginal === 'TCC') {
        transportadorContent = `<a href="https://www.tcc.com.co" target="_blank">${transportadorOriginal}</a>`;
    } else if (transportadorOriginal === 'TACMO SAS') {
        transportadorContent = `<a href="https://tacmosas.com/" target="_blank">${transportadorOriginal}</a>`;
    } else if (transportadorOriginal === 'IMD & CIA SAS' || transportadorOriginal === 'IMD Y CIA SAS') {
        transportadorContent = `<a href="https://www.imd.com.co" target="_blank">${transportadorOriginal}</a>`;
    }
    
    document.getElementById('modalTransportador').innerHTML = transportadorContent;
    document.getElementById('modalRuta').textContent = order.ruta || transportadorOriginal || 'Sin transportador';

    const estados = [
        {
            titulo: 'Registro del Pedido',
            fecha: order.fecha_registro_pedido,
            icono: 'fa-solid fa-file-signature',
            descripcion: 'Pedido registrado en el sistema',
            mensajePendiente: 'Pedido no registrado'
        },
        {
            titulo: 'Preparación',
            fecha: order.fecha_preparacion,
            icono: 'fas fa-box-open',
            descripcion: 'Pedido en preparación',
            mensajePendiente: 'Pendiente de preparación'
        },
        {
            titulo: 'Picking',
            fecha: order.fecha_picking,
            icono: 'fas fa-people-carry',
            descripcion: 'Proceso de picking completado',
            mensajePendiente: 'Pendiente de picking'
        },
        {
            titulo: 'Alistamiento',
            fecha: order.fecha_de_alistamiento,
            icono: 'fas fa-dolly',
            descripcion: 'Pedido alistado para despacho',
            mensajePendiente: 'Pendiente de alistamiento'
        },
        {
            titulo: 'Despacho',
            fecha: order.fecha_despacho,
            icono: 'fas fa-shipping-fast',
            descripcion: 'Pedido despachado al cliente',
            mensajePendiente: 'No se ha despachado'
        }
    ];

    // Encontrar el estado actual
    let estadoActual = 0;
    for (let i = estados.length - 1; i >= 0; i--) {
        if (estados[i].fecha && estados[i].fecha !== 'No disponible') {
            estadoActual = i;
            break;
        }
    }

    // Filtrar y crear elementos del timeline solo para estados con fecha
    estados.forEach((estado, index) => {
        let tieneFecha = false;
        let fecha = estado.mensajePendiente;
    
        if (estado.fecha && estado.fecha !== 'No disponible') {
            try {
                const fechaObj = new Date(estado.fecha);
                if (!isNaN(fechaObj.getTime())) {
                    // Add 5 hours to the date for timezone adjustment
                    fechaObj.setHours(fechaObj.getHours() + 5);
                    
                    tieneFecha = true;
                    fecha = fechaObj.toLocaleString('es-CO', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    });
                }
            } catch (e) {
                // Si hay error al parsear la fecha, usamos el mensajePendiente
                fecha = estado.mensajePendiente;
            }
        }
        
        const timelineItem = document.createElement('div');
        timelineItem.className = 'timeline-item';
        
        const isActive = index <= estadoActual;
        const estadoColor = tieneFecha ? (isActive ? '#00a3b4' : '#e0e0e0') : '#ff6b6b';
        
        
        timelineItem.innerHTML = `
            <div class="timeline-line"></div>
            <div class="timeline-icon ${tieneFecha ? (isActive ? 'active' : '') : 'pending'}" 
                 style="background-color: ${estadoColor}">
                <i class="${estado.icono}"></i>
            </div>
            <div class="timeline-content ${tieneFecha ? (isActive ? 'active' : '') : 'pending'}" 
                 style="border-left: 4px solid ${estadoColor}; ${!tieneFecha ? 'background-color: #ffe5e5;' : ''}">
                <div class="timeline-title">
                    <i class="${estado.icono}" style="margin-right: 8px; color: ${estadoColor}"></i>
                    ${estado.titulo}
                </div>
                <div class="timeline-date" style="color: ${tieneFecha ? (isActive ? '#00a3b4' : '#666') : '#ff6b6b'}">
                    ${fecha}
                </div>
                <div class="timeline-description">
                    ${tieneFecha ? estado.descripcion : 'Estado no registrado'}
                </div>
            </div>
        `;

        timeline.appendChild(timelineItem);
    });

    modal.style.display = 'block';

    // Cerrar modal
    const closeBtn = document.querySelector('.close-modal');
    closeBtn.onclick = function() {
        modal.style.display = 'none';
    }

    // Cerrar modal al hacer clic fuera
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    }
}

function showInfoMessage(icon) {
    const message = icon.nextElementSibling;
    const allMessages = document.querySelectorAll('.info-message');
    
    // Hide all other messages first
    allMessages.forEach(msg => {
        if (msg !== message) {
            msg.classList.remove('show');
        }
    });
    
    // Toggle current message
    message.classList.toggle('show');
    
    // Close message when clicking outside
    document.addEventListener('click', function closeMessage(e) {
        if (!icon.contains(e.target) && !message.contains(e.target)) {
            message.classList.remove('show');
            document.removeEventListener('click', closeMessage);
        }
    });
}