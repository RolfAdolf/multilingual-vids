import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.logging_config import setup_logging
from core.settings import app_settings
from database import create_tables
from video_tasks.api.router import router as videos_router


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app_ = FastAPI(title="Multilingual Videos API")
    app_.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.parsed_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app_.include_router(videos_router)
    return app_


app = create_app()


@app.on_event("startup")
async def startup() -> None:
    await setup_logging()
    app_settings.storage_dir.mkdir(parents=True, exist_ok=True)
    await create_tables()
