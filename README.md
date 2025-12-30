# AI-Powered Document Intelligence Backend

A production-ready multi-agent document intelligence system with REST APIs, AI integrations, async processing, caching, and Docker support.

## Features

- Multi-agent architecture (Ingestion, Indexing, QA)
- PDF and Image (OCR) processing
- Vector search with FAISS
- Async background processing
- Redis caching layer
- Docker containerization
- Health monitoring

## System Architecture

```
+------------------------------------------------------------------+
|                      FastAPI Application                          |
+------------------------------------------------------------------+
|                          API Layer                                |
|   POST /upload    POST /upload/async    POST /ask    GET /health |
+------------------------------------------------------------------+
|                        Orchestrator                               |
|                  (Multi-Agent Coordinator)                        |
+------------------------------------------------------------------+
|                      Agent Workflow                               |
|                                                                   |
|   +-------------+    +-------------+    +-------------+          |
|   |  Ingestion  |--->|  Indexing   |    |     QA      |          |
|   |    Agent    |    |    Agent    |    |    Agent    |          |
|   +-------------+    +-------------+    +-------------+          |
|        |                  |                   |                   |
|   PDF/Image          Chunking &          Retrieval &             |
|   Extraction         Embeddings          Generation              |
+------------------------------------------------------------------+
|                     Infrastructure                                |
|   +----------+    +----------+    +----------+    +----------+   |
|   |  Local   |    |  FAISS   |    |  Redis   |    |  OpenAI  |   |
|   | Storage  |    |Vector DB |    |  Cache   |    | GPT-3.5  |   |
|   +----------+    +----------+    +----------+    +----------+   |
+------------------------------------------------------------------+
```

## Agent Responsibilities

### Ingestion Agent
- PDF text extraction using pypdf
- Image OCR using Tesseract
- Metadata extraction

### Indexing Agent
- Recursive text chunking (1000 chars, 100 overlap)
- OpenAI embeddings generation
- FAISS index management

### QA Agent
- Semantic vector search
- RAG-based answer generation
- Source attribution

## API Endpoints

### Health Check
```
GET /api/health

Response:
{
  "status": "healthy",
  "message": "Document Intelligence Backend is running",
  "cache_enabled": true,
  "async_enabled": true,
  "redis_connected": true
}
```

### Upload Document (Sync)
```
POST /api/upload
Content-Type: multipart/form-data
Body: file=<binary>

Response:
{
  "filename": "document.pdf",
  "message": "Successfully processed and indexed (pdf).",
  "num_pages": 5,
  "doc_id": "document.pdf",
  "file_type": "pdf",
  "chunks_indexed": 12
}
```

### Upload Document (Async)
```
POST /api/upload/async
Content-Type: multipart/form-data
Body: file=<binary>

Response:
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "status": "pending",
  "message": "Document upload started. Poll /api/tasks/{task_id} for status."
}
```

### Check Task Status
```
GET /api/tasks/{task_id}

Response:
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": 1703865600.0,
  "updated_at": 1703865605.0,
  "result": {"filename": "document.pdf", "chunks_indexed": 12},
  "error": null
}
```

### Ask Question
```
POST /api/ask
Content-Type: application/json
Body: {"query": "What is the main topic?"}

Response:
{
  "answer": "The main topic is...",
  "sources": ["document.pdf"],
  "cached": false
}
```

### List Documents
```
GET /api/documents

Response:
{
  "documents": [{"filename": "document.pdf", "file_type": "pdf", "size_bytes": 102400}],
  "total": 1
}
```

### Delete Document
```
DELETE /api/documents/{filename}
```

### Clear Cache
```
DELETE /api/cache
```

## Quick Start

### Local Development

```bash
# Clone repository
git clone <repository-url>
cd Client-1

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build and run individually
docker build -t doc-intelligence .
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-xxx doc-intelligence
```

### Docker Services

| Service | Port | Description |
|---------|------|-------------|
| api | 8000 | FastAPI application |
| redis | 6379 | Cache and task queue |
| worker | - | Background processor |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| OPENAI_API_KEY | - | OpenAI API key (required) |
| REDIS_URL | - | Redis connection URL |
| STORAGE_DIR | .storage | File storage directory |
| CACHE_ENABLED | true | Enable query caching |
| CACHE_TTL | 300 | Cache TTL in seconds |
| ASYNC_PROCESSING | true | Enable async uploads |
| MAX_WORKERS | 4 | Thread pool size |
| MAX_FILE_SIZE | 52428800 | Max upload size (50MB) |

## Sample API Calls

### cURL

```bash
# Upload (sync)
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@document.pdf"

# Upload (async)
curl -X POST "http://localhost:8000/api/upload/async" \
  -F "file=@document.pdf"

# Check task status
curl "http://localhost:8000/api/tasks/{task_id}"

# Ask question
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the time constraint?"}'

# Health check
curl "http://localhost:8000/api/health"

# Clear cache
curl -X DELETE "http://localhost:8000/api/cache"
```

### Python

```python
import requests

# Async upload
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/upload/async",
        files={"file": f}
    )
    task_id = response.json()["task_id"]

# Poll for completion
import time
while True:
    status = requests.get(f"http://localhost:8000/api/tasks/{task_id}").json()
    if status["status"] in ["completed", "failed"]:
        break
    time.sleep(1)

# Query with caching
response = requests.post(
    "http://localhost:8000/api/ask",
    json={"query": "What are the main points?"}
)
print(response.json())
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI |
| AI/LLM | OpenAI GPT-3.5, LangChain |
| Vector DB | FAISS |
| Cache | Redis / In-memory |
| Task Queue | ThreadPool / Redis |
| PDF | pypdf |
| OCR | Tesseract |
| Container | Docker |

## Design Decisions

### Async Processing
- ThreadPoolExecutor for local development
- Redis-backed queue for distributed deployment
- Non-blocking file uploads for large documents

### Caching Strategy
- Query results cached with configurable TTL
- In-memory fallback when Redis unavailable
- MD5-based cache key generation

### Multi-Agent Design
- BaseAgent abstract class for extensibility
- Single responsibility per agent
- Orchestrator pattern for workflow coordination

### Scalability Considerations
- Stateless API design
- External cache and queue support
- Docker-ready architecture

## Project Structure

```
Client-1/
├── app/
│   ├── agents/
│   │   ├── base.py          # Abstract agent
│   │   ├── ingestion.py     # Text extraction
│   │   ├── indexing.py      # Vector indexing
│   │   └── qa.py            # Question answering
│   ├── api/
│   │   └── routes.py        # API endpoints
│   ├── core/
│   │   ├── config.py        # Configuration
│   │   ├── orchestrator.py  # Agent coordination
│   │   ├── cache.py         # Caching layer
│   │   └── task_queue.py    # Async processing
│   ├── main.py              # FastAPI app
│   ├── schemas.py           # Pydantic models
│   └── worker.py            # Background worker
├── .storage/                # File storage
├── Dockerfile               # Container config
├── docker-compose.yml       # Multi-service setup
├── requirements.txt         # Dependencies
├── .env.example            # Environment template
└── README.md
```

## Future Improvements

- WebSocket support for real-time processing updates
- Multiple LLM provider support (Anthropic, local models)
- Document versioning and history
- User authentication and multi-tenancy
- Kubernetes deployment manifests
- Prometheus metrics and Grafana dashboards
