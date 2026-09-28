import asyncio
import os
import sys
import time
import random
import subprocess
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

TARGET_URL = "http://127.0.0.1:8000/api/health"
KILL_URL = "http://127.0.0.1:8000/api/crash"
CHECK_INTERVAL_SECONDS = 1.8
MAX_HISTORY_LEN = 30
RESTART_DELAY_SECONDS = 10  # Delay real antes de resucitar el proceso

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")

venv_py = os.path.join(PROJECT_DIR, "venv", "bin", "python3")
PYTHON_EXEC = venv_py if os.path.exists(venv_py) else sys.executable

app = FastAPI(
    title="DemonSeeker DemonEye Sentinel",
    description="Supervisor independiente con reinicio real de proceso y delay configurable",
    version="2.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

backend_process: Optional[subprocess.Popen] = None
is_restarting_lock = False

demoneye_state: Dict[str, Any] = {
    "supervisor_name": "DemonEye",
    "status": "INITIALIZING",
    "backend_pid": None,
    "target_url": TARGET_URL,
    "last_check_time": None,
    "last_latency_ms": None,
    "average_latency_ms": None,
    "total_checks": 0,
    "successful_checks": 0,
    "failed_checks": 0,
    "auto_restarts_count": 0,
    "consecutive_failures": 0,
    "uptime_pct": 100.0,
    "random_chaos_enabled": True,
    "restart_delay_seconds": RESTART_DELAY_SECONDS,
    "restart_countdown": None,
    "history": [],
    "incidents": [],
    "current_outage": None,
}

def log_event(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [DEMONEYE {level}] {message}")

def spawn_backend_process() -> subprocess.Popen:
    global backend_process
    log_event("Ejecutando inicio de proceso backend uvicorn...", "INFO")
    proc = subprocess.Popen(
        [PYTHON_EXEC, "-m", "uvicorn", "backend.app:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=PROJECT_DIR,
    )
    backend_process = proc
    demoneye_state["backend_pid"] = proc.pid
    log_event(f"Proceso backend iniciado con PID: {proc.pid}", "OK")
    return proc

async def real_process_restart():
    """
    Mata restos del proceso y espera RESTART_DELAY_SECONDS de verdad 
    antes de resucitar el backend. El puerto 8000 permanece muerto todo ese tiempo.
    """
    global backend_process, is_restarting_lock
    if is_restarting_lock:
        return
    is_restarting_lock = True

    try:
        delay = demoneye_state["restart_delay_seconds"]
        
        # Kill zombie if hanging
        if backend_process and backend_process.poll() is None:
            try:
                backend_process.kill()
                backend_process.wait(timeout=1.0)
            except Exception:
                pass

        log_event(f"PROCESO MUERTO. Esperando {delay} segundos antes de resucitar...", "WARN")
        
        # Real countdown visible from the UI
        for remaining in range(delay, 0, -1):
            demoneye_state["restart_countdown"] = remaining
            log_event(f"Reinicio en {remaining}s...", "WARN")
            await asyncio.sleep(1.0)
        
        demoneye_state["restart_countdown"] = 0
        log_event("Levantando nuevo proceso backend...", "INFO")
        
        new_proc = spawn_backend_process()
        demoneye_state["auto_restarts_count"] += 1

        # Wait until port 8000 actually responds
        for _ in range(30):
            await asyncio.sleep(0.3)
            try:
                async with httpx.AsyncClient(timeout=1.0, trust_env=False) as client:
                    r = await client.get(TARGET_URL)
                    if r.status_code == 200:
                        log_event(
                            f"Backend resucitado (PID: {new_proc.pid}). "
                            f"Total resurrecciones: {demoneye_state['auto_restarts_count']}",
                            "OK"
                        )
                        demoneye_state["restart_countdown"] = None
                        break
            except Exception:
                pass
    finally:
        is_restarting_lock = False

async def perform_health_check() -> Dict[str, Any]:
    global backend_process
    start_time = time.perf_counter()
    check_entry: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status_code": None,
        "latency_ms": 0.0,
        "status": "UNKNOWN",
        "error": None,
    }

    is_process_dead = backend_process is not None and backend_process.poll() is not None

    try:
        if is_process_dead:
            raise httpx.RequestError(
                f"Proceso terminado (exit code {backend_process.poll()})"
            )
        async with httpx.AsyncClient(timeout=1.5, trust_env=False) as client:
            resp = await client.get(TARGET_URL)
            latency = (time.perf_counter() - start_time) * 1000
            check_entry["latency_ms"] = round(latency, 2)
            check_entry["status_code"] = resp.status_code

            if resp.status_code == 200:
                check_entry["status"] = "HEALTHY"
                data = resp.json()
                demoneye_state["backend_pid"] = data.get("pid", demoneye_state["backend_pid"])
            else:
                check_entry["status"] = "OUTAGE"
                check_entry["error"] = f"HTTP {resp.status_code}"
    except Exception:
        latency = (time.perf_counter() - start_time) * 1000
        check_entry["latency_ms"] = round(latency, 2)
        check_entry["status"] = "DOWN"
        check_entry["error"] = "Proceso caido / Conexion rechazada"

    demoneye_state["total_checks"] += 1
    demoneye_state["last_check_time"] = check_entry["timestamp"]
    demoneye_state["last_latency_ms"] = check_entry["latency_ms"]

    if check_entry["status"] == "HEALTHY":
        demoneye_state["successful_checks"] += 1
        demoneye_state["status"] = "HEALTHY"
        demoneye_state["consecutive_failures"] = 0

        if demoneye_state["current_outage"]:
            outage = demoneye_state["current_outage"]
            dur = round(time.time() - outage["started_epoch"], 1)
            outage["resolved_at"] = check_entry["timestamp"]
            outage["duration_seconds"] = dur
            outage["status"] = "RESOLVED"
            outage["resolution"] = f"Resucitado con nuevo PID {demoneye_state['backend_pid']}"
            demoneye_state["incidents"].insert(0, outage)
            demoneye_state["current_outage"] = None
            log_event(f"Incidente cerrado. Backend caido {dur}s, ahora operativo.", "OK")
    else:
        demoneye_state["failed_checks"] += 1
        demoneye_state["consecutive_failures"] += 1
        demoneye_state["status"] = "CRITICAL_OUTAGE"

        if not demoneye_state["current_outage"]:
            demoneye_state["current_outage"] = {
                "id": f"INC-{len(demoneye_state['incidents']) + 1:03d}",
                "started_at": check_entry["timestamp"],
                "started_epoch": time.time(),
                "resolved_at": None,
                "error": check_entry["error"],
                "status": "RESTARTING",
            }
            log_event(
                f"CAIDA REAL DETECTADA ({check_entry['error']}). "
                f"Reinicio programado en {demoneye_state['restart_delay_seconds']}s...",
                "ALERT"
            )
            asyncio.create_task(real_process_restart())

    if demoneye_state["total_checks"] > 0:
        demoneye_state["uptime_pct"] = round(
            (demoneye_state["successful_checks"] / demoneye_state["total_checks"]) * 100, 2
        )

    demoneye_state["history"].append(check_entry)
    if len(demoneye_state["history"]) > MAX_HISTORY_LEN:
        demoneye_state["history"].pop(0)

    healthy_pings = [h["latency_ms"] for h in demoneye_state["history"] if h["status"] == "HEALTHY"]
    if healthy_pings:
        demoneye_state["average_latency_ms"] = round(sum(healthy_pings) / len(healthy_pings), 1)

    return check_entry

async def monitor_loop():
    log_event(f"DemonEye activado. Vigilando: {TARGET_URL}", "INFO")

    # Spawn backend on first launch if not already running
    try:
        async with httpx.AsyncClient(timeout=1.0, trust_env=False) as client:
            await client.get(TARGET_URL)
    except Exception:
        log_event("Backend no detectado al arrancar. Levantando proceso...", "WARN")
        spawn_backend_process()

    while True:
        try:
            await perform_health_check()
        except Exception as e:
            log_event(f"Error en loop: {e}", "ALERT")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)

async def spontaneous_chaos_loop():
    """Mata el backend de verdad cada 50-85s si el modo random está activo."""
    await asyncio.sleep(30)
    while True:
        await asyncio.sleep(random.randint(50, 85))
        if demoneye_state["random_chaos_enabled"] and demoneye_state["status"] == "HEALTHY":
            log_event("CHAOS RANDOM: Matando proceso del backend para probar resurrección real...", "WARN")
            await force_kill_backend("Caida espontanea aleatoria")

async def force_kill_backend(reason: str = "Caida forzada a proposito"):
    global backend_process
    log_event(f"Ejecutando kill: {reason}", "ALERT")

    # Try HTTP suicide
    try:
        async with httpx.AsyncClient(timeout=1.0, trust_env=False) as client:
            await client.post(KILL_URL, json={"reason": reason})
    except Exception:
        pass

    # Kill process handle directly as fallback
    if backend_process and backend_process.poll() is None:
        try:
            backend_process.terminate()
        except Exception:
            pass

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(monitor_loop())
    asyncio.create_task(spontaneous_chaos_loop())

# ----------------- API ENDPOINTS -----------------

@app.get("/status")
def get_status():
    return demoneye_state

@app.get("/incidents")
def get_incidents():
    incidents = list(demoneye_state["incidents"])
    if demoneye_state["current_outage"]:
        incidents.insert(0, demoneye_state["current_outage"])
    return incidents

@app.post("/force-crash")
async def trigger_force_crash():
    await force_kill_backend("Caida forzada a proposito desde la interfaz")
    asyncio.create_task(perform_health_check())
    return {"message": "Proceso del backend terminado. Reinicio en curso con delay.", "delay": demoneye_state["restart_delay_seconds"]}

@app.post("/toggle-chaos")
def toggle_chaos():
    demoneye_state["random_chaos_enabled"] = not demoneye_state["random_chaos_enabled"]
    return {"random_chaos_enabled": demoneye_state["random_chaos_enabled"]}

@app.post("/set-delay")
def set_delay(seconds: int = 10):
    clamped = max(3, min(seconds, 60))
    demoneye_state["restart_delay_seconds"] = clamped
    return {"restart_delay_seconds": clamped}

# Serve the status page and shared CSS from DemonEye's own port (8001)
# so it stays alive even when port 8000 is dead.
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    print("-" * 65)
    print("DEMONSEEKER - DEMONEYE SENTINEL")
    print("-" * 65)
    uvicorn.run("monitor.demon_eye:app", host="127.0.0.1", port=8001, reload=False, log_level="warning")
