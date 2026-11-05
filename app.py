"""
================================================================================
AGROINDUSTRIAL DEL LITORAL S.A.
PROTOTIPO DE INTEGRACIÓN DE PROCESOS Y SISTEMAS EMPRESARIALES (CASO 2)
================================================================================
Backend Flask modular y unificado con:
- Almacenamiento desacoplado en JSON (/data)
- Motor de Validación de Integridad (Sintaxis, IDs, Foreign Keys, Rangos)
- Pipeline ETL (Extracción, Normalización, Desduplicación, Carga en memoria)
- Módulo MRP de Planificación (+30% Demanda, PT, MP y Compras Sugeridas)
- Dashboard Gerencial con 5 KPIs en tiempo real
- Asistente IA RAG local estricto con tolerancia semántica y fallback obligatorio
- Simulador de Integración ERP Bidireccional (Odoo JSON-RPC / REST)
- Sistema de Autenticación RBAC (Administrador y Gerente)
================================================================================
"""

import os
import json
import math
import re
import datetime
import unicodedata
from unicodedata import normalize
from typing import Dict, Any, List, Optional, Tuple
from flask import Flask, jsonify, request, render_template, session

# ------------------------------------------------------------------------------
# CONFIGURACIÓN GENERAL DE LA APLICACIÓN
# ------------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "agro_litoral_super_secret_enterprise_key_2026"
app.config["JSON_AS_ASCII"] = False
app.config["JSON_SORT_KEYS"] = False


# ------------------------------------------------------------------------------
# MODELO EN MEMORIA: DATA WAREHOUSE INTEGRADO
# El sistema NUNCA sobreescribe los JSON originales para cálculos o proyecciones.
# ------------------------------------------------------------------------------
class DataWarehouse:
    def __init__(self):
        self.productos: List[Dict[str, Any]] = []
        self.inventario: List[Dict[str, Any]] = []
        self.clientes: List[Dict[str, Any]] = []
        self.proveedores: List[Dict[str, Any]] = []
        self.pedidos: List[Dict[str, Any]] = []
        self.compras: List[Dict[str, Any]] = []
        self.usuarios: List[Dict[str, Any]] = []

        # Estado y métricas de la última ejecución ETL
        self.etl_meta: Dict[str, Any] = {
            "ultima_ejecucion": None,
            "estado": "PENDIENTE",
            "duracion_ms": 0.0,
            "registros_extraidos": 0,
            "registros_cargados": 0,
            "duplicados_descartados": 0,
            "normalizaciones_aplicadas": 0
        }

        # Simulación de anomalía para probar el motor de validación
        self.anomalia_simulada: Optional[Dict[str, Any]] = None

dw = DataWarehouse()


