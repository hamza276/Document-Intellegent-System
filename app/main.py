from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.cache import cache_manager
from app.core.task_queue import initialize_task_queue
from app.api.routes import router as api_router
import uvicorn
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Document Intelligence Backend")
    
    cache_manager.initialize(settings.REDIS_URL if settings.REDIS_URL else None)
    logger.info(f"Cache initialized (Redis: {bool(settings.REDIS_URL)})")
    
    initialize_task_queue(
        redis_url=settings.REDIS_URL if settings.REDIS_URL else None,
        max_workers=settings.MAX_WORKERS
    )
    logger.info(f"Task queue initialized (Workers: {settings.MAX_WORKERS})")
    
    yield
    
    logger.info("Shutting down Document Intelligence Backend")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multi-agent document intelligence system with async processing and caching.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api", tags=["Document Intelligence"])


@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": "Document Intelligence Backend",
        "version": "1.0.0",
        "features": {
            "async_processing": settings.ASYNC_PROCESSING,
            "caching": settings.CACHE_ENABLED,
            "redis": bool(settings.REDIS_URL)
        },
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": {
            "upload": "POST /api/upload",
            "upload_async": "POST /api/upload/async",
            "task_status": "GET /api/tasks/{task_id}",
            "ask": "POST /api/ask",
            "documents": "GET /api/documents",
            "health": "GET /api/health"
        }
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
