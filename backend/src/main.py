import uvicorn

from core import settings


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.app_settings.app_host,
        port=settings.app_settings.app_port,
        reload=settings.DEBUG,
    )
