/**
 * AGROINDUSTRIAL DEL LITORAL S.A. - FRONTEND SPA
 * Vanilla JavaScript Modular Architecture
 */

// Estado global de la aplicación
const state = {
  usuario: null,
  activeTab: "dashboard",
  mrpFactor: 1.30,
  mrpData: null,
  kpiData: null,
  auditoriaData: null,
  etlData: null,
  chatHistory: []
};

// =============================================================================
// INICIALIZACIÓN Y CICLO DE VIDA
// =============================================================================
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  verificarSesion();
});

function initEventListeners() {
  // Navegación Sidebar
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const tabTarget = btn.getAttribute("data-tab");
      cambiarPestana(tabTarget);
    });
  });

  // Login Form
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", handleLoginSubmit);
  }

  // Logout Button
  const btnLogout = document.getElementById("btnLogout");
  if (btnLogout) {
    btnLogout.addEventListener("click", handleLogout);
  }

  // Chat IA
  const btnEnviarChat = document.getElementById("btnEnviarChat");
  const inputChat = document.getElementById("inputChat");
  if (btnEnviarChat && inputChat) {
    btnEnviarChat.addEventListener("click", enviarPreguntaIA);
    inputChat.addEventListener("keydown", (e) => {
      if (e.key === "Enter") enviarPreguntaIA();
    });
  }

  // Factor MRP Buttons
  document.querySelectorAll(".btn-factor-mrp").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".btn-factor-mrp").forEach(b => b.classList.remove("active", "btn-primary"));
      document.querySelectorAll(".btn-factor-mrp").forEach(b => b.classList.add("btn-secondary"));
      btn.classList.add("active", "btn-primary");
      btn.classList.remove("btn-secondary");
      state.mrpFactor = parseFloat(btn.getAttribute("data-factor"));
      cargarModuloMRP();
    });
  });

  // Subtabs Operativos
  document.querySelectorAll(".subtab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".subtab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const targetSubtab = btn.getAttribute("data-subtab");
      mostrarSubtabOperativo(targetSubtab);
    });
  });
}

// =============================================================================
// NAVEGACIÓN Y TABS
// =============================================================================
function cambiarPestana(tabId) {
  state.activeTab = tabId;

  // Actualizar Sidebar
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
  const activeBtn = document.querySelector(`.nav-btn[data-tab="${tabId}"]`);
  if (activeBtn) activeBtn.classList.add("active");

  // Actualizar Paneles
  document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
  const activePane = document.getElementById(`tab-${tabId}`);
  if (activePane) activePane.classList.add("active");

  // Título Superior
  const pageTitle = document.getElementById("pageTitle");
  const titles = {
    "dashboard": "Dashboard Gerencial & KPIs",
    "mrp": "Planificación y MRP (+30% Demanda)",
    "operativo": "Gestión Operativa (Pedidos e Inventario)",
    "auditoria": "Motor de Validación de Integridad",
    "etl": "Pipeline ETL Empresarial",
    "ia": "Asistente de Consulta Inteligente (RAG)",
    "erp": "Simulador de Integración ERP Odoo"
  };
  if (pageTitle) pageTitle.textContent = titles[tabId] || "Panel de Control";

  // Cargar datos según pestaña
  switch (tabId) {
    case "dashboard":
      cargarDashboardGerencial();
      break;
    case "mrp":
      cargarModuloMRP();
      break;
    case "operativo":
      cargarDatosOperativos();
      break;
    case "auditoria":
      cargarAuditoriaIntegridad();
      break;
    case "etl":
      cargarEstadoETL();
      break;
    case "erp":
      cargarVistaERP();
      break;
  }
}

