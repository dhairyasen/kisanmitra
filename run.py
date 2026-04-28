"""
Entry point to run KisanMitra API server.
Run: python run.py
"""
import os
import uvicorn
from config.settings import get_settings

settings = get_settings()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.app_port))
    host = "0.0.0.0"

    print("Starting KisanMitra - Smart Weather Intelligence for Farmers")
    print(f"   Server: http://{host}:{port}")
    print(f"   Docs:   http://localhost:{port}/docs")
    print("   Press Ctrl+C to stop\n")

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )