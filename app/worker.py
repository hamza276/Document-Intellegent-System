"""
Background worker for processing document uploads.
Used in Docker deployment with Redis task queue.
"""
import time
import logging
from app.core.config import settings
from app.core.task_queue import initialize_task_queue, get_task_queue

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_worker():
    logger.info("Starting background worker")
    
    initialize_task_queue(
        redis_url=settings.REDIS_URL if settings.REDIS_URL else None,
        max_workers=settings.MAX_WORKERS
    )
    
    logger.info(f"Worker initialized (Redis: {bool(settings.REDIS_URL)})")
    logger.info(f"Max workers: {settings.MAX_WORKERS}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Worker shutdown requested")


if __name__ == "__main__":
    run_worker()