// =============================================================================
// AUTENTICACIÓN (ADMINISTRADOR / GERENTE)
// =============================================================================
async function verificarSesion() {
  try {
    const res = await fetch("/api/auth/me");
    const data = await res.json();
    if (data.authenticated && data.usuario) {
      aplicarSesionUsuario(data.usuario);
      ocultarModalLogin();
      cambiarPestana("dashboard");
    } else {
      mostrarModalLogin();
    }
  } catch (err) {
    console.error("Error verificando sesión:", err);
    mostrarModalLogin();
  }
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const username = document.getElementById("loginUsername").value.trim();
  const password = document.getElementById("loginPassword").value.trim();

  if (!username || !password) {
    mostrarToast("Por favor ingresa usuario y contraseña.", "warning");
    return;
  }

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();

    if (data.success) {
      aplicarSesionUsuario(data.usuario);
      ocultarModalLogin();
      mostrarToast(`Bienvenido(a), ${data.usuario.nombre}`, "success");
      cambiarPestana("dashboard");
    } else {
      mostrarToast(data.message || "Credenciales incorrectas.", "danger");
    }
  } catch (err) {
    mostrarToast("Error de conexión con el servidor.", "danger");
  }
}

function loginComo(usuario, contrasena) {
  document.getElementById("loginUsername").value = usuario;
  document.getElementById("loginPassword").value = contrasena;
  document.getElementById("loginForm").dispatchEvent(new Event("submit"));
}

async function handleLogout() {
  try {
    await fetch("/api/auth/logout", { method: "POST" });
    state.usuario = null;
    mostrarToast("Sesión finalizada.", "info");
    mostrarModalLogin();
  } catch (err) {
    console.error("Error cerrando sesión:", err);
  }
}

function aplicarSesionUsuario(usr) {
  state.usuario = usr;

  const userAvatar = document.getElementById("userAvatar");
  const userName = document.getElementById("userName");
  const userRole = document.getElementById("userRole");

  if (userAvatar) userAvatar.textContent = usr.nombre.charAt(0);
  if (userName) userName.textContent = usr.nombre;
  if (userRole) userRole.textContent = usr.rol;

  // Ajustar permisos visuales si es Gerente o Admin
  const adminOnlyElements = document.querySelectorAll(".admin-only");
  adminOnlyElements.forEach(el => {
    el.style.display = usr.rol === "ADMINISTRADOR" ? "" : "none";
  });
}

function mostrarModalLogin() {
  const modal = document.getElementById("loginOverlay");
  if (modal) modal.style.display = "flex";
}

function ocultarModalLogin() {
  const modal = document.getElementById("loginOverlay");
  if (modal) modal.style.display = "none";
}

// =============================================================================
// MÓDULO 4: DASHBOARD GERENCIAL (5 KPIS)
// =============================================================================
async function cargarDashboardGerencial() {
  try {
    const res = await fetch("/api/kpis");
    const kpis = await res.json();
    state.kpiData = kpis;

    // 1. Total Pedidos
    document.getElementById("kpi1Valor").textContent = kpis.kpi_1_total_pedidos.valor;
    document.getElementById("kpi1Detalle").textContent = kpis.kpi_1_total_pedidos.detalle;

    // 2. Unidades Totales por Producir (2730)
    document.getElementById("kpi2Valor").textContent = Number(kpis.kpi_2_unidades_producir.valor).toLocaleString();
    document.getElementById("kpi2Detalle").textContent = kpis.kpi_2_unidades_producir.detalle;

    // 3. Materia Prima Total Requerida (4448.0 kg)
    document.getElementById("kpi3Valor").textContent = Number(kpis.kpi_3_mp_requerida.valor).toLocaleString(undefined, { minimumFractionDigits: 1 }) + " kg";
    document.getElementById("kpi3Detalle").textContent = kpis.kpi_3_mp_requerida.detalle;

    // 4. Compras Totales Sugeridas (620.0 kg)
    document.getElementById("kpi4Valor").textContent = Number(kpis.kpi_4_compras_sugeridas.valor).toLocaleString(undefined, { minimumFractionDigits: 1 }) + " kg";
    document.getElementById("kpi4Detalle").textContent = kpis.kpi_4_compras_sugeridas.detalle;

    // 5. Alerta de Productos en Riesgo (2 productos)
    const kpi5 = document.getElementById("kpi5Valor");
    kpi5.textContent = kpis.kpi_5_productos_riesgo.valor;
    document.getElementById("kpi5Detalle").textContent = kpis.kpi_5_productos_riesgo.detalle;

    const cardRiesgo = document.getElementById("cardKpi5");
    if (kpis.kpi_5_productos_riesgo.valor > 0) {
      cardRiesgo.className = "kpi-card danger";
    } else {
      cardRiesgo.className = "kpi-card success";
    }

    // Renderizar tarjetas de resumen por producto base
    await cargarResumenProductosDashboard();
  } catch (err) {
    console.error("Error al cargar KPIs:", err);
  }
}

