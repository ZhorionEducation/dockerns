def get_unified_orders(start_date, end_date, guia=None, cliente=None, transportadora=None, pedido=None, vendedor=None, limit=None, offset=None):
    where_clauses = [
        f"FORMAT(t430.f430_fecha_ts_creacion, 'yyyyMM') BETWEEN '{start_date}' AND '{end_date}'",
        "t430.f430_id_tipo_docto IN ('PVN', 'PNF', 'PVI')"
    ]
    
    # Agregar filtros adicionales si están presentes
    if guia:
        where_clauses.append(f"upper(G.Num_Guia) LIKE '%{guia.upper()}%'")
    if cliente:
        where_clauses.append(f"p.NOMBRECLIENTE LIKE '%{cliente}%'")
    if transportadora:
        where_clauses.append(f"UPPER(G.Transportador) LIKE '%{transportadora.upper()}%'")
    if pedido:
        pedido_parts = pedido.split('-')
        if len(pedido_parts) > 1:
            tipo_docto = pedido_parts[0]
            num_docto = pedido_parts[1]
            where_clauses.append(f"(t430.f430_id_tipo_docto = '{tipo_docto}' AND CAST(t430.f430_consec_docto AS NVARCHAR) LIKE '%{num_docto}%')")
        else:
            where_clauses.append(f"CAST(t430.f430_consec_docto AS NVARCHAR) LIKE '%{pedido}%'")
    if vendedor:
        where_clauses.append(f"p.NombreVendedor LIKE '%{vendedor}%'")

    where_clause = " AND ".join(where_clauses)

    query = f"""
    SELECT DISTINCT
        t430.f430_id_tipo_docto "Tipo de documento",
        RTRIM(t430.f430_id_tipo_docto) + '-' + CONVERT(varchar(50), FORMAT(CONVERT(bigint, t430.f430_consec_docto), '00000000')) "Numero de pedido",
        RTRIM(t430.f430_id_tipo_docto) + '-' + CONVERT(varchar(50), t430.f430_consec_docto) Keypedido,
        sum(s.cantidadAduanada) Cantidad,
        upper(G.Num_Guia) Guia,
        UPPER(G.Transportador) Transportador,
        t430.f430_fecha_ts_creacion "Fecha Registro de pedido",
        t430.f430_fecha_ts_aprobacion "Fecha Preparacion de pedido",
        t430.f430_fecha_ts_aprob_cartera "Fecha aprobacion Cartera",
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
        upper(G.Num_Guia),
        UPPER(G.Transportador),
        t430.f430_fecha_ts_creacion,
        t430.f430_fecha_ts_aprobacion,
        t430.f430_fecha_ts_aprob_cartera,
        fechainicia,
        [Fecha_Despacho],
        t430.f430_ind_estado,
        p.NOMBRECLIENTE,
        p.NombreVendedor,
        Factura
    ORDER BY t430.f430_fecha_ts_creacion DESC
    """
    
    if limit is not None and offset is not None:
        query += f"\nOFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"
    
    return query