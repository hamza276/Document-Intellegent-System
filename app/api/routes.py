from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas import (
    UploadResponse,
    AsyncUploadResponse,
    TaskStatusResponse,
    TaskStatus,
    QueryRequest,
    QueryResponse,
    HealthResponse,
    DocumentListResponse,
    DocumentInfo
)
from app.core.orchestrator import Orchestrator
from app.core.config import settings
from app.core.cache import cache_manager, generate_cache_key
from app.core.task_queue import get_task_queue
import shutil
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
orchestrator = Orchestrator()

SUPPORTED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp'}


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def process_upload_task(file_path: str) -> dict:
    """Background task for processing uploads."""
    return orchestrator.handle_upload(file_path)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    redis_connected = False
    if settings.REDIS_URL:
        try:
            import redis
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            redis_connected = True
        except Exception:
            pass
    
    return HealthResponse(
        status="healthy",
        message="Document Intelligence Backend is running",
        cache_enabled=settings.CACHE_ENABLED,
        async_enabled=settings.ASYNC_PROCESSING,
        redis_connected=redis_connected
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    documents = []
    storage_dir = settings.STORAGE_DIR
    
    if os.path.exists(storage_dir):
        for filename in os.listdir(storage_dir):
            file_path = os.path.join(storage_dir, filename)
            if os.path.isfile(file_path) and not filename.startswith('.'):
                ext = get_file_extension(filename)
                if ext in SUPPORTED_EXTENSIONS:
                    file_size = os.path.getsize(file_path)
                    documents.append(DocumentInfo(
                        filename=filename,
                        file_type="pdf" if ext == '.pdf' else "image",
                        size_bytes=file_size
                    ))
    
    return DocumentListResponse(documents=documents, total=len(documents))


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Synchronous document upload and processing."""
    file_ext = get_file_extension(file.filename)
    
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    
    file_location = os.path.join(settings.STORAGE_DIR, file.filename)
    
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        result = orchestrator.handle_upload(file_location)
        
        return UploadResponse(
            filename=result["filename"],
            message=f"Successfully processed and indexed ({result.get('file_type', 'document')}).",
            num_pages=result.get("pages", 1),
            doc_id=result["filename"],
            file_type=result.get("file_type", "unknown"),
            chunks_indexed=result.get("chunks_indexed", 0)
        )
        
    except ValueError as e:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/async", response_model=AsyncUploadResponse)
async def upload_document_async(file: UploadFile = File(...)):
    """Asynchronous document upload - returns task ID for status polling."""
    file_ext = get_file_extension(file.filename)
    
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    
    file_location = os.path.join(settings.STORAGE_DIR, file.filename)
    
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        task_queue = get_task_queue()
        task_id = task_queue.submit(process_upload_task, file_location)
        
        logger.info(f"Async upload started: {file.filename} -> Task: {task_id}")
        
        return AsyncUploadResponse(
            task_id=task_id,
            filename=file.filename,
            status=TaskStatus.PENDING,
            message="Document upload started. Poll /api/tasks/{task_id} for status."
        )
        
    except Exception as e:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get status of an async processing task."""
    task_queue = get_task_queue()
    status = task_queue.get_task_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatusResponse(
        task_id=status.get("id", task_id),
        status=TaskStatus(status.get("status", "pending")),
        created_at=float(status.get("created_at", 0)),
        updated_at=float(status.get("updated_at", 0)),
        result=status.get("result"),
        error=status.get("error")
    )


@router.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """Ask a question with optional caching."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    cached = False
    cache_key = None
    
    if settings.CACHE_ENABLED:
        cache_key = f"qa:{generate_cache_key(request.query)}"
        cached_result = cache_manager.cache.get(cache_key)
        
        if cached_result:
            logger.info(f"Cache hit for query: {request.query[:50]}...")
            return QueryResponse(
                answer=cached_result["answer"],
                sources=cached_result["sources"],
                cached=True
            )
    
    try:
        result = orchestrator.handle_query(request.query)
        
        if settings.CACHE_ENABLED and cache_key:
            cache_manager.cache.set(cache_key, result, settings.CACHE_TTL)
            logger.info(f"Cached query result: {request.query[:50]}...")
        
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            cached=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Delete a document from storage."""
    file_path = os.path.join(settings.STORAGE_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        os.remove(file_path)
        return {"message": f"Document '{filename}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache")
async def clear_cache():
    """Clear the query cache."""
    if not settings.CACHE_ENABLED:
        raise HTTPException(status_code=400, detail="Caching is not enabled")
    
    cache_manager.cache.clear()
    return {"message": "Cache cleared successfully"}
