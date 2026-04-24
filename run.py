"""
Entry point to run KisanMitra API server.
Run: python run.py
"""
import uvicorn
from config.settings import get_settings

settings = get_settings()

if __name__ == "__main__":
    print("🌾 Starting KisanMitra — Smart Weather Intelligence for Farmers")
    print(f"   Server: http://{settings.app_host}:{settings.app_port}")
    print(f"   Docs:   http://localhost:{settings.app_port}/docs")
    print("   Press Ctrl+C to stop\n")

    uvicorn.run(
        "api.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level="info"
    )
