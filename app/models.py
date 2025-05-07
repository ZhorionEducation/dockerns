from typing import Dict, Any

class OrderInfo:
    def __init__(self, guia: str, transportadora: str, cliente: str, 
                numero_pedido: str, numero_factura: str,
                referencia: str, linea: str, grupo: str, 
                subgrupo: str, cantidad: str,
                fecha_despacho: str = '', fecha_picking: str = '', 
                razon_social_vendedor: str = '', fecha_preparacion: str = '', estado_documento: str = '',
                ruta: str = '', fecha_de_alistamiento: str = '', fecha_aprobacion_cartera: str = ''):  # Agregar nuevos parámetros
        self.guia = guia
        self.transportadora = transportadora
        self.cliente = cliente
        self.numero_pedido = numero_pedido
        self.numero_factura = numero_factura
        self.referencia = referencia
        self.linea = linea
        self.grupo = grupo
        self.subgrupo = subgrupo
        self.cantidad = cantidad
        self.fecha_despacho = fecha_despacho
        self.fecha_picking = fecha_picking
        self.razon_social_vendedor = razon_social_vendedor
        self.fecha_preparacion = fecha_preparacion
        self.estado_documento = estado_documento
        self.ruta = ruta
        self.fecha_de_alistamiento = fecha_de_alistamiento  # Nueva propiedad
        self.fecha_aprobacion_cartera = fecha_aprobacion_cartera  # Nueva propiedad

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'OrderInfo':
        info = OrderInfo(
            guia=data.get('Guia', ''),
            transportadora=data.get('Transportador', ''),
            cliente=data.get('Razon social cliente', ''),
            numero_pedido=data.get('Numero de pedido', ''),
            numero_factura=data.get('Numero de factura', ''),
            referencia=data.get('Referencia', ''),
            linea=data.get('LINEA', ''),
            grupo=data.get('GRUPO', ''),
            subgrupo=data.get('SUBGRUPO', ''),
            cantidad=data.get('Cantidad', ''),
            fecha_despacho=data.get('Fecha_Despacho', ''),
            fecha_picking=data.get('Fecha_Picking', ''),
            razon_social_vendedor=data.get('Razon social vendedor', ''),
            fecha_preparacion=data.get('Fecha Preparacion de pedido', ''),
            estado_documento=data.get('Estado del documento', ''),
            ruta=data.get('RUTA', ''),
            fecha_de_alistamiento=data.get('Fecha de alistamiento', ''),  # Obtener del diccionario
            fecha_aprobacion_cartera=data.get('Fecha aprobacion Cartera', '')  # Obtener del diccionario
        )
        # Agregar fecha_registro_pedido después de la creación
        info.fecha_registro_pedido = data.get('Fecha Registro de pedido', '')
        return info