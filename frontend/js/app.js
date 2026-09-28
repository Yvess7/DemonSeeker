/**
 * DEMONSEEKER // GEOMETRY DASH TOP 50 DEMONS & WATCHDOG INTERFACE
 */

// API Endpoints
const BACKEND_URL = window.location.port === "8000" || window.location.port === "" 
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : "http://127.0.0.1:8000";

const WATCHDOG_URL = "http://127.0.0.1:8001";

// Global App State
const state = {
  demons: [],
  searchQuery: "",
  backendOnline: false,
  watchdogOnline: false,
  soundEnabled: true,
};

// Web Audio API Alert Synthesizer
class AudioAlertSynth {
  constructor() {
    this.ctx = null;
  }

  init() {
    if (!this.ctx && (window.AudioContext || window.webkitAudioContext)) {
      this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    }
  }

  playAlert(type = "outage") {
    if (!state.soundEnabled) return;
    try {
      this.init();
      if (!this.ctx) return;
      if (this.ctx.state === "suspended") this.ctx.resume();

      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.connect(gain);
      gain.connect(this.ctx.destination);

      const now = this.ctx.currentTime;
      if (type === "outage") {
        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.exponentialRampToValueAtTime(140, now + 0.35);
        gain.gain.setValueAtTime(0.18, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.35);
        osc.start(now);
        osc.stop(now + 0.35);
      } else if (type === "recovered") {
        osc.type = "sine";
        osc.frequency.setValueAtTime(523.25, now);
        osc.frequency.setValueAtTime(659.25, now + 0.1);
        osc.frequency.setValueAtTime(783.99, now + 0.2);
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.4);
        osc.start(now);
        osc.stop(now + 0.4);
      }
    } catch (e) {
      console.warn("Audio warning:", e);
    }
  }
}

const audioSynth = new AudioAlertSynth();

// DOM References
const backendPill = document.getElementById("backend-status-pill");
const backendStatusText = document.getElementById("backend-status-text");
const watchdogPill = document.getElementById("watchdog-status-pill");
const watchdogStatusText = document.getElementById("watchdog-status-text");
const watchdogLatencyBadge = document.getElementById("watchdog-latency-badge");

const outageBanner = document.getElementById("outage-alert-banner");
const outageBannerDesc = document.getElementById("outage-banner-desc");
const btnChaosCrash = document.getElementById("btn-chaos-crash");
const btnChaosRestore = document.getElementById("btn-chaos-restore");
const btnBannerRestore = document.getElementById("btn-banner-restore");

const kpiTotalDemons = document.getElementById("kpi-total-demons");
const kpiTop1Name = document.getElementById("kpi-top1-name");
const kpiTop1Creator = document.getElementById("kpi-top1-creator");
const kpiUptimePct = document.getElementById("kpi-uptime-pct");
const kpiTotalChecks = document.getElementById("kpi-total-checks");
const kpiBackendLatency = document.getElementById("kpi-backend-latency");

const demonsContainer = document.getElementById("demons-container");
const entitiesBadgeCount = document.getElementById("entities-badge-count");
const inputSearch = document.getElementById("input-search");

const sentinelStateTag = document.getElementById("sentinel-state-tag");
const sentinelLatency = document.getElementById("sentinel-latency");
const pingBarsContainer = document.getElementById("ping-bars-container");
const incidentsContainer = document.getElementById("incidents-container");
const sentinelTerminalLog = document.getElementById("sentinel-terminal-log");

const btnSoundToggle = document.getElementById("btn-sound-toggle");
const btnPingNow = document.getElementById("btn-ping-now");

// Terminal Logger
function appendLog(message, type = "info") {
  const line = document.createElement("div");
  const timeStr = new Date().toTimeString().split(" ")[0];
  line.className = `term-line ${type}`;
  line.textContent = `[${timeStr}] [WATCHDOG] ${message}`;
  sentinelTerminalLog.appendChild(line);
  sentinelTerminalLog.scrollTop = sentinelTerminalLog.scrollHeight;

  while (sentinelTerminalLog.children.length > 50) {
    sentinelTerminalLog.removeChild(sentinelTerminalLog.firstChild);
  }
}

// ----------------- BACKEND SYNC -----------------

async function fetchBackendData() {
  const startT = performance.now();
  try {
    const healthRes = await fetch(`${BACKEND_URL}/api/health`, { signal: AbortSignal.timeout(2000) });
    const latency = Math.round(performance.now() - startT);
    kpiBackendLatency.textContent = `${latency} ms`;

    if (healthRes.ok) {
      setBackendState(true);

      const [demonsRes, statsRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/demons?limit=50`),
        fetch(`${BACKEND_URL}/api/stats`),
      ]);

      if (demonsRes.ok && statsRes.ok) {
        state.demons = await demonsRes.json();
        const stats = await statsRes.json();
        renderStats(stats);
        renderDemons();
      }
    } else {
      const err = await healthRes.json().catch(() => ({}));
      setBackendState(false, err.error || `HTTP ${healthRes.status}`);
    }
  } catch (err) {
    setBackendState(false, "Conexión rechazada o timeout");
  }
}

function setBackendState(isOnline, reason = "") {
  const wasOnline = state.backendOnline;
  state.backendOnline = isOnline;

  if (isOnline) {
    backendPill.className = "status-pill";
    backendStatusText.textContent = "ONLINE (8000)";
    outageBanner.classList.add("hidden");
    btnChaosCrash.classList.remove("hidden");
    btnChaosRestore.classList.add("hidden");

    if (!wasOnline && wasOnline !== null) {
      appendLog("API Backend restablecida y funcionando correctamente.", "ok");
      audioSynth.playAlert("recovered");
    }
  } else {
    backendPill.className = "status-pill status-error";
    backendStatusText.textContent = "CRÍTICO / CAÍDO";
    outageBanner.classList.remove("hidden");
    outageBannerDesc.textContent = reason 
      ? `Causa detectada: ${reason}. El Watchdog Sentinel registró la caída del API.`
      : "El backend no responde en el puerto 8000. El Watchdog independiente está alertando la falla.";
    btnChaosCrash.classList.add("hidden");
    btnChaosRestore.classList.remove("hidden");

    if (wasOnline) {
      appendLog(`¡ALERTA CRÍTICA! El API principal se ha caído: ${reason}`, "alert");
      audioSynth.playAlert("outage");
    }
  }
}

// ----------------- WATCHDOG SYNC (PORT 8001) -----------------

async function fetchWatchdogData() {
  try {
    const res = await fetch(`${WATCHDOG_URL}/status`, { signal: AbortSignal.timeout(1800) });
    if (!res.ok) throw new Error("Watchdog HTTP error");

    const data = await res.json();
    state.watchdogOnline = true;
    renderWatchdogStatus(data);
  } catch (err) {
    state.watchdogOnline = false;
    watchdogPill.className = "status-pill status-error";
    watchdogStatusText.textContent = "OFFLINE";
    watchdogLatencyBadge.textContent = "N/A";
    sentinelStateTag.textContent = "WATCHDOG DESCONECTADO";
    sentinelStateTag.className = "meta-value status-tag-bad";
  }
}

function renderWatchdogStatus(data) {
  watchdogPill.className = "status-pill";
  watchdogStatusText.textContent = data.status === "HEALTHY" ? "ACTIVO" : data.status;
  
  const curLatency = data.last_latency_ms !== null ? `${data.last_latency_ms} ms` : "--";
  watchdogLatencyBadge.textContent = curLatency;

  sentinelLatency.textContent = curLatency;
  kpiUptimePct.textContent = `${data.uptime_pct}%`;
  kpiTotalChecks.textContent = `${data.total_checks} chequeos (${data.successful_checks} OK / ${data.failed_checks} Fallos)`;

  if (data.status === "HEALTHY") {
    sentinelStateTag.textContent = "OPERATIVO (100%)";
    sentinelStateTag.className = "meta-value status-tag-good";
  } else {
    sentinelStateTag.textContent = `CAÍDA ACTIVA (${data.consecutive_failures}x)`;
    sentinelStateTag.className = "meta-value status-tag-bad";
  }

  // Ping History Bars
  if (data.history && data.history.length > 0) {
    pingBarsContainer.innerHTML = "";
    data.history.forEach((h) => {
      const bar = document.createElement("div");
      bar.className = `ping-bar ${h.status === "HEALTHY" ? "healthy" : "outage"}`;
      
      const heightPct = h.status === "HEALTHY" 
        ? Math.min(Math.max((h.latency_ms / 30) * 100, 20), 95)
        : 100;
      bar.style.height = `${heightPct}%`;
      bar.title = `[${h.timestamp.split("T")[1].slice(0, 8)}] ${h.status} - ${h.latency_ms}ms`;
      pingBarsContainer.appendChild(bar);
    });
  }

  renderIncidents(data.incidents, data.current_outage);
}

function renderIncidents(incidents, currentOutage) {
  const allIncidents = [...incidents];
  if (currentOutage && !allIncidents.find(i => i.id === currentOutage.id)) {
    allIncidents.unshift(currentOutage);
  }

  if (allIncidents.length === 0) {
    incidentsContainer.innerHTML = `
      <div class="empty-state">
        <span class="shield-icon">🛡️</span>
        <p>El servicio API se mantiene sin caídas.</p>
        <small>Presiona "Simular Caída" arriba para comprobar la reacción del supervisor.</small>
      </div>
    `;
    return;
  }

  incidentsContainer.innerHTML = "";
  allIncidents.forEach((inc) => {
    const card = document.createElement("div");
    const isActive = inc.status === "ACTIVE";
    card.className = `incident-card ${isActive ? "active" : "resolved"}`;

    const startTime = inc.started_at ? inc.started_at.split("T")[1].slice(0, 8) : "--";
    const duration = inc.duration_seconds ? `${inc.duration_seconds} seg` : "En curso...";

    card.innerHTML = `
      <div class="incident-info">
        <strong>${inc.id || "INC-999"}: ${inc.error || "Pérdida de respuesta"}</strong>
        <span>Inicio: ${startTime} UTC | Duración: ${duration}</span>
      </div>
      <div class="incident-badge ${isActive ? "active" : "resolved"}">
        ${isActive ? "ACTIVO" : "RESUELTO"}
      </div>
    `;
    incidentsContainer.appendChild(card);
  });
}

// ----------------- RENDER GD DEMONS & STATS -----------------

function renderStats(stats) {
  kpiTotalDemons.textContent = stats.total_demons;
  if (stats.top_1) {
    kpiTop1Name.textContent = stats.top_1.name;
    kpiTop1Creator.textContent = `por ${stats.top_1.creator}`;
  }
}

function renderDemons() {
  let list = state.demons;
  if (state.searchQuery.trim()) {
    const q = state.searchQuery.toLowerCase();
    list = list.filter(d => 
      d.name.toLowerCase().includes(q) || 
      d.creator.toLowerCase().includes(q)
    );
  }

  entitiesBadgeCount.textContent = `${list.length} / 50`;

  if (list.length === 0) {
    demonsContainer.innerHTML = `
      <div class="empty-state">
        <p>No se encontraron demons con el término: "${state.searchQuery}"</p>
      </div>
    `;
    return;
  }

  demonsContainer.innerHTML = "";
  list.forEach(demon => {
    const card = document.createElement("div");
    const topClass = demon.position === 1 ? "top-1" : demon.position === 2 ? "top-2" : demon.position === 3 ? "top-3" : demon.position <= 10 ? "top-10" : "";
    card.className = `gd-demon-card ${topClass}`;

    card.innerHTML = `
      <div class="gd-left">
        <div class="gd-rank-badge">#${demon.position}</div>
        <div class="gd-info">
          <span class="gd-name">${demon.name}</span>
          <span class="gd-creator">por <strong>${demon.creator}</strong></span>
        </div>
      </div>
      <div class="gd-right">
        <span class="gd-tag">Extreme Demon</span>
      </div>
    `;
    demonsContainer.appendChild(card);
  });
}

// ----------------- USER ACTIONS -----------------

async function triggerCrash() {
  try {
    appendLog("SIMULACIÓN DE CAÍDA INICIADA por el usuario...", "alert");
    await fetch(`${BACKEND_URL}/api/chaos/simulate-crash`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason: "Colapso del servicio simulado" }),
    });
    fetchBackendData();
    fetchWatchdogData();
  } catch (err) {
    console.error("Crash error:", err);
  }
}

async function restoreService() {
  try {
    appendLog("RESTAURACIÓN DEL SERVICIO SOLICITADA...", "ok");
    await fetch(`${BACKEND_URL}/api/chaos/restore`, { method: "POST" });
    fetchBackendData();
    fetchWatchdogData();
  } catch (err) {
    console.error("Restore error:", err);
  }
}

async function manualPing() {
  try {
    appendLog("Solicitando verificación inmediata al Watchdog...", "info");
    const res = await fetch(`${WATCHDOG_URL}/ping-now`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      appendLog(`Resultado de ping: ${data.result.status} (${data.result.latency_ms}ms)`, data.result.status === "HEALTHY" ? "ok" : "alert");
      fetchWatchdogData();
    }
  } catch (err) {
    appendLog("Error contactando con el servicio Watchdog.", "alert");
  }
}

// ----------------- LISTENERS -----------------

btnChaosCrash.addEventListener("click", triggerCrash);
btnChaosRestore.addEventListener("click", restoreService);
btnBannerRestore.addEventListener("click", restoreService);
btnPingNow.addEventListener("click", manualPing);

inputSearch.addEventListener("input", (e) => {
  state.searchQuery = e.target.value;
  renderDemons();
});

btnSoundToggle.addEventListener("click", () => {
  state.soundEnabled = !state.soundEnabled;
  btnSoundToggle.innerHTML = state.soundEnabled ? `<span class="icon">🔊</span>` : `<span class="icon">🔇</span>`;
});

// Initial boot
appendLog("DemonSeeker GD Top 50 cargado. Conectando con servicios...", "info");
fetchBackendData();
fetchWatchdogData();

setInterval(fetchBackendData, 2500);
setInterval(fetchWatchdogData, 2000);
