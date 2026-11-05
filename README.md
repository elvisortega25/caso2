# CASO DE ESTUDIO 2: AGROINDUSTRIAL DEL LITORAL S.A.
## Prototipo de Integración de Procesos y Sistemas Empresariales (MRP & ERP)

Sistema empresarial desarrollado en **Python (Flask)**, almacenamiento desacoplado en **JSON**, y frontend interactivo Single Page Application (SPA) con **Vanilla JavaScript**, diseñado para la planificación de producción y abastecimiento con un incremento proyectado del **+30% en la demanda**.

---

### 1. ESTRUCTURA DEL PROYECTO
```text
caso 2/
├── data/                               # 6 archivos JSON persistentes + usuarios
│   ├── productos.json                  # Catálogo de los 3 productos base
│   ├── inventario.json                 # Stocks de Producto Terminado (PT) y Materia Prima (MP)
│   ├── clientes.json                   # Cartera de clientes agroindustriales
│   ├── proveedores.json                # Proveedores calificados de fruta
│   ├── pedidos.json                    # Pedidos comerciales con detalle y estado
│   ├── compras.json                    # Histórico de órdenes de compra
│   └── usuarios.json                   # Credenciales y roles (Administrador / Gerente)
├── static/
│   ├── css/
│   │   └── styles.css                  # Estilos corporativos modernos (Dark/Enterprise Theme)
│   └── js/
│       └── app.js                      # Lógica Vanilla JS, consumo de API REST y UI reactiva
├── templates/
│   └── index.html                      # SPA interactiva con Dashboard, MRP, IA y ERP
├── app.py                              # Backend Flask: ETL, Auditoría, MRP, IA RAG y API REST
├── requirements.txt                    # Dependencias mínimas (Flask)
├── run.bat                             # Script de arranque rápido para Windows
└── README.md                           # Documentación completa del sistema
```

---

### 2. DATOS BASE EXACTOS Y REGLAS DE NEGOCIO

#### Productos Iniciales:
1. **Pulpa de mango:**
   - Demanda actual: `1000 u`
   - Stock terminado (PT): `180 u`
   - Materia Prima por unidad: `2.0 kg/u`
   - Materia Prima disponible: `1900.0 kg`

2. **Jugo de maracuyá:**
   - Demanda actual: `800 u`
   - Stock terminado (PT): `120 u`
   - Materia Prima por unidad: `1.5 kg/u`
   - Materia Prima disponible: `1100.0 kg`

3. **Conserva de piña:**
   - Demanda actual: `600 u`
   - Stock terminado (PT): `90 u`
   - Materia Prima por unidad: `1.2 kg/u`
   - Materia Prima disponible: `850.0 kg`

#### Fórmulas de Cálculo Aplicadas (MRP):
1. **Demanda proyectada** = `demanda_actual * 1.30` (redondeado a enteros):
   - Mango: `1000 * 1.30 = 1300 u`
   - Maracuyá: `800 * 1.30 = 1040 u`
   - Piña: `600 * 1.30 = 780 u`
   - *Total Demanda Proyectada: 3,120 u*

2. **Producción requerida** = `max(0, Demanda proyectada - Stock terminado)`:
   - Mango: `max(0, 1300 - 180) = 1120 u`
   - Maracuyá: `max(0, 1040 - 120) = 920 u`
   - Piña: `max(0, 780 - 90) = 690 u`
   - *Total Producción Requerida: 2,730 u*

3. **Materia prima requerida** = `Producción requerida * MP por unidad (kg)`:
   - Mango: `1120 * 2.0 = 2240.0 kg`
   - Maracuyá: `920 * 1.5 = 1380.0 kg`
   - Piña: `690 * 1.2 = 828.0 kg`
   - *Total Materia Prima Requerida: 4,448.0 kg*

4. **Compra sugerida** = `max(0, Materia prima requerida - Materia prima disponible) (kg)`:
   - Mango: `max(0, 2240.0 - 1900.0) = 340.0 kg` *(Déficit - Riesgo)*
   - Maracuyá: `max(0, 1380.0 - 1100.0) = 280.0 kg` *(Déficit - Riesgo)*
   - Piña: `max(0, 828.0 - 850.0) = 0.0 kg` *(Stock suficiente, margen de +22.0 kg)*
   - *Total Compras Sugeridas: 620.0 kg*

