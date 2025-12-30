import uuid
import time
import json
from enum import Enum
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import threading
import logging

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    id: str
    status: TaskStatus
    created_at: float
    updated_at: float
    result: Optional[Dict] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['status'] = self.status.value
        return data


class TaskQueue:
    """In-memory async task queue with thread pool executor."""
    
    def __init__(self, max_workers: int = 4):
        self._tasks: Dict[str, Task] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.Lock()
        logger.info(f"TaskQueue initialized with {max_workers} workers")
    
    def submit(self, func: Callable, *args, **kwargs) -> str:
        task_id = str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            status=TaskStatus.PENDING,
            created_at=time.time(),
            updated_at=time.time()
        )
        
        with self._lock:
            self._tasks[task_id] = task
        
        self._executor.submit(self._execute_task, task_id, func, *args, **kwargs)
        logger.info(f"Task submitted: {task_id}")
        
        return task_id
    
    def _execute_task(self, task_id: str, func: Callable, *args, **kwargs):
        with self._lock:
            self._tasks[task_id].status = TaskStatus.PROCESSING
            self._tasks[task_id].updated_at = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            with self._lock:
                self._tasks[task_id].status = TaskStatus.COMPLETED
                self._tasks[task_id].result = result
                self._tasks[task_id].updated_at = time.time()
            
            logger.info(f"Task completed: {task_id}")
            
        except Exception as e:
            with self._lock:
                self._tasks[task_id].status = TaskStatus.FAILED
                self._tasks[task_id].error = str(e)
                self._tasks[task_id].updated_at = time.time()
            
            logger.error(f"Task failed: {task_id} - {e}")
    
    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        task = self.get_task(task_id)
        if task:
            return task.to_dict()
        return None
    
    def cleanup_old_tasks(self, max_age: int = 3600):
        current_time = time.time()
        with self._lock:
            to_remove = [
                tid for tid, task in self._tasks.items()
                if current_time - task.created_at > max_age
            ]
            for tid in to_remove:
                del self._tasks[tid]
        logger.info(f"Cleaned up {len(to_remove)} old tasks")


class RedisTaskQueue:
    """Redis-backed task queue for distributed processing."""
    
    def __init__(self, redis_url: str, max_workers: int = 4):
        try:
            import redis
            self._redis = redis.from_url(redis_url)
            self._redis.ping()
            self._executor = ThreadPoolExecutor(max_workers=max_workers)
            logger.info("Redis TaskQueue initialized")
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}")
            self._redis = None
            self._fallback = TaskQueue(max_workers)
    
    def submit(self, func: Callable, *args, **kwargs) -> str:
        if self._redis is None:
            return self._fallback.submit(func, *args, **kwargs)
        
        task_id = str(uuid.uuid4())
        task_data = {
            "id": task_id,
            "status": TaskStatus.PENDING.value,
            "created_at": time.time(),
            "updated_at": time.time(),
            "result": None,
            "error": None
        }
        
        self._redis.hset(f"task:{task_id}", mapping={
            k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            for k, v in task_data.items()
        })
        
        self._executor.submit(self._execute_task, task_id, func, *args, **kwargs)
        return task_id
    
    def _execute_task(self, task_id: str, func: Callable, *args, **kwargs):
        key = f"task:{task_id}"
        self._redis.hset(key, "status", TaskStatus.PROCESSING.value)
        self._redis.hset(key, "updated_at", str(time.time()))
        
        try:
            result = func(*args, **kwargs)
            self._redis.hset(key, "status", TaskStatus.COMPLETED.value)
            self._redis.hset(key, "result", json.dumps(result))
            self._redis.hset(key, "updated_at", str(time.time()))
        except Exception as e:
            self._redis.hset(key, "status", TaskStatus.FAILED.value)
            self._redis.hset(key, "error", str(e))
            self._redis.hset(key, "updated_at", str(time.time()))
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        if self._redis is None:
            return self._fallback.get_task_status(task_id)
        
        key = f"task:{task_id}"
        data = self._redis.hgetall(key)
        if not data:
            return None
        
        return {
            k.decode(): json.loads(v) if k.decode() in ['result'] and v else v.decode()
            for k, v in data.items()
        }


task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    global task_queue
    if task_queue is None:
        task_queue = TaskQueue()
    return task_queue


def initialize_task_queue(redis_url: Optional[str] = None, max_workers: int = 4):
    global task_queue
    if redis_url:
        task_queue = RedisTaskQueue(redis_url, max_workers)
    else:
        task_queue = TaskQueue(max_workers)

