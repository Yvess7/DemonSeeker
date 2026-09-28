"""
Compatibility redirect: Watchdog Sentinel is now DemonEye Sentinel.
"""
from monitor.demon_eye import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("monitor.demon_eye:app", host="127.0.0.1", port=8001, reload=False, log_level="warning")
