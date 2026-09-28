import os
import sys
import time
import random
import threading
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .mock_data import get_initial_demons

app = FastAPI(
    title="DemonSeeker API",
    description="Geometry Dash Top Extreme Demons & Core API",
    version="2.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVER_START_TIME = time.time()
CURRENT_PID = os.getpid()
demons_database = get_initial_demons()

# ----------------- REAL PROCESS CRASH ENDPOINTS -----------------

@app.post("/api/crash")
@app.post("/api/kill")
def kill_process(reason: Optional[str] = "Caída forzada a propósito por el usuario"):
    """
    Termina el proceso del backend de verdad a nivel de sistema operativo (os._exit).
    El puerto 8000 dejará de responder completamente hasta que DemonEye lo reviva.
    """
    print(f"[BACKEND CRASH] {reason}. Terminando proceso PID {CURRENT_PID} en 100ms...")
    
    def delayed_suicide():
        time.sleep(0.1)
        os._exit(1)

    threading.Thread(target=delayed_suicide, daemon=True).start()
    return {
        "message": "Comando de muerte ejecutado. El proceso del servidor morira de verdad.",
        "pid": CURRENT_PID,
        "reason": reason,
        "timestamp": time.time(),
    }

# ----------------- HEALTH & SYSTEM ENDPOINTS -----------------

@app.get("/api/health")
def get_health():
    uptime = time.time() - SERVER_START_TIME
    return {
        "status": "HEALTHY",
        "service": "DemonSeeker Core Engine",
        "pid": CURRENT_PID,
        "uptime_seconds": round(uptime, 2),
        "total_demons": len(demons_database),
        "timestamp": time.time(),
        "version": "2.2.0",
    }

# ----------------- DEMON DATA ENDPOINTS -----------------

@app.get("/api/demons")
def list_demons(
    search: Optional[str] = Query(None, description="Buscar por nombre o creador"),
    limit: Optional[int] = Query(50, description="Límite de niveles")
):
    results = demons_database
    if search:
        s = search.lower().strip()
        results = [
            d for d in results 
            if s in d.get("name", "").lower() or s in d.get("creator", "").lower()
        ]
    return results[:limit]

@app.get("/api/stats")
def get_stats():
    return {
        "total_demons": len(demons_database),
        "top_1": demons_database[0] if demons_database else None,
        "pid": CURRENT_PID,
        "source": "AREDL",
    }

# ----------------- FRONTEND STATIC SERVING -----------------

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