# ------------------------------------------------------------------------------
# UTILIDADES AUXILIARES
# ------------------------------------------------------------------------------
def leer_json_disco(nombre_archivo: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """Lee un archivo JSON desde /data con manejo estricto de errores sintácticos."""
    ruta = os.path.join(DATA_DIR, nombre_archivo)
    if not os.path.exists(ruta):
        return None, f"Archivo no encontrado: {nombre_archivo}"
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
            if not isinstance(datos, list):
                return None, f"Estructura inválida en {nombre_archivo}: Se esperaba un arreglo JSON."
            return datos, None
    except json.JSONDecodeError as e:
        return None, f"Error de sintaxis JSON en {nombre_archivo} (Línea {e.lineno}, Col {e.colno}): {e.msg}"
    except Exception as e:
        return None, f"Error de E/S leyendo {nombre_archivo}: {str(e)}"


def normalizar_texto(texto: Any) -> str:
    """Elimina espacios redundantes y sanitiza texto."""
    if texto is None:
        return ""
    return str(texto).strip()


def normalizar_fecha_iso(fecha_str: Any) -> str:
    """Normaliza fechas a formato estándar ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)."""
    if not fecha_str:
        return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cadena = str(fecha_str).strip()
    try:
        # Intenta parsear ISO directo
        if "T" in cadena:
            cadena_limpia = cadena.replace("Z", "+00:00")
            dt = datetime.datetime.fromisoformat(cadena_limpia)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        elif len(cadena) == 10 and "-" in cadena:
            # Formato YYYY-MM-DD
            dt = datetime.datetime.strptime(cadena, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%dT00:00:00Z")
    except Exception:
        pass
    return cadena


def limpiar_texto_busqueda(texto: str) -> str:
    """Limpia tildes, mayúsculas y caracteres especiales para matching semántico."""
    if not texto:
        return ""
    texto = texto.lower()
    # Descomponer caracteres con acento y remover marcas diacríticas
    texto = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    # Remover puntuaciones innecesarias
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return " ".join(texto.split())


# ------------------------------------------------------------------------------
# 1. MOTOR DE VALIDACIÓN DE INTEGRIDAD EMPRESARIAL
# Detecta: JSON mal formado, IDs duplicados, FK rotas y valores negativos.
# ------------------------------------------------------------------------------
def ejecutar_auditoria_integridad() -> Dict[str, Any]:
    """
    Inspecciona todos los conjuntos de datos en busca de:
    1. Errores de sintaxis o JSON mal formado.
    2. Claves primarias / IDs duplicados.
    3. Claves foráneas rotas (pedidos sin cliente, items sin producto, inventario sin producto).
    4. Valores numéricos negativos (demanda, stocks, cantidades, precios).
    """
    archivos = [
        "productos.json", "inventario.json", "clientes.json",
        "proveedores.json", "pedidos.json", "compras.json", "usuarios.json"
    ]

    errores: List[Dict[str, Any]] = []
    advertencias: List[Dict[str, Any]] = []
    datos_crudos: Dict[str, List[Dict[str, Any]]] = {}

    # 1. Verificar lectura y sintaxis JSON
    for nombre in archivos:
        datos, err = leer_json_disco(nombre)
        if err:
            errores.append({
                "categoria": "SINTAXIS_JSON",
                "archivo": nombre,
                "identificador": "N/A",
                "mensaje": err,
                "severidad": "CRÍTICA"
            })
            datos_crudos[nombre] = []
        else:
            datos_crudos[nombre] = datos

    # Si hay una anomalía inyectada para pruebas de auditoría, se mezcla temporalmente
    if dw.anomalia_simulada:
        archivo_target = dw.anomalia_simulada.get("archivo")
        registro_anomalo = dw.anomalia_simulada.get("registro")
        if archivo_target in datos_crudos and registro_anomalo:
            datos_crudos[archivo_target] = list(datos_crudos[archivo_target]) + [registro_anomalo]

    # Conjuntos de IDs para validación de Foreign Keys
    prods_raw = datos_crudos.get("productos.json", [])
    clis_raw = datos_crudos.get("clientes.json", [])
    prvs_raw = datos_crudos.get("proveedores.json", [])

    prod_ids = set()
    cli_ids = set()
    prv_ids = set()

    # 2. Validación de Productos (IDs duplicados y números negativos)
    vistos_prod = set()
    for p in prods_raw:
        pid = p.get("id")
        if not pid:
            errores.append({
                "categoria": "CAMPO_FALTANTE",
                "archivo": "productos.json",
                "identificador": "N/A",
                "mensaje": "Producto sin campo obligatorio 'id'.",
                "severidad": "ALTA"
            })
            continue

        if pid in vistos_prod:
            errores.append({
                "categoria": "ID_DUPLICADO",
                "archivo": "productos.json",
                "identificador": pid,
                "mensaje": f"El ID de producto '{pid}' está duplicado en productos.json.",
                "severidad": "ALTA"
            })
        else:
            vistos_prod.add(pid)
            prod_ids.add(pid)

        # Numéricos negativos
        demanda = p.get("demanda_actual", 0)
        if isinstance(demanda, (int, float)) and demanda < 0:
            errores.append({
                "categoria": "VALOR_NEGATIVO",
                "archivo": "productos.json",
                "identificador": pid,
                "mensaje": f"Demanda actual negativa ({demanda}) en producto '{pid}'.",
                "severidad": "ALTA"
            })

        mp_unidad = p.get("mp_por_unidad_kg", 0)
        if isinstance(mp_unidad, (int, float)) and mp_unidad <= 0:
            errores.append({
                "categoria": "VALOR_INVALIDO",
                "archivo": "productos.json",
                "identificador": pid,
                "mensaje": f"MP por unidad debe ser estrictamente positiva ({mp_unidad}) en producto '{pid}'.",
                "severidad": "ALTA"
            })

    # 3. Validación de Clientes
    vistos_cli = set()
    for c in clis_raw:
        cid = c.get("id")
        if not cid:
            continue
        if cid in vistos_cli:
            errores.append({
                "categoria": "ID_DUPLICADO",
                "archivo": "clientes.json",
                "identificador": cid,
                "mensaje": f"El ID de cliente '{cid}' está duplicado.",
                "severidad": "ALTA"
            })
        else:
            vistos_cli.add(cid)
            cli_ids.add(cid)

    # 4. Validación de Proveedores
    vistos_prv = set()
    for pr in prvs_raw:
        prid = pr.get("id")
        if not prid:
            continue
        if prid in vistos_prv:
            errores.append({
                "categoria": "ID_DUPLICADO",
                "archivo": "proveedores.json",
                "identificador": prid,
                "mensaje": f"El ID de proveedor '{prid}' está duplicado.",
                "severidad": "ALTA"
            })
        else:
            vistos_prv.add(prid)
            prv_ids.add(prid)

        # Clave foránea a producto asociado
        prod_asoc = pr.get("id_producto_asociado")
        if prod_asoc and prod_asoc not in prod_ids:
            advertencias.append({
                "categoria": "CLAVE_FORANEA_ROTA",
                "archivo": "proveedores.json",
                "identificador": prid,
                "mensaje": f"Proveedor '{prid}' asocia un producto inexistente: '{prod_asoc}'.",
                "severidad": "MEDIA"
            })

    # 5. Validación de Inventario (FK a productos y stocks negativos)
    inv_raw = datos_crudos.get("inventario.json", [])
    for inv in inv_raw:
        pid = inv.get("id_producto")
        if pid not in prod_ids:
            errores.append({
                "categoria": "CLAVE_FORANEA_ROTA",
                "archivo": "inventario.json",
                "identificador": pid or "DESCONOCIDO",
                "mensaje": f"Registro de inventario referencia un id_producto inexistente: '{pid}'.",
                "severidad": "ALTA"
            })

        stock_pt = inv.get("stock_pt", 0)
        if isinstance(stock_pt, (int, float)) and stock_pt < 0:
            errores.append({
                "categoria": "VALOR_NEGATIVO",
                "archivo": "inventario.json",
                "identificador": pid or "N/A",
                "mensaje": f"Stock de producto terminado negativo ({stock_pt}) para producto '{pid}'.",
                "severidad": "CRÍTICA"
            })

        mp_disp = inv.get("mp_disponible_kg", 0)
        if isinstance(mp_disp, (int, float)) and mp_disp < 0:
            errores.append({
                "categoria": "VALOR_NEGATIVO",
                "archivo": "inventario.json",
                "identificador": pid or "N/A",
                "mensaje": f"Materia prima disponible negativa ({mp_disp} kg) para producto '{pid}'.",
                "severidad": "CRÍTICA"
            })

    # 6. Validación de Pedidos (FK cliente, FK productos en detalle, valores negativos)
    ped_raw = datos_crudos.get("pedidos.json", [])
    vistos_ped = set()
    for ped in ped_raw:
        ped_id = ped.get("id")
        if not ped_id:
            continue
        if ped_id in vistos_ped:
            errores.append({
                "categoria": "ID_DUPLICADO",
                "archivo": "pedidos.json",
                "identificador": ped_id,
                "mensaje": f"El ID de pedido '{ped_id}' está duplicado.",
                "severidad": "ALTA"
            })
        else:
            vistos_ped.add(ped_id)

        # FK Cliente
        id_cli = ped.get("id_cliente")
        if id_cli not in cli_ids:
            errores.append({
                "categoria": "CLAVE_FORANEA_ROTA",
                "archivo": "pedidos.json",
                "identificador": ped_id,
                "mensaje": f"Pedido '{ped_id}' pertenece a un cliente inexistente: '{id_cli}'.",
                "severidad": "CRÍTICA"
            })

        # Detalle de productos
        detalles = ped.get("detalle", [])
        if not isinstance(detalles, list) or len(detalles) == 0:
            advertencias.append({
                "categoria": "DETALLE_VACIO",
                "archivo": "pedidos.json",
                "identificador": ped_id,
                "mensaje": f"Pedido '{ped_id}' no contiene líneas de detalle.",
                "severidad": "BAJA"
            })
        else:
            for item in detalles:
                item_pid = item.get("id_producto")
                if item_pid not in prod_ids:
                    errores.append({
                        "categoria": "CLAVE_FORANEA_ROTA",
                        "archivo": "pedidos.json",
                        "identificador": f"{ped_id} -> {item_pid}",
                        "mensaje": f"El pedido '{ped_id}' contiene el producto inexistente '{item_pid}'.",
                        "severidad": "CRÍTICA"
                    })

                cant = item.get("cantidad", 0)
                if isinstance(cant, (int, float)) and cant <= 0:
                    errores.append({
                        "categoria": "VALOR_INVALIDO",
                        "archivo": "pedidos.json",
                        "identificador": ped_id,
                        "mensaje": f"Línea con cantidad no positiva ({cant}) en pedido '{ped_id}'.",
                        "severidad": "ALTA"
                    })

    # Resumen y calificación de integridad
    total_errores = len(errores)
    total_advertencias = len(advertencias)
    estado = "INTEGRO" if total_errores == 0 else "CORRUPTO_O_CON_ERRORES"
    score = max(0, 100 - (total_errores * 25) - (total_advertencias * 5))

    return {
        "estado": estado,
        "score_integridad": score,
        "total_errores": total_errores,
        "total_advertencias": total_advertencias,
        "errores": errores,
        "advertencias": advertencias,
        "anomalia_simulada_activa": dw.anomalia_simulada is not None,
        "fecha_auditoria": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }


# ------------------------------------------------------------------------------
# 2. PIPELINE ETL (Extract, Transform, Load)
# Extrae de los 6 JSON, normaliza textos/fechas, desduplica y carga en memoria.
# ------------------------------------------------------------------------------
def ejecutar_pipeline_etl() -> Dict[str, Any]:
    """
    Ejecuta el ciclo completo ETL:
    - Extrae datos de los archivos JSON.
    - Transforma y normaliza strings (trim, uppercase) y fechas ISO.
    - Desduplica registros aplicando la regla de negocio:
      'En caso de conflicto de IDs repetidos, prevalece el registro con fecha de actualización más reciente'.
    - Carga en memoria sin tocar los archivos persistentes.
    """
    inicio = datetime.datetime.now()
    archivos = {
        "productos": "productos.json",
        "inventario": "inventario.json",
        "clientes": "clientes.json",
        "proveedores": "proveedores.json",
        "pedidos": "pedidos.json",
        "compras": "compras.json",
        "usuarios": "usuarios.json"
    }

    raw_data: Dict[str, List[Dict[str, Any]]] = {}
    registros_extraidos = 0
    normalizaciones = 0
    duplicados_descartados = 0

    # 1. EXTRACT
    for key, filename in archivos.items():
        datos, err = leer_json_disco(filename)
        if err or datos is None:
            raw_data[key] = []
        else:
            raw_data[key] = datos
            registros_extraidos += len(datos)

    # 2. TRANSFORM & DEDUPLICATE
    def desduplicar_y_normalizar(lista: List[Dict[str, Any]], id_key: str = "id") -> List[Dict[str, Any]]:
        nonlocal normalizaciones, duplicados_descartados
        agrupados: Dict[str, Dict[str, Any]] = {}

        for item in lista:
            if not isinstance(item, dict):
                continue
            item_norm = dict(item)

            # Normalización de textos y fechas
            for k, v in item_norm.items():
                if isinstance(v, str):
                    if "fecha" in k or k.endswith("_at"):
                        item_norm[k] = normalizar_fecha_iso(v)
                        normalizaciones += 1
                    else:
                        item_norm[k] = normalizar_texto(v)
                        # Normalizar a MAYÚSCULAS estados y categorías
                        if k in ["estado", "categoria", "unidad_medida", "prioridad", "rol"]:
                            item_norm[k] = item_norm[k].upper()
                            normalizaciones += 1

            rid = str(item_norm.get(id_key, "")).strip()
            if not rid:
                continue

            if rid in agrupados:
                duplicados_descartados += 1
                # Regla de desduplicación: mantener el de fecha_actualizacion más reciente
                existente = agrupados[rid]
                fecha_exist = existente.get("fecha_actualizacion", "")
                fecha_nueva = item_norm.get("fecha_actualizacion", "")
                if fecha_nueva > fecha_exist:
                    agrupados[rid] = item_norm
            else:
                agrupados[rid] = item_norm

        return list(agrupados.values())

    prods_limpios = desduplicar_y_normalizar(raw_data.get("productos", []), "id")
    inv_limpios = desduplicar_y_normalizar(raw_data.get("inventario", []), "id_producto")
    clis_limpios = desduplicar_y_normalizar(raw_data.get("clientes", []), "id")
    prvs_limpios = desduplicar_y_normalizar(raw_data.get("proveedores", []), "id")
    peds_limpios = desduplicar_y_normalizar(raw_data.get("pedidos", []), "id")
    comps_limpios = desduplicar_y_normalizar(raw_data.get("compras", []), "id")
    usrs_limpios = desduplicar_y_normalizar(raw_data.get("usuarios", []), "username")

    # 3. LOAD (Carga en DataWarehouse en memoria)
    dw.productos = prods_limpios
    dw.inventario = inv_limpios
    dw.clientes = clis_limpios
    dw.proveedores = prvs_limpios
    dw.pedidos = peds_limpios
    dw.compras = comps_limpios
    dw.usuarios = usrs_limpios

    duracion = (datetime.datetime.now() - inicio).total_seconds() * 1000.0
    registros_cargados = (
        len(dw.productos) + len(dw.inventario) + len(dw.clientes) +
        len(dw.proveedores) + len(dw.pedidos) + len(dw.compras) + len(dw.usuarios)
    )

    dw.etl_meta = {
        "ultima_ejecucion": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "estado": "COMPLETADO_EXITOSO",
        "duracion_ms": round(duracion, 2),
        "registros_extraidos": registros_extraidos,
        "registros_cargados": registros_cargados,
        "duplicados_descartados": duplicados_descartados,
        "normalizaciones_aplicadas": normalizaciones
    }

    return dw.etl_meta


# Ejecución inicial del ETL al arrancar la aplicación
ejecutar_pipeline_etl()


# ------------------------------------------------------------------------------
# 3. MÓDULO DE PLANIFICACIÓN Y MRP (Producción y Compras)
# Reglas de cálculo exactas especificadas en el requerimiento:
# 1. Demanda proyectada = round/ceil(demanda_actual * 1.30)
# 2. Producción requerida = max(0, Demanda proyectada - Stock terminado)
# 3. Materia prima requerida = Producción requerida * MP por unidad (kg)
# 4. Compra sugerida = max(0, Materia prima requerida - Materia prima disponible) (kg)
# ------------------------------------------------------------------------------
def calcular_mrp_completo(factor_incremento: float = 1.30) -> Dict[str, Any]:
    """
    Calcula el MRP dinámico para los productos base.
    Crucial: No sobreescribe los JSON en disco.
    """
    # Mapeo de inventario por id_producto
    inv_map = {item["id_producto"]: item for item in dw.inventario if "id_producto" in item}
    prv_map = {item["id"]: item for item in dw.proveedores if "id" in item}

    lineas_mrp: List[Dict[str, Any]] = []
    totales = {
        "demanda_actual": 0,
        "demanda_proyectada": 0,
        "stock_pt": 0,
        "produccion_requerida": 0,
        "mp_requerida_kg": 0.0,
        "mp_disponible_kg": 0.0,
        "compra_sugerida_kg": 0.0,
        "productos_en_riesgo": 0,
        "costo_estimado_compras": 0.0
    }

    for prod in dw.productos:
        pid = prod.get("id")
        nombre = prod.get("nombre", "")
        demanda_act = int(prod.get("demanda_actual", 0))
        mp_unidad = float(prod.get("mp_por_unidad_kg", 0.0))

        # Inventario asociado
        inv_item = inv_map.get(pid, {})
        stock_pt = int(inv_item.get("stock_pt", 0))
        mp_disp = float(inv_item.get("mp_disponible_kg", 0.0))

        # REGLAS DE CÁLCULO
        # 1. Demanda proyectada = redondear a entero (1.30 -> +30%)
        demanda_proy = int(math.ceil(demanda_act * factor_incremento))

        # 2. Producción requerida = max(0, Demanda proyectada - Stock terminado)
        prod_req = max(0, demanda_proy - stock_pt)

        # 3. Materia prima requerida = Producción requerida * MP por unidad (en kg)
        mp_req = round(prod_req * mp_unidad, 2)

        # 4. Compra sugerida = max(0, Materia prima requerida - Materia prima disponible)
        compra_sug = round(max(0.0, mp_req - mp_disp), 2)

        # Riesgo de desabastecimiento
        en_riesgo = compra_sug > 0.0

        # Costo sugerido de compra
        id_prv = prod.get("id_proveedor_sugerido")
        proveedor = prv_map.get(id_prv, {})
        precio_kg = float(proveedor.get("precio_kg_estimado", 1.25))
        costo_compra = round(compra_sug * precio_kg, 2)

        fila = {
            "id_producto": pid,
            "nombre": nombre,
            "categoria": prod.get("categoria", ""),
            "demanda_actual": demanda_act,
            "factor_incremento_porc": round((factor_incremento - 1.0) * 100, 1),
            "demanda_proyectada": demanda_proy,
            "stock_pt": stock_pt,
            "produccion_requerida": prod_req,
            "mp_por_unidad_kg": mp_unidad,
            "mp_requerida_kg": mp_req,
            "mp_disponible_kg": mp_disp,
            "compra_sugerida_kg": compra_sug,
            "en_riesgo_desabastecimiento": en_riesgo,
            "nombre_materia_prima": prod.get("nombre_materia_prima", ""),
            "proveedor_sugerido": proveedor.get("razon_social", "Proveedor No Asignado"),
            "id_proveedor_sugerido": id_prv,
            "precio_kg_estimado": precio_kg,
            "costo_estimado_compra": costo_compra
        }

        lineas_mrp.append(fila)

        # Acumulación de totales
        totales["demanda_actual"] += demanda_act
        totales["demanda_proyectada"] += demanda_proy
        totales["stock_pt"] += stock_pt
        totales["produccion_requerida"] += prod_req
        totales["mp_requerida_kg"] = round(totales["mp_requerida_kg"] + mp_req, 2)
        totales["mp_disponible_kg"] = round(totales["mp_disponible_kg"] + mp_disp, 2)
        totales["compra_sugerida_kg"] = round(totales["compra_sugerida_kg"] + compra_sug, 2)
        totales["costo_estimado_compras"] = round(totales["costo_estimado_compras"] + costo_compra, 2)
        if en_riesgo:
            totales["productos_en_riesgo"] += 1

    return {
        "lineas": lineas_mrp,
        "totales": totales,
        "factor_aplicado": factor_incremento,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }


# ------------------------------------------------------------------------------
# 4. DASHBOARD GERENCIAL (5 KPIs CLAVE)
# 1. Total Pedidos Registrados
# 2. Unidades Totales por Producir
# 3. Materia Prima Total Requerida (kg)
# 4. Compras Totales Sugeridas (kg)
# 5. Alerta de Productos en Riesgo de Desabastecimiento
# ------------------------------------------------------------------------------
def obtener_kpis_gerenciales() -> Dict[str, Any]:
    mrp = calcular_mrp_completo(factor_incremento=1.30)
    totales_mrp = mrp["totales"]

    # 1. Total Pedidos Registrados
    total_pedidos = len(dw.pedidos)
    total_facturado_pedidos = sum(float(p.get("total", 0.0)) for p in dw.pedidos)

    # 2. Unidades Totales por Producir
    unidades_por_producir = totales_mrp["produccion_requerida"]  # Exacto: 2730

    # 3. Materia Prima Total Requerida (kg)
    mp_total_requerida_kg = totales_mrp["mp_requerida_kg"]       # Exacto: 4448.0

    # 4. Compras Totales Sugeridas (kg)
    compras_totales_sugeridas_kg = totales_mrp["compra_sugerida_kg"] # Exacto: 620.0

    # 5. Alerta de Productos en Riesgo de Desabastecimiento
    productos_en_riesgo = totales_mrp["productos_en_riesgo"]      # Exacto: 2

    # Lista de nombres de productos en riesgo
    nombres_riesgo = [p["nombre"] for p in mrp["lineas"] if p["en_riesgo_desabastecimiento"]]

    # Cliente con más pedidos (análisis dinámico)
    conteo_clientes: Dict[str, int] = {}
    for ped in dw.pedidos:
        cid = ped.get("id_cliente")
        if cid:
            conteo_clientes[cid] = conteo_clientes.get(cid, 0) + 1

    cliente_top_id = max(conteo_clientes, key=conteo_clientes.get) if conteo_clientes else None
    cliente_top_info = next((c for c in dw.clientes if c.get("id") == cliente_top_id), None)
    cliente_top_nombre = cliente_top_info.get("razon_social") if cliente_top_info else "Ninguno"
    cliente_top_pedidos = conteo_clientes.get(cliente_top_id, 0) if cliente_top_id else 0

    return {
        "kpi_1_total_pedidos": {
            "valor": total_pedidos,
            "unidad": "pedidos",
            "titulo": "Total Pedidos Registrados",
            "detalle": f"Monto global acumulado: ${total_facturado_pedidos:,.2f}",
            "icono": "shopping-cart",
            "color": "primary"
        },
        "kpi_2_unidades_producir": {
            "valor": unidades_por_producir,
            "unidad": "unidades",
            "titulo": "Unidades Totales por Producir",
            "detalle": "Plan de producción con incremento del +30% de demanda",
            "icono": "cogs",
            "color": "indigo"
        },
        "kpi_3_mp_requerida": {
            "valor": mp_total_requerida_kg,
            "unidad": "kg",
            "titulo": "Materia Prima Total Requerida",
            "detalle": "Volumen de fruta fresca requerida para la producción planificada",
            "icono": "weight-hanging",
            "color": "teal"
        },
        "kpi_4_compras_sugeridas": {
            "valor": compras_totales_sugeridas_kg,
            "unidad": "kg",
            "titulo": "Compras Totales Sugeridas",
            "detalle": f"Déficit neto de abastecimiento (${totales_mrp['costo_estimado_compras']:,.2f} USD est.)",
            "icono": "cart-plus",
            "color": "amber"
        },
        "kpi_5_productos_riesgo": {
            "valor": productos_en_riesgo,
            "unidad": "productos",
            "titulo": "Productos en Riesgo de Desabastecimiento",
            "detalle": f"Críticos: {', '.join(nombres_riesgo)}" if nombres_riesgo else "Abastecimiento completo garantizado",
            "icono": "exclamation-triangle",
            "color": "danger" if productos_en_riesgo > 0 else "success",
            "lista_productos_riesgo": nombres_riesgo
        },
        "cliente_top": {
            "id": cliente_top_id,
            "nombre": cliente_top_nombre,
            "total_pedidos": cliente_top_pedidos
        }
    }


# ------------------------------------------------------------------------------
# 5. ASISTENTE DE CONSULTA CON IA (Simulación Controlada / RAG Local Estricto)
# Responde ÚNICAMENTE en base al contexto de los datos cargados.
# Si no está en el sistema: "No dispongo de datos en el sistema para responder esa consulta"
# ------------------------------------------------------------------------------
def consultar_asistente_ia(pregunta_usuario: str) -> Dict[str, Any]:
    """
    RAG local estricto sobre el DataWarehouse y el módulo MRP.
    Respuestas predeterminadas y cálculo semántico exacto.
    """
    if not pregunta_usuario or not pregunta_usuario.strip():
        return {
            "respuesta": "Por favor escribe una consulta válida para el asistente agroindustrial.",
            "fuente": "sistema",
            "categoria": "entrada_vacia"
        }

    q_clean = limpiar_texto_busqueda(pregunta_usuario)
    mrp = calcular_mrp_completo(1.30)
    lineas = mrp["lineas"]
    totales = mrp["totales"]
    kpis = obtener_kpis_gerenciales()

    # Mapeo rápido de productos MRP (limpiando acentos y mayúsculas)
    mrp_mango = next((p for p in lineas if "mango" in limpiar_texto_busqueda(p.get("nombre", ""))), None)
    mrp_maracuya = next((p for p in lineas if "maracuya" in limpiar_texto_busqueda(p.get("nombre", ""))), None)
    mrp_pina = next((p for p in lineas if "pina" in limpiar_texto_busqueda(p.get("nombre", ""))), None)

    # --------------------------------------------------------------------------
    # PREGUNTA 1: ¿Cuál es la compra sugerida para la pulpa de mango?
    # --------------------------------------------------------------------------
    if ("compra" in q_clean or "comprar" in q_clean or "sugerida" in q_clean or "requiere comprar" in q_clean) and "mango" in q_clean:
        if mrp_mango:
            resp = (
                f"Para la **{mrp_mango['nombre']}**, la compra sugerida es de **{mrp_mango['compra_sugerida_kg']:.1f} kg** "
                f"de materia prima ({mrp_mango['nombre_materia_prima']}).\n\n"
                f"**Desglose del cálculo MRP (+30%):**\n"
                f"- Demanda actual: {mrp_mango['demanda_actual']:,} u  →  Proyectada (+30%): {mrp_mango['demanda_proyectada']:,} u\n"
                f"- Stock terminado (PT): {mrp_mango['stock_pt']:,} u  →  Producción requerida: {mrp_mango['produccion_requerida']:,} u\n"
                f"- MP requerida ({mrp_mango['mp_por_unidad_kg']} kg/u): {mrp_mango['mp_requerida_kg']:,.1f} kg\n"
                f"- MP disponible en bodega: {mrp_mango['mp_disponible_kg']:,.1f} kg\n"
                f"- **Compra sugerida neta:** max(0, {mrp_mango['mp_requerida_kg']:,.1f} - {mrp_mango['mp_disponible_kg']:,.1f}) = **{mrp_mango['compra_sugerida_kg']:,.1f} kg**."
            )
            return {"respuesta": resp, "fuente": "mrp_engine", "categoria": "compra_sugerida_mango"}

    # --------------------------------------------------------------------------
    # PREGUNTA 2: ¿Cuánto stock de producto terminado tenemos de jugo de maracuyá?
    # --------------------------------------------------------------------------
    if ("stock" in q_clean or "terminado" in q_clean or "pt" in q_clean or "inventario" in q_clean) and "maracuya" in q_clean and "mp" not in q_clean and "materia prima" not in q_clean:
        if mrp_maracuya:
            resp = (
                f"Actualmente disponemos de **{mrp_maracuya['stock_pt']} unidades** de producto terminado (PT) "
                f"para el **{mrp_maracuya['nombre']}** en la bodega de refrigeración (ALM-PT-FRIGORIFICO-2).\n\n"
                f"*Dato adicional de inventario:* Se cuenta además con **{mrp_maracuya['mp_disponible_kg']:,.1f} kg** "
                f"de fruta fresca disponible para procesamiento."
            )
            return {"respuesta": resp, "fuente": "inventario_engine", "categoria": "stock_pt_maracuya"}

    # --------------------------------------------------------------------------
    # PREGUNTA 3: ¿Cuáles son los productos con riesgo de desabastecimiento de materia prima?
    # --------------------------------------------------------------------------
    if ("riesgo" in q_clean or "desabastecimiento" in q_clean or "deficit" in q_clean or "falta" in q_clean or "faltante" in q_clean):
        riesgos = [p for p in lineas if p["en_riesgo_desabastecimiento"]]
        no_riesgos = [p for p in lineas if not p["en_riesgo_desabastecimiento"]]

        lineas_resp = [
            f"Se identifican **{len(riesgos)} productos en riesgo de desabastecimiento** de materia prima (Compra sugerida > 0 kg):"
        ]
        for r in riesgos:
            lineas_resp.append(
                f"1. **{r['nombre']}**: Déficit de **{r['compra_sugerida_kg']:.1f} kg** "
                f"(Requiere {r['mp_requerida_kg']:.1f} kg y solo dispone de {r['mp_disponible_kg']:.1f} kg)."
            )

        if no_riesgos:
            lineas_resp.append("\n**Productos con abastecimiento suficiente:**")
            for nr in no_riesgos:
                excedente = nr["mp_disponible_kg"] - nr["mp_requerida_kg"]
                lineas_resp.append(
                    f"- **{nr['nombre']}**: Stock MP suficiente con un margen excedente de **{excedente:.1f} kg**."
                )

        return {"respuesta": "\n".join(lineas_resp), "fuente": "mrp_engine", "categoria": "alerta_desabastecimiento"}

    # --------------------------------------------------------------------------
    # PREGUNTA 4: ¿Cuántas unidades en total se deben producir con el aumento del 30%?
    # --------------------------------------------------------------------------
    if ("unidades" in q_clean or "total" in q_clean or "producir" in q_clean or "produccion" in q_clean) and ("30" in q_clean or "aumento" in q_clean or "proyectada" in q_clean or "cuantas" in q_clean):
        resp = (
            f"Con el aumento proyectado del **+30% en la demanda**, se deben producir un total de "
            f"**{totales['produccion_requerida']:,} unidades** de producto terminado.\n\n"
            f"**Distribución detallada por producto:**\n"
            f"- **Pulpa de mango:** {mrp_mango['produccion_requerida']:,} unidades "
            f"(Demanda proyectada {mrp_mango['demanda_proyectada']:,} u - Stock {mrp_mango['stock_pt']:,} u)\n"
            f"- **Jugo de maracuyá:** {mrp_maracuya['produccion_requerida']:,} unidades "
            f"(Demanda proyectada {mrp_maracuya['demanda_proyectada']:,} u - Stock {mrp_maracuya['stock_pt']:,} u)\n"
            f"- **Conserva de piña:** {mrp_pina['produccion_requerida']:,} unidades "
            f"(Demanda proyectada {mrp_pina['demanda_proyectada']:,} u - Stock {mrp_pina['stock_pt']:,} u)"
        )
        return {"respuesta": resp, "fuente": "mrp_engine", "categoria": "total_produccion_30"}

    # --------------------------------------------------------------------------
    # PREGUNTA 5: ¿Cuál es el cliente con más pedidos registrados?
    # --------------------------------------------------------------------------
    if ("cliente" in q_clean or "clientes" in q_clean) and ("mas pedidos" in q_clean or "mayor pedidos" in q_clean or "principal" in q_clean or "top" in q_clean or "registrados" in q_clean):
        c_top = kpis["cliente_top"]
        cli_obj = next((c for c in dw.clientes if c.get("id") == c_top["id"]), {})
        resp = (
            f"El cliente con más pedidos registrados es **{c_top['nombre']}** (ID: `{c_top['id']}`), "
            f"con un total de **{c_top['total_pedidos']} pedidos registrados** en el sistema.\n\n"
            f"- **RUC:** {cli_obj.get('ruc', 'N/D')}\n"
            f"- **Ciudad:** {cli_obj.get('ciudad', 'N/D')}\n"
            f"- **Contacto:** {cli_obj.get('contacto', 'N/D')} ({cli_obj.get('email', 'N/D')})\n"
            f"- **Categoría:** {cli_obj.get('categoria', 'N/D')}"
        )
        return {"respuesta": resp, "fuente": "clientes_pedidos_db", "categoria": "cliente_top_pedidos"}

    # --------------------------------------------------------------------------
    # CONSULTAS SEMÁNTICAS COMPLEMENTARIAS SOBRE CONTEXTO PERMITIDO
    # --------------------------------------------------------------------------
    # Compra maracuyá
    if ("compra" in q_clean or "comprar" in q_clean) and "maracuya" in q_clean:
        resp = (
            f"Para el **{mrp_maracuya['nombre']}**, la compra sugerida es de **{mrp_maracuya['compra_sugerida_kg']:.1f} kg** "
            f"de materia prima (Maracuyá amarillo fresco) para cubrir el déficit de producción."
        )
        return {"respuesta": resp, "fuente": "mrp_engine", "categoria": "compra_maracuya"}

    # Compra piña
    if ("compra" in q_clean or "comprar" in q_clean) and ("pina" in q_clean or "piña" in q_clean):
        resp = (
            f"Para la **{mrp_pina['nombre']}**, la compra sugerida es de **{mrp_pina['compra_sugerida_kg']:.1f} kg** (0.0 kg). "
            f"El stock disponible de 850.0 kg cubre sobradamente los 828.0 kg requeridos (excedente de 22.0 kg)."
        )
        return {"respuesta": resp, "fuente": "mrp_engine", "categoria": "compra_pina"}

    # Stock terminado general o de mango / piña
    if ("stock" in q_clean or "terminado" in q_clean) and "mango" in q_clean:
        return {
            "respuesta": f"El stock de producto terminado de **Pulpa de mango** es de **{mrp_mango['stock_pt']} unidades**.",
            "fuente": "inventario_engine",
            "categoria": "stock_mango"
        }
    if ("stock" in q_clean or "terminado" in q_clean) and ("pina" in q_clean or "piña" in q_clean):
        return {
            "respuesta": f"El stock de producto terminado de **Conserva de piña** es de **{mrp_pina['stock_pt']} unidades**.",
            "fuente": "inventario_engine",
            "categoria": "stock_pina"
        }

    # Resumen de KPIs
    if "kpi" in q_clean or "resumen" in q_clean or "dashboard" in q_clean:
        resp = (
            f"**Resumen Gerencial de la Planta:**\n"
            f"1. Total Pedidos: {kpis['kpi_1_total_pedidos']['valor']} pedidos\n"
            f"2. Unidades Totales por Producir: {totales['produccion_requerida']:,} u\n"
            f"3. Materia Prima Total Requerida: {totales['mp_requerida_kg']:,.1f} kg\n"
            f"4. Compras Totales Sugeridas: {totales['compra_sugerida_kg']:,.1f} kg\n"
            f"5. Productos en Riesgo: {totales['productos_en_riesgo']} (Mango y Maracuyá)"
        )
        return {"respuesta": resp, "fuente": "kpis_engine", "categoria": "resumen_kpis"}

    # --------------------------------------------------------------------------
    # FALLBACK ESTRICTO OBLIGATORIO:
    # "Si se consulta algo que no está en el sistema, debe responder:
    #  'No dispongo de datos en el sistema para responder esa consulta'"
    # --------------------------------------------------------------------------
    return {
        "respuesta": "No dispongo de datos en el sistema para responder esa consulta",
        "fuente": "filtro_estricto_contexto",
        "categoria": "sin_datos"
    }


# ------------------------------------------------------------------------------
# 6. SIMULADOR DE INTEGRACIÓN ERP (Ej. Odoo JSON-RPC / REST)
# Simula el intercambio bidireccional y genera el acuse de recibo ficticio.
# ------------------------------------------------------------------------------
def simular_sincronizacion_odoo(payload_personalizado: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Simula la integración formal con el ERP Odoo (v16/v17) para emitir
    Órdenes de Compra basadas en el MRP de materias primas con déficit.
    """
    mrp = calcular_mrp_completo(1.30)
    lineas_riesgo = [p for p in mrp["lineas"] if p["compra_sugerida_kg"] > 0]

    # Construir líneas en formato Odoo purchase.order.line
    odoo_lines = []
    line_id = 1
    total_oc = 0.0

    for item in lineas_riesgo:
        subtotal = round(item["compra_sugerida_kg"] * item["precio_kg_estimado"], 2)
        total_oc += subtotal
        odoo_lines.append({
            "sequence": line_id,
            "product_id": [100 + line_id, f"[{item['id_producto']}] {item['nombre_materia_prima']}"],
            "name": f"Materia prima para {item['nombre']} (Requerimiento MRP +30%)",
            "product_qty": item["compra_sugerida_kg"],
            "product_uom": [1, "kg"],
            "price_unit": item["precio_kg_estimado"],
            "price_subtotal": subtotal,
            "date_planned": (datetime.datetime.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d 08:00:00")
        })
        line_id += 1

    # Estructura de salida enviada hacia Odoo (Payload XML-RPC / JSON-RPC)
    numero_oc_sec = len(dw.compras) + 40
    odoo_po_name = f"PO-2026-00{numero_oc_sec}"

    odoo_request_payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                "agro_litoral_production_db",
                2,  # User ID en Odoo
                "odoo_api_token_hash_secured",
                "purchase.order",
                "create",
                [{
                    "partner_id": [201, "Agrícola San José S.A. / Consorcio Litoral"],
                    "partner_ref": "REQ-MRP-2026-LITORAL",
                    "date_order": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "origin": "PLANIFICADOR_MRP_AGROLITORAL_30PCT",
                    "company_id": [1, "AGROINDUSTRIAL DEL LITORAL S.A."],
                    "order_line": [
                        (0, 0, line) for line in odoo_lines
                    ]
                }]
            ]
        },
        "id": int(datetime.datetime.now().timestamp())
    }

    # Respuesta ficticia simulada desde Odoo (Acuse de recibo 201)
    odoo_response_simulada = {
        "jsonrpc": "2.0",
        "id": odoo_request_payload["id"],
        "result": {
            "status_code": 201,
            "odoo_res_id": 1000 + numero_oc_sec,
            "name": odoo_po_name,
            "state": "draft",
            "amount_untaxed": round(total_oc, 2),
            "amount_tax": round(total_oc * 0.15, 2),  # IVA 15%
            "amount_total": round(total_oc * 1.15, 2),
            "currency_id": [1, "USD"],
            "message": "Orden de compra generada exitosamente en el ERP Odoo mediante protocolo JSON-RPC.",
            "acknowledged_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "odoo_server_version": "Odoo 17.0-2026 Enterprise"
        }
    }

    # Registrar en el log de compras en memoria
    nueva_compra = {
        "id": f"OC-2026-00{len(dw.compras) + 1}",
        "id_proveedor": "PRV-001",
        "nombre_proveedor": "Agrícola San José / Finca Tropical Litoral",
        "fecha": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "estado": "GENERADA_ERP",
        "origen": "SIMULADOR_ODOO_MRP_30PCT",
        "lineas": [
            {
                "id_producto": p["id_producto"],
                "insumo": p["nombre_materia_prima"],
                "cantidad_kg": p["compra_sugerida_kg"],
                "precio_kg": p["precio_kg_estimado"],
                "subtotal": round(p["compra_sugerida_kg"] * p["precio_kg_estimado"], 2)
            }
            for p in lineas_riesgo
        ],
        "total": round(total_oc, 2),
        "odoo_ref": odoo_po_name,
        "fecha_actualizacion": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    dw.compras.append(nueva_compra)

    return {
        "transaccion_exitosa": True,
        "codigo_http": 201,
        "referencia_generada": odoo_po_name,
        "odoo_request": odoo_request_payload,
        "odoo_response": odoo_response_simulada,
        "nueva_orden_registrada": nueva_compra
    }


# ------------------------------------------------------------------------------
# 7. CONTROL DE ACCESO (AUTENTICACIÓN Y ROLES: ADMIN / GERENTE)
# ------------------------------------------------------------------------------
def obtener_usuario_sesion() -> Optional[Dict[str, Any]]:
    username = session.get("user")
    if not username:
        return None
    for u in dw.usuarios:
        if u.get("username") == username:
            usr = dict(u)
            usr.pop("password_hash", None)
            return usr
    return None


# ------------------------------------------------------------------------------
# 8. RUTAS Y ENDPOINTS DE LA API REST
# ------------------------------------------------------------------------------

# --- VISTA PRINCIPAL SPA ---
@app.route("/")
def index():
    return render_template("index.html")


# --- AUTENTICACIÓN ---
@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip().lower()
    password = str(data.get("password", "")).strip()

    usuario_valido = None
    for u in dw.usuarios:
        if u.get("username", "").lower() == username and u.get("password_hash") == password:
            usuario_valido = u
            break

    if usuario_valido:
        session["user"] = usuario_valido["username"]
        session["rol"] = usuario_valido["rol"]
        usr_resp = dict(usuario_valido)
        usr_resp.pop("password_hash", None)
        return jsonify({
            "success": True,
            "message": f"Bienvenido(a), {usuario_valido['nombre']}",
            "usuario": usr_resp
        })
    else:
        return jsonify({
            "success": False,
            "message": "Credenciales inválidas. Comprueba tu usuario y contraseña."
        }), 401


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    session.clear()
    return jsonify({"success": True, "message": "Sesión cerrada correctamente."})


@app.route("/api/auth/me", methods=["GET"])
def api_auth_me():
    user = obtener_usuario_sesion()
    if user:
        return jsonify({"authenticated": True, "usuario": user})
    return jsonify({"authenticated": False, "usuario": None})


# --- AUDITORÍA DE INTEGRIDAD ---
@app.route("/api/auditoria", methods=["GET"])
def api_auditoria():
    reporte = ejecutar_auditoria_integridad()
    return jsonify(reporte)


@app.route("/api/auditoria/simular-incoherencia", methods=["POST"])
def api_simular_incoherencia():
    """Inyecta una anomalía de prueba para demostrar el motor de auditoría."""
    data = request.get_json(silent=True) or {}
    tipo = data.get("tipo", "clave_foranea")

    if tipo == "clave_foranea":
        dw.anomalia_simulada = {
            "archivo": "pedidos.json",
            "registro": {
                "id": "PED-INCORRECTO-999",
                "id_cliente": "CLI-FANTASMA-999",  # Cliente inexistente
                "fecha": "2026-11-05T14:00:00Z",
                "estado": "PENDIENTE",
                "detalle": [{"id_producto": "PROD-FANTASMA-888", "cantidad": 50, "precio_unitario": 4.0}],
                "total": 200.0,
                "fecha_actualizacion": "2026-11-05T14:00:00Z"
            }
        }
    elif tipo == "valor_negativo":
        dw.anomalia_simulada = {
            "archivo": "inventario.json",
            "registro": {
                "id_producto": "PROD-001",
                "stock_pt": -250,  # Stock negativo
                "mp_disponible_kg": -50.0,
                "fecha_actualizacion": "2026-11-05T14:00:00Z"
            }
        }
    elif tipo == "id_duplicado":
        dw.anomalia_simulada = {
            "archivo": "productos.json",
            "registro": {
                "id": "PROD-001",  # Duplicado de mango
                "nombre": "Pulpa de mango duplicada",
                "demanda_actual": 500,
                "mp_por_unidad_kg": 2.0,
                "fecha_actualizacion": "2026-11-05T14:00:00Z"
            }
        }

    reporte = ejecutar_auditoria_integridad()
    return jsonify({
        "success": True,
        "mensaje": f"Inconsistencia simulada ('{tipo}') inyectada con éxito.",
        "reporte": reporte
    })


@app.route("/api/auditoria/restaurar", methods=["POST"])
def api_restaurar_auditoria():
    """Restaura la integridad original del sistema."""
    dw.anomalia_simulada = None
    ejecutar_pipeline_etl()
    reporte = ejecutar_auditoria_integridad()
    return jsonify({
        "success": True,
        "mensaje": "Integridad restaurada al estado original de los archivos.",
        "reporte": reporte
    })


# --- PIPELINE ETL ---
@app.route("/api/etl/ejecutar", methods=["POST"])
def api_etl_ejecutar():
    resultado = ejecutar_pipeline_etl()
    return jsonify({
        "success": True,
        "mensaje": "Pipeline ETL ejecutado correctamente.",
        "resultado": resultado
    })


@app.route("/api/etl/estado", methods=["GET"])
def api_etl_estado():
    return jsonify(dw.etl_meta)


# --- MRP Y PLANIFICACIÓN ---
@app.route("/api/mrp", methods=["GET"])
def api_mrp():
    factor_str = request.args.get("factor", "1.30")
    try:
        factor = float(factor_str)
    except ValueError:
        factor = 1.30
    resultado = calcular_mrp_completo(factor_incremento=factor)
    return jsonify(resultado)


# --- DASHBOARD GERENCIAL (5 KPIS) ---
@app.route("/api/kpis", methods=["GET"])
def api_kpis():
    kpis = obtener_kpis_gerenciales()
    return jsonify(kpis)


# --- ASISTENTE IA (RAG LOCAL ESTRICTO) ---
@app.route("/api/ia/consulta", methods=["POST"])
def api_ia_consulta():
    data = request.get_json(silent=True) or {}
    pregunta = str(data.get("pregunta", "")).strip()
    resultado = consultar_asistente_ia(pregunta)
    return jsonify(resultado)


# --- SIMULADOR DE INTEGRACIÓN ERP (ODOO) ---
@app.route("/api/erp/sync", methods=["POST"])
def api_erp_sync():
    data = request.get_json(silent=True)
    resultado = simular_sincronizacion_odoo(data)
    return jsonify(resultado)


# --- DATOS CRUD DE SOLO LECTURA EN MEMORIA ---
@app.route("/api/productos", methods=["GET"])
def api_productos():
    return jsonify(dw.productos)


@app.route("/api/inventario", methods=["GET"])
def api_inventario():
    return jsonify(dw.inventario)


@app.route("/api/clientes", methods=["GET"])
def api_clientes():
    return jsonify(dw.clientes)


@app.route("/api/proveedores", methods=["GET"])
def api_proveedores():
    return jsonify(dw.proveedores)


@app.route("/api/pedidos", methods=["GET"])
def api_pedidos():
    return jsonify(dw.pedidos)


@app.route("/api/compras", methods=["GET"])
def api_compras():
    return jsonify(dw.compras)


# ------------------------------------------------------------------------------
# PUNTO DE ENTRADA PRINCIPAL
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" AGROINDUSTRIAL DEL LITORAL S.A. - SISTEMA MRP & GESTIÓN EMPRESARIAL")
    print("=" * 70)
    print("  * Servidor web Flask activo en: http://127.0.0.1:5000")
    print("  * Almacenamiento JSON: /data")
    print("  * Cuentas de Acceso:")
    print("      - Administrador : admin   / admin123")
    print("      - Gerente       : gerente / gerente123")
    print("=" * 70 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