> **Principio de Inmutabilidad:** El sistema opera en memoria mediante el objeto `DataWarehouse`. Los archivos JSON en `/data` nunca son sobreescritos durante los cálculos.

---

### 3. ROLES Y CREDENCIALES DE ACCESO (LOGIN)

El sistema incluye una pantalla de autenticación con selector rápido de usuarios:

| Usuario | Contraseña | Rol | Perfil y Acceso |
| :--- | :--- | :--- | :--- |
| `admin` | `admin123` | **ADMINISTRADOR** | Acceso total: Ejecución ETL, Auditoría de Integridad, Inyección de anomalías de prueba, ERP Sync y MRP. |
| `gerente` | `gerente123` | **GERENTE** | Acceso ejecutivo: Dashboard (5 KPIs), Matriz MRP, Asistente IA, Visualización de Pedidos e Inventario. |

---

### 4. GUÍA DE EJECUCIÓN PASO A PASO

#### Requisitos Previos:
- Python 3.10+ (o lanzador `py` de Windows).
- Librería Flask instalada (`pip install Flask`).

#### Paso 1: Abrir la terminal en la carpeta del proyecto
```powershell
cd "c:\Users\Administrador\Downloads\trabajoenclases\caso 2"
```

#### Paso 2: Instalar dependencias (si no se han instalado)
```powershell
py -m pip install -r requirements.txt
```

#### Paso 3: Iniciar el servidor web
```powershell
py app.py
# O alternativamente:
# python app.py
# O haciendo doble clic en el archivo run.bat
```

#### Paso 4: Acceder en el navegador
Ingresar a: **`http://127.0.0.1:5000`**

---

### 5. MÓDULOS DEL SISTEMA

1. **Dashboard Gerencial (5 KPIs):**
   - KPI 1: Total Pedidos Registrados (6 pedidos acumulados).
   - KPI 2: Unidades Totales por Producir (**2,730 u**).
   - KPI 3: Materia Prima Total Requerida (**4,448.0 kg**).
   - KPI 4: Compras Totales Sugeridas (**620.0 kg**).
   - KPI 5: Alerta de Productos en Riesgo (**2 productos**: Pulpa de mango y Jugo de maracuyá).

2. **Matriz Planificación MRP (+30%):**
   - Tabla interactiva con columnas obligatorias:
     `[Producto | Demanda Actual | Proyección (+30%) | Stock PT | Producción Requerida | MP/Unidad | MP Req (kg) | MP Disp (kg) | Compra Sugerida (kg)]`.
   - Selector dinámico de incrementos (+10%, +20%, +30%, +50%).
   - Botón de despacho directo a Odoo ERP.

3. **Motor de Validación de Integridad:**
   - Detecta JSON mal formado, IDs duplicados, claves foráneas rotas y números negativos.
   - Incluye **Laboratorio de Resiliencia** para inyectar anomalías de prueba en vivo (FK rota, stock negativo, ID duplicado) y restaurar al estado 100% íntegro.

4. **Pipeline ETL (Extract, Transform, Load):**
   - Limpieza de cadenas (`strip`), estandarización ISO 8601 de fechas, normalización de categorías en mayúsculas y desduplicación determinista.

5. **Asistente de Consulta con IA (RAG Local Estricto):**
   - Respuestas exactas basadas exclusivamente en los datos de la empresa.
   - Botones rápidos para las 5 preguntas clave de evaluación:
     a) *"¿Cuál es la compra sugerida para la pulpa de mango?"* → **340.0 kg**
     b) *"¿Cuánto stock de producto terminado tenemos de jugo de maracuyá?"* → **120 unidades**
     c) *"¿Cuáles son los productos con riesgo de desabastecimiento de materia prima?"* → **Pulpa de mango (340 kg) y Jugo de maracuyá (280 kg)**
     d) *"¿Cuántas unidades en total se deben producir con el aumento del 30%?"* → **2,730 unidades**
     e) *"¿Cuál es el cliente con más pedidos registrados?"* → **Supermercados El Litoral S.A.C. (3 pedidos)**
   - Soporte estricto de fallback ante preguntas externas: *"No dispongo de datos en el sistema para responder esa consulta"*.

6. **Simulador de Integración ERP (Odoo v17):**
   - Endpoint `/api/erp/sync` que genera el payload JSON-RPC `purchase.order` con las compras sugeridas y retorna acuse de recibo HTTP 201 (`PO-2026-0042`).