async function cargarResumenProductosDashboard() {
  const container = document.getElementById("dashboardProductsSummary");
  if (!container) return;

  try {
    const res = await fetch(`/api/mrp?factor=1.30`);
    const mrp = await res.json();

    let html = "";
    mrp.lineas.forEach(p => {
      const badgeRiesgo = p.en_riesgo_desabastecimiento
        ? `<span class="badge badge-danger"><i class="fas fa-exclamation-triangle"></i> Déficit MP: ${p.compra_sugerida_kg.toFixed(1)} kg</span>`
        : `<span class="badge badge-success"><i class="fas fa-check-circle"></i> Stock MP Óptimo</span>`;

      html += `
        <div class="kpi-card ${p.en_riesgo_desabastecimiento ? 'amber' : 'teal'}" style="margin-bottom: 0;">
          <div class="kpi-header">
            <div>
              <span class="kpi-title">${p.categoria}</span>
              <h3 style="font-size: 16px; font-weight: 700; margin-top: 4px;">${p.nombre}</h3>
            </div>
            ${badgeRiesgo}
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 8px; font-size: 12.5px;">
            <div>
              <span style="color: var(--text-muted);">Demanda Actual:</span>
              <strong style="display: block; font-size: 14px;">${p.demanda_actual.toLocaleString()} u</strong>
            </div>
            <div>
              <span style="color: var(--text-muted);">Proyección (+30%):</span>
              <strong style="display: block; font-size: 14px; color: #60a5fa;">${p.demanda_proyectada.toLocaleString()} u</strong>
            </div>
            <div>
              <span style="color: var(--text-muted);">Stock Terminado:</span>
              <strong style="display: block; font-size: 14px;">${p.stock_pt.toLocaleString()} u</strong>
            </div>
            <div>
              <span style="color: var(--text-muted);">Producción Requerida:</span>
              <strong style="display: block; font-size: 14px; color: #a78bfa;">${p.produccion_requerida.toLocaleString()} u</strong>
            </div>
          </div>
          <div style="margin-top: 14px; padding-top: 10px; border-top: 1px solid var(--border-color); font-size: 12px; display: flex; justify-content: space-between;">
            <span>MP Requerida: <strong>${p.mp_requerida_kg.toFixed(1)} kg</strong></span>
            <span>MP Disponible: <strong>${p.mp_disponible_kg.toFixed(1)} kg</strong></span>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  } catch (err) {
    console.error("Error resumen productos:", err);
  }
}

// =============================================================================
// MÓDULO 3: PLANIFICACIÓN Y MRP (+30%)
// [Producto | Demanda Actual | Proyección (+30%) | Stock PT | Producción Requerida | MP/Unidad | MP Req | MP Disp | Compra Sugerida]
// =============================================================================
async function cargarModuloMRP() {
  const tbody = document.getElementById("mrpTableBody");
  const tfoot = document.getElementById("mrpTableFoot");
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 20px;">Calculando plan de producción y requerimientos...</td></tr>`;

  try {
    const res = await fetch(`/api/mrp?factor=${state.mrpFactor}`);
    const mrp = await res.json();
    state.mrpData = mrp;

    let rowsHtml = "";
    mrp.lineas.forEach(p => {
      const riesgoClass = p.en_riesgo_desabastecimiento ? "style='background-color: rgba(239, 68, 68, 0.08); font-weight: 700; color: #f87171;'" : "";
      const alertaBadge = p.en_riesgo_desabastecimiento
        ? `<span class="badge badge-danger">COMPRA OBLIGATORIA</span>`
        : `<span class="badge badge-success">SUFICIENTE</span>`;

      rowsHtml += `
        <tr>
          <td>
            <strong>${p.nombre}</strong><br>
            <small style="color: var(--text-muted);">${p.id_producto} | Insumo: ${p.nombre_materia_prima}</small>
          </td>
          <td style="text-align: right;">${p.demanda_actual.toLocaleString()} u</td>
          <td style="text-align: right; color: #60a5fa; font-weight: 600;">${p.demanda_proyectada.toLocaleString()} u</td>
          <td style="text-align: right;">${p.stock_pt.toLocaleString()} u</td>
          <td style="text-align: right; color: #a78bfa; font-weight: 700;">${p.produccion_requerida.toLocaleString()} u</td>
          <td style="text-align: right;">${p.mp_por_unidad_kg.toFixed(1)} kg/u</td>
          <td style="text-align: right; color: #38bdf8;">${p.mp_requerida_kg.toLocaleString(undefined, {minimumFractionDigits: 1})} kg</td>
          <td style="text-align: right;">${p.mp_disponible_kg.toLocaleString(undefined, {minimumFractionDigits: 1})} kg</td>
          <td style="text-align: right;" ${riesgoClass}>
            ${p.compra_sugerida_kg.toLocaleString(undefined, {minimumFractionDigits: 1})} kg
          </td>
          <td style="text-align: center;">${alertaBadge}</td>
        </tr>
      `;
    });

    tbody.innerHTML = rowsHtml;

    // Totales en pie de tabla
    const tot = mrp.totales;
    tfoot.innerHTML = `
      <tr>
        <th>TOTALES PLANIFICADOS</th>
        <th style="text-align: right;">${tot.demanda_actual.toLocaleString()} u</th>
        <th style="text-align: right; color: #60a5fa;">${tot.demanda_proyectada.toLocaleString()} u</th>
        <th style="text-align: right;">${tot.stock_pt.toLocaleString()} u</th>
        <th style="text-align: right; color: #a78bfa; font-size: 14px;">${tot.produccion_requerida.toLocaleString()} u</th>
        <th style="text-align: right;">-</th>
        <th style="text-align: right; color: #38bdf8; font-size: 14px;">${tot.mp_requerida_kg.toLocaleString(undefined, {minimumFractionDigits: 1})} kg</th>
        <th style="text-align: right;">${tot.mp_disponible_kg.toLocaleString(undefined, {minimumFractionDigits: 1})} kg</th>
        <th style="text-align: right; color: #f87171; font-size: 15px; font-weight: 800;">
          ${tot.compra_sugerida_kg.toLocaleString(undefined, {minimumFractionDigits: 1})} kg
        </th>
        <th style="text-align: center;">
          <span class="badge ${tot.productos_en_riesgo > 0 ? 'badge-danger' : 'badge-success'}">
            ${tot.productos_en_riesgo} en riesgo
          </span>
        </th>
      </tr>
    `;
  } catch (err) {
    console.error("Error cargando MRP:", err);
  }
}

// =============================================================================
// MÓDULO 1: MOTOR DE VALIDACIÓN DE INTEGRIDAD
// Sintaxis, IDs Duplicados, Claves Foráneas y Números Negativos
// =============================================================================
async function cargarAuditoriaIntegridad() {
  const container = document.getElementById("auditoriaResults");
  if (!container) return;

  container.innerHTML = `<div style="text-align:center; padding: 20px;">Ejecutando motor de verificación de integridad referencial...</div>`;

  try {
    const res = await fetch("/api/auditoria");
    const data = await res.json();
    state.auditoriaData = data;

    const esIntegro = data.estado === "INTEGRO";
    const badgeEstado = esIntegro
      ? `<span class="badge badge-success" style="font-size: 14px; padding: 6px 14px;"><i class="fas fa-check-shield"></i> SISTEMA 100% ÍNTEGRO</span>`
      : `<span class="badge badge-danger" style="font-size: 14px; padding: 6px 14px;"><i class="fas fa-exclamation-triangle"></i> ANOMALÍAS DETECTADAS (${data.total_errores})</span>`;

    let html = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
        <div>
          ${badgeEstado}
          <p style="font-size: 12px; color: var(--text-muted); margin-top: 6px;">
            Auditoría completada el: ${new Date(data.fecha_auditoria).toLocaleString()} | Puntaje: <strong>${data.score_integridad}/100</strong>
          </p>
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-secondary btn-sm" onclick="cargarAuditoriaIntegridad()">
            <i class="fas fa-sync-alt"></i> Re-auditar Ahora
          </button>
          <button class="btn btn-success btn-sm" onclick="restaurarIntegridad()">
            <i class="fas fa-undo"></i> Restaurar Integridad
          </button>
        </div>
      </div>
    `;

    if (esIntegro) {
      html += `
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid var(--success-border); border-radius: var(--radius-md); padding: 20px; text-align: center;">
          <i class="fas fa-check-circle" style="font-size: 36px; color: #10b981; margin-bottom: 10px;"></i>
          <h4 style="font-size: 16px; font-weight: 700; color: #34d399;">Consistencia de Datos Verificada Exitosamente</h4>
          <p style="font-size: 13px; color: var(--text-secondary); max-width: 600px; margin: 8px auto 0;">
            No se detectaron errores de sintaxis JSON, todas las claves foráneas (pedidos → clientes/productos) coinciden exactamente, no existen IDs duplicados y todos los valores numéricos son consistentes y no negativos.
          </p>
        </div>
      `;
    } else {
      html += `
        <div style="margin-bottom: 16px;">
          <h4 style="font-size: 14px; font-weight: 700; color: #f87171; margin-bottom: 10px;">
            <i class="fas fa-bug"></i> Lista de Errores e Incoherencias Detectadas:
          </h4>
          <div class="table-responsive">
            <table class="enterprise-table">
              <thead>
                <tr>
                  <th>Severidad</th>
                  <th>Categoría</th>
                  <th>Archivo</th>
                  <th>Identificador</th>
                  <th>Diagnóstico Técnico</th>
                </tr>
              </thead>
              <tbody>
      `;

      data.errores.forEach(err => {
        html += `
          <tr>
            <td><span class="badge badge-danger">${err.severidad}</span></td>
            <td><strong>${err.categoria}</strong></td>
            <td><code>${err.archivo}</code></td>
            <td><code>${err.identificador}</code></td>
            <td style="color: #fca5a5;">${err.mensaje}</td>
          </tr>
        `;
      });

      html += `</tbody></table></div></div>`;
    }

    container.innerHTML = html;
  } catch (err) {
    console.error("Error al cargar auditoría:", err);
  }
}

async function simularIncoherencia(tipo) {
  try {
    const res = await fetch("/api/auditoria/simular-incoherencia", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tipo })
    });
    const data = await res.json();
    mostrarToast(`Anomalía de prueba inyectada: ${tipo}`, "warning");
    cargarAuditoriaIntegridad();
  } catch (err) {
    mostrarToast("Error inyectando anomalía.", "danger");
  }
}

async function restaurarIntegridad() {
  try {
    const res = await fetch("/api/auditoria/restaurar", { method: "POST" });
    const data = await res.json();
    mostrarToast("Integridad del sistema restaurada al 100%.", "success");
    cargarAuditoriaIntegridad();
  } catch (err) {
    mostrarToast("Error al restaurar integridad.", "danger");
  }
}

// =============================================================================
// MÓDULO 2: PIPELINE ETL (Extract, Transform, Load)
// =============================================================================
async function cargarEstadoETL() {
  try {
    const res = await fetch("/api/etl/estado");
    const data = await res.json();
    state.etlData = data;

    document.getElementById("etlUltimaEjecucion").textContent = data.ultima_ejecucion
      ? new Date(data.ultima_ejecucion).toLocaleString()
      : "No disponible";
    document.getElementById("etlDuracion").textContent = `${data.duracion_ms} ms`;
    document.getElementById("etlExtraidos").textContent = data.registros_extraidos;
    document.getElementById("etlCargados").textContent = data.registros_cargados;
    document.getElementById("etlDuplicados").textContent = data.duplicados_descartados;
    document.getElementById("etlNormalizaciones").textContent = data.normalizaciones_aplicadas;
  } catch (err) {
    console.error("Error cargando estado ETL:", err);
  }
}

async function ejecutarETLAhora() {
  const btn = document.getElementById("btnEjecutarETL");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Procesando ETL...`;
  }

  try {
    const res = await fetch("/api/etl/ejecutar", { method: "POST" });
    const data = await res.json();
    mostrarToast("Pipeline ETL ejecutado exitosamente en memoria.", "success");
    cargarEstadoETL();
    cargarDashboardGerencial();
    cargarModuloMRP();
  } catch (err) {
    mostrarToast("Error ejecutando pipeline ETL.", "danger");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fas fa-play"></i> Re-ejecutar Pipeline ETL Ahora`;
    }
  }
}

// =============================================================================
// MÓDULO 5: ASISTENTE DE CONSULTA CON IA (RAG LOCAL ESTRICTO)
// 5 preguntas obligatorias + fallback estricto
// =============================================================================
async function enviarPreguntaIA(textoDirecto = null) {
  const input = document.getElementById("inputChat");
  const pregunta = (typeof textoDirecto === "string" ? textoDirecto : input.value).trim();

  if (!pregunta) return;

  // Agregar mensaje del usuario a la vista
  agregarMensajeChat("user", pregunta);
  if (input) input.value = "";

  // Mostrar mensaje de espera del bot
  const placeholderId = agregarMensajeChat("bot", `<i class="fas fa-circle-notch fa-spin"></i> Consultando base de conocimiento interna...`);

  try {
    const res = await fetch("/api/ia/consulta", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pregunta })
    });
    const data = await res.json();

    // Reemplazar placeholder con la respuesta real
    const elem = document.getElementById(placeholderId);
    if (elem) {
      // Formatear markdown básico (*, **, nuevas líneas)
      const formatted = formatearMarkdown(data.respuesta);
      elem.innerHTML = formatted;
    }
  } catch (err) {
    const elem = document.getElementById(placeholderId);
    if (elem) {
      elem.textContent = "Error al comunicarse con el asistente de IA.";
    }
  }

  // Auto scroll
  const box = document.getElementById("chatMessages");
  if (box) box.scrollTop = box.scrollHeight;
}

