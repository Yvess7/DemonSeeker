#!/usr/bin/env python3
"""
DemonSeeker - Master Launcher
Starts DemonEye Sentinel on port 8001, which automatically spawns and manages
the backend process on port 8000 with real process-level auto-restart.
"""

import subprocess
import sys
import time
import os
import signal

def print_banner():
    banner = r"""
  ================================================================================
                            D E M O N   S E E K E R
                  Geometry Dash Extreme Demons // DemonEye Sentinel
  ================================================================================
    """
    print(banner)

def main():
    print_banner()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(project_dir, "venv", "bin", "python3")
    py_exec = venv_python if os.path.exists(venv_python) else sys.executable

    print(f"Python Runtime: {py_exec}")
    print("Iniciando DemonEye Sentinel (Supervisor de Alta Disponibilidad)...")

    # Start DemonEye on port 8001
    demoneye_proc = subprocess.Popen(
        [py_exec, "-m", "uvicorn", "monitor.demon_eye:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd=project_dir,
    )

    time.sleep(1.8)

    print("\n" + "=" * 65)
    print("  INTERFAZ PRINCIPAL:        http://127.0.0.1:8000")
    print("  PANEL DE ESTADO DEMONEYE:  http://127.0.0.1:8000/status.html")
    print("  API DEMONS:                http://127.0.0.1:8000/api/demons")
    print("  API DEMONEYE:              http://127.0.0.1:8001/status")
    print("=" * 65 + "\n")
    print("Presiona Ctrl+C para detener todos los servicios.\n")

    def shutdown(signum, frame):
        print("\nApagando DemonSeeker y DemonEye...")
        demoneye_proc.terminate()
        demoneye_proc.wait()
        print("Servicios detenidos.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while True:
        if demoneye_proc.poll() is not None:
            print("El proceso DemonEye se ha detenido.")
            break
        time.sleep(1)

if __name__ == "__main__":
    main()
