from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadResponse(BaseModel):
    filename: str
    message: str
    num_pages: int
    doc_id: str
    file_type: str = "unknown"
    chunks_indexed: int = 0


class AsyncUploadResponse(BaseModel):
    task_id: str
    filename: str
    status: TaskStatus
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: float
    updated_at: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[str] = []
    cached: bool = False


class HealthResponse(BaseModel):
    status: str
    message: str
    cache_enabled: bool = False
    async_enabled: bool = False
    redis_connected: bool = False


class DocumentInfo(BaseModel):
    filename: str
    file_type: str
    size_bytes: int


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]
    total: int


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
