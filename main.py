from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.middleware.logging import RequestLoggingMiddleware
from app.routers.auth import router as auth_router
from app.routers.monitors import router as monitors_router
from app.services.scheduler import start_scheduler, stop_scheduler


# Setup logging before anything else
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Application startup", extra={"event": "app_startup"})
    
    if settings.scheduler_enabled:
        start_scheduler()
    
    yield
    
    logger.info("Application shutdown", extra={"event": "app_shutdown"})
    
    if settings.scheduler_enabled:
        stop_scheduler()

app = FastAPI(
    title="HushMonitor",
    version="0.1.0",
    lifespan=lifespan,
)


# Middleware for HTTP request logging
app.add_middleware(RequestLoggingMiddleware)


@app.get("/health")
def health_check():
    return {"status": "ok"}


# Auth routes (no auth required)
app.include_router(auth_router)

# Monitor routes (requires auth)
app.include_router(monitors_router)