function preguntarIA(texto) {
  enviarPreguntaIA(texto);
}

function agregarMensajeChat(tipo, contenido) {
  const box = document.getElementById("chatMessages");
  if (!box) return null;

  const msgId = "msg-" + Date.now() + "-" + Math.floor(Math.random() * 1000);
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${tipo}`;

  const icon = tipo === "bot" ? '<i class="fas fa-robot"></i>' : '<i class="fas fa-user"></i>';
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  msgDiv.innerHTML = `
    <div class="message-avatar">${icon}</div>
    <div class="message-body">
      <div class="message-content" id="${msgId}">${contenido}</div>
      <div class="message-meta" style="${tipo === 'user' ? 'text-align: right;' : ''}">${time}</div>
    </div>
  `;

  box.appendChild(msgDiv);
  box.scrollTop = box.scrollHeight;
  return msgId;
}

function formatearMarkdown(texto) {
  if (!texto) return "";
  let res = texto
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, "<code>$1</code>")
    .replace(/\n\n/g, "<br><br>")
    .replace(/\n/g, "<br>");
  return res;
}

// =============================================================================
// MÓDULO 6: SIMULADOR DE INTEGRACIÓN ERP (ODOO)
// =============================================================================
async function cargarVistaERP() {
  try {
    const res = await fetch("/api/compras");
    const compras = await res.json();

    const tbody = document.getElementById("erpOrdersTableBody");
    if (!tbody) return;

    if (compras.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 20px;">No se han emitido órdenes de compra aún.</td></tr>`;
      return;
    }

    let html = "";
    compras.forEach(c => {
      const lineasTxt = c.lineas ? c.lineas.map(l => `${l.insumo}: ${l.cantidad_kg} kg`).join("<br>") : "-";
      html += `
        <tr>
          <td><strong>${c.id}</strong></td>
          <td><span class="badge badge-primary">${c.odoo_ref || "EN PROCESO"}</span></td>
          <td>${c.nombre_proveedor}</td>
          <td style="font-size: 12px;">${lineasTxt}</td>
          <td style="text-align: right; font-weight: 700;">$${Number(c.total).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
          <td><span class="badge badge-success">${c.estado}</span></td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    console.error("Error cargando compras ERP:", err);
  }
}

async function dispararSincronizacionERP() {
  const modal = document.getElementById("modalERP");
  const modalBody = document.getElementById("modalERPBody");
  if (modal) modal.classList.add("active");

  if (modalBody) {
    modalBody.innerHTML = `
      <div style="text-align:center; padding: 30px;">
        <i class="fas fa-satellite-dish fa-spin" style="font-size: 32px; color: var(--primary); margin-bottom: 12px;"></i>
        <h4 style="font-size: 15px; font-weight: 700;">Conectando con Servidor Odoo ERP (JSON-RPC)...</h4>
        <p style="font-size: 12.5px; color: var(--text-muted); margin-top: 4px;">Empaquetando órdenes de compra sugeridas por MRP (+30%)...</p>
      </div>
    `;
  }

  try {
    const res = await fetch("/api/erp/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });
    const data = await res.json();

    if (modalBody) {
      modalBody.innerHTML = `
        <div style="margin-bottom: 14px; background: rgba(16, 185, 129, 0.1); border: 1px solid var(--success-border); border-radius: var(--radius-md); padding: 12px 16px; display: flex; align-items: center; justify-content: space-between;">
          <div>
            <span class="badge badge-success" style="font-size: 12px;"><i class="fas fa-check-circle"></i> HTTP ${data.codigo_http} OK</span>
            <strong style="margin-left: 8px; color: #34d399;">Orden Creada: ${data.referencia_generada}</strong>
          </div>
          <span style="font-size: 11.5px; color: var(--text-secondary);">Odoo 17.0 Enterprise</span>
        </div>

        <h5 style="font-size: 12.5px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">
          1. Payload JSON Enviado al Web Service de Odoo:
        </h5>
        <div class="code-viewer">${JSON.stringify(data.odoo_request, null, 2)}</div>

        <h5 style="font-size: 12.5px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin: 16px 0 6px;">
          2. Acuse de Recibo Ficticio Retornado por Odoo:
        </h5>
        <div class="code-viewer" style="color: #34d399;">${JSON.stringify(data.odoo_response, null, 2)}</div>
      `;
    }

    mostrarToast(`Orden ${data.referencia_generada} sincronizada con éxito en Odoo ERP.`, "success");
    cargarVistaERP();
  } catch (err) {
    if (modalBody) {
      modalBody.innerHTML = `<div style="color: #f87171; text-align: center; padding: 20px;">Error al conectar con la API de Odoo.</div>`;
    }
  }
}

function cerrarModalERP() {
  const modal = document.getElementById("modalERP");
  if (modal) modal.classList.remove("active");
}

// =============================================================================
// GESTIÓN OPERATIVA (SUBTABS: PEDIDOS, CLIENTES, INVENTARIO, PROVEEDORES)
// =============================================================================
function mostrarSubtabOperativo(subtabId) {
  document.querySelectorAll(".subtab-content").forEach(el => el.style.display = "none");
  const target = document.getElementById(`subtab-${subtabId}`);
  if (target) target.style.display = "block";
}

async function cargarDatosOperativos() {
  await Promise.all([
    cargarTablaPedidos(),
    cargarTablaInventario(),
    cargarTablaClientes(),
    cargarTablaProveedores()
  ]);
}

async function cargarTablaPedidos() {
  const tbody = document.getElementById("pedidosTableBody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/pedidos");
    const pedidos = await res.json();

    let html = "";
    pedidos.forEach(p => {
      const itemsTxt = p.detalle.map(d => `${d.nombre_producto} (${d.cantidad} u @ $${d.precio_unitario})`).join("<br>");
      html += `
        <tr>
          <td><strong>${p.id}</strong></td>
          <td><code>${p.id_cliente}</code></td>
          <td>${new Date(p.fecha).toLocaleDateString()}</td>
          <td style="font-size: 12.5px;">${itemsTxt}</td>
          <td style="text-align: right; font-weight: 700; color: #60a5fa;">$${p.total.toFixed(2)}</td>
          <td><span class="badge ${p.estado === 'ENTREGADO' ? 'badge-success' : 'badge-warning'}">${p.estado}</span></td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    console.error("Error pedidos:", err);
  }
}

async function cargarTablaInventario() {
  const tbody = document.getElementById("inventarioTableBody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/inventario");
    const inv = await res.json();

    let html = "";
    inv.forEach(i => {
      html += `
        <tr>
          <td><strong>${i.nombre_producto}</strong><br><small style="color:var(--text-muted);">${i.id_producto}</small></td>
          <td style="text-align: right; font-weight: 700; font-size: 14px;">${i.stock_pt.toLocaleString()} u</td>
          <td><code>${i.almacen_pt}</code></td>
          <td style="text-align: right; font-weight: 700; font-size: 14px; color: #38bdf8;">${i.mp_disponible_kg.toLocaleString(undefined, {minimumFractionDigits: 1})} kg</td>
          <td><code>${i.almacen_mp}</code></td>
          <td><small style="color:var(--text-muted);">${new Date(i.fecha_actualizacion).toLocaleString()}</small></td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    console.error("Error inventario:", err);
  }
}

async function cargarTablaClientes() {
  const tbody = document.getElementById("clientesTableBody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/clientes");
    const clientes = await res.json();

    let html = "";
    clientes.forEach(c => {
      html += `
        <tr>
          <td><strong>${c.razon_social}</strong><br><small style="color:var(--text-muted);">${c.id}</small></td>
          <td><code>${c.ruc}</code></td>
          <td>${c.ciudad}</td>
          <td>${c.contacto}<br><small style="color:var(--text-muted);">${c.email}</small></td>
          <td><span class="badge badge-primary">${c.categoria}</span></td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    console.error("Error clientes:", err);
  }
}

async function cargarTablaProveedores() {
  const tbody = document.getElementById("proveedoresTableBody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/proveedores");
    const proveedores = await res.json();

    let html = "";
    proveedores.forEach(pr => {
      html += `
        <tr>
          <td><strong>${pr.razon_social}</strong><br><small style="color:var(--text-muted);">${pr.id}</small></td>
          <td>${pr.insumo_principal}</td>
          <td style="text-align: right; font-weight: 700;">$${pr.precio_kg_estimado.toFixed(2)}/kg</td>
          <td>${pr.ciudad}</td>
          <td><span class="badge badge-warning"><i class="fas fa-star"></i> ${pr.calificacion}</span></td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    console.error("Error proveedores:", err);
  }
}

// =============================================================================
// TOAST NOTIFICATIONS
// =============================================================================
function mostrarToast(mensaje, tipo = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${tipo}`;

  const icons = {
    success: "fa-check-circle",
    danger: "fa-times-circle",
    warning: "fa-exclamation-triangle",
    info: "fa-info-circle"
  };

  toast.innerHTML = `
    <i class="fas ${icons[tipo] || 'fa-bell'}"></i>
    <span>${mensaje}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(50px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

