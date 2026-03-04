from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import setup_logging
from app.models.db import ensure_tables


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    ensure_tables()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="KB Server",
        version="0.1.0",
        lifespan=lifespan,
    )

    from app.api.routes.health import router as health_router
    from app.api.routes.notes import router as notes_router
    from app.api.routes.publish import router as publish_router

    app.include_router(health_router)
    app.include_router(notes_router)
    app.include_router(publish_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )
