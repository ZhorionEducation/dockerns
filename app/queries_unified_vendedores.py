def get_unified_orders_vendedores(vendedor, cliente=None, pedido=None, factura=None, referencia=None):
    """
    Query unificado para la vista de vendedores, que muestra solo los pedidos del vendedor logueado
    y soporta los filtros específicos de la vista de vendedores.
    
    Args:
        vendedor: Nombre del vendedor (obligatorio)
        cliente: Filtro por nombre de cliente (opcional)
        pedido: Filtro por número de pedido (opcional)
        factura: Filtro por número de factura (opcional)
        referencia: Filtro por referencia del producto (opcional)
    """
    from datetime import datetime, timedelta
    today = datetime.today()
    two_months_ago = today - timedelta(days=60)  # Aproximadamente 2 meses
    date_filter = two_months_ago.strftime('%Y%m')
    
    where_clauses = [
        "t430.f430_id_tipo_docto IN ('PVN', 'PNF', 'PVI')",
        f"p.NombreVendedor LIKE '%{vendedor}%'",
        f"FORMAT(t430.f430_fecha_ts_creacion, 'yyyyMM') >= '{date_filter}'"  # Filtro para mostrar solo pedidos de los últimos 2 meses
    ]
    
    # Agregar filtros adicionales si están presentes
    if cliente:
        where_clauses.append(f"p.NOMBRECLIENTE LIKE '%{cliente}%'")
    if pedido:
        pedido_parts = pedido.split('-')
        if len(pedido_parts) > 1:
            tipo_docto = pedido_parts[0]
            num_docto = pedido_parts[1]
            where_clauses.append(f"(t430.f430_id_tipo_docto = '{tipo_docto}' AND CAST(t430.f430_consec_docto AS NVARCHAR) LIKE '%{num_docto}%')")
        else:
            where_clauses.append(f"CAST(t430.f430_consec_docto AS NVARCHAR) LIKE '%{pedido}%'")
    if factura:
        where_clauses.append(f"Factura LIKE '%{factura}%'")
    if referencia:
        where_clauses.append(f"a.referencia LIKE '%{referencia}%'")

    where_clause = " AND ".join(where_clauses)

    query = f"""
    SELECT DISTINCT
        t430.f430_id_tipo_docto "Tipo de documento",
        RTRIM(t430.f430_id_tipo_docto) + '-' + CONVERT(varchar(50), FORMAT(CONVERT(bigint, t430.f430_consec_docto), '00000000')) "Numero de pedido",
        RTRIM(t430.f430_id_tipo_docto) + '-' + CONVERT(varchar(50), t430.f430_consec_docto) Keypedido,
        sum(s.cantidadAduanada) Cantidad,
        s.idprepack "Numero de picking",
        a.referencia Referencia,
        a.descripcion "Descripcion",
        EanContenido "Extencion del item",
        upper(G.Num_Guia) Guia,
        UPPER(G.Transportador) Transportador,
        t430.f430_fecha_ts_creacion "Fecha Registro de pedido",
        t430.f430_fecha_ts_aprobacion "Fecha Preparacion de pedido",
        fechainicia "Fecha picking",
        max(s.fechaRegistro) "Fecha de alistamiento",
        [Fecha_Despacho] "Fecha_Despacho",
        CASE 
            WHEN t430.f430_ind_estado = 0 THEN 'En elaboración'
            WHEN t430.f430_ind_estado = 1 THEN 'Retenido'
            WHEN t430.f430_ind_estado = 2 THEN 'Aprobado'
            WHEN t430.f430_ind_estado = 3 THEN 'Comprometido'
            WHEN t430.f430_ind_estado = 4 THEN 'Cumplido'
            WHEN t430.f430_ind_estado = 9 THEN 'Anulado'
            WHEN t430.f430_ind_estado <> 9 AND t430.f430_ind_estado <> 4 THEN 'Pendiente'
            WHEN t430.f430_ind_estado <> 9 THEN 'No Anulado'
        END "Estado del documento",
        p.NOMBRECLIENTE "Razon social cliente",
        p.NombreVendedor "Razon social vendedor",
        Factura "Numero de factura",
        '' as "LINEA",
        '' as "GRUPO",  
        '' as "SUBGRUPO",
        CASE 
            WHEN UPPER(G.Transportador)='CONALCA'             THEN 'CONALCA'
            WHEN UPPER(G.Transportador)='CONALCA BOGOTA'      THEN 'Urbano Bogota'
            WHEN UPPER(G.Transportador)='IMD & CIA SAS'       THEN 'Urbano Medellin'
            WHEN UPPER(G.Transportador)='IMD Y CIA SAS'       THEN 'Urbano Medellin'
            WHEN UPPER(G.Transportador)='MEDELLIN GUSTAVO'    THEN 'Urbano Medellin'
            WHEN UPPER(G.Transportador)='S&S ADMINISTRATION'  THEN 'S&S ADMINISTRATION'
            WHEN UPPER(G.Transportador)='TACMO SAS'           THEN 'Nacional Guarne-Bogota'
            WHEN UPPER(G.Transportador)='TCC'                 THEN 'Paqueteria excepto Bogota-Medellin'
            WHEN UPPER(G.Transportador)='TRANSPORTADORA'      THEN 'TRANSPORTADORA' 
        END RUTA
    FROM [UNOEE].[dbo].[t430_cm_pv_docto] t430
    LEFT JOIN [SGV_BKGENERICABASE1].dbo.v_wms_EPK E ON t430.f430_id_tipo_docto = E.tipoDocto AND t430.f430_consec_docto = E.doctoERP
    LEFT JOIN [SGV_BKGENERICABASE1].dbo.v_wms_clientes C ON E.item = C.item
    LEFT JOIN SGV_BKGENERICABASE1.dbo.t_materiales_por_orden MO ON CAST(MO.eaninsumo AS NVARCHAR) = CAST(E.numPedido AS NVARCHAR) AND MO.color = E.tipoDocto
    LEFT JOIN SGV_BKGENERICABASE1.dbo.T_encabezado_Prepack f ON f.consmov = MO.orden
    LEFT JOIN SGV_BKGENERICABASE1.dbo.T_SSCCxCaja s ON s.idprepack = f.Picking
    LEFT JOIN SGV_BKGENERICABASE1.dbo.t_Guias_Generadas G ON f.IdMovimiento = G.PrepackingID
    LEFT JOIN SGV_BKGENERICABASE1.dbo.V_WMS_Pedidos P ON CAST(P.pedido AS NVARCHAR) = CAST(f.npedid AS NVARCHAR)
    LEFT JOIN SGV_BKGENERICABASE1.dbo.V_WMS_Articulos A ON CAST(s.EanContenido AS NVARCHAR) = CAST(A.productoEAN AS NVARCHAR)
    WHERE {where_clause}
    GROUP BY 
        t430.f430_id_tipo_docto,
        t430.f430_consec_docto,
        s.idprepack,
        a.referencia,
        a.descripcion,
        EanContenido,
        upper(G.Num_Guia),
        UPPER(G.Transportador),
        t430.f430_fecha_ts_creacion,
        t430.f430_fecha_ts_aprobacion,
        fechainicia,
        [Fecha_Despacho],
        t430.f430_ind_estado,
        p.NOMBRECLIENTE,
        p.NombreVendedor,
        Factura
    ORDER BY t430.f430_fecha_ts_creacion DESC
    """
    
    return query