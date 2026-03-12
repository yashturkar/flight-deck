from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.auth import APIKeyMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.models.db import ensure_tables


@asynccontextmanager
async def lifespan(_app: FastAPI):
    import logging
    
    setup_logging()
    ensure_tables()
    
    # Recover any uncommitted changes from previous crash/restart
    from app.services.git_batcher import batcher
    try:
        recovered = batcher.recover_uncommitted()
        if recovered:
            logging.getLogger(__name__).info(
                "Recovered %d uncommitted files from previous session", recovered
            )
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "Failed to recover uncommitted changes: %s", exc
        )
    
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="KB Server",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(APIKeyMiddleware)

    from app.api.routes.health import router as health_router
    from app.api.routes.context import router as context_router
    from app.api.routes.notes import router as notes_router
    from app.api.routes.publish import router as publish_router

    app.include_router(health_router)
    app.include_router(context_router)
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
