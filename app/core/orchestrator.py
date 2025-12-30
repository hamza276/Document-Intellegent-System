from app.agents.ingestion import IngestionAgent
from app.agents.indexing import IndexingAgent
from app.agents.qa import QAAgent
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Orchestrator:  
    def __init__(self):
        self.ingestion_agent = IngestionAgent()
        self.indexing_agent = IndexingAgent()
        self.qa_agent = QAAgent()
        logger.info("Orchestrator initialized")
        
    def handle_upload(self, file_path: str) -> dict:

        logger.info(f"Processing upload: {file_path}")
        
        ingestion_result = self.ingestion_agent.process({"file_path": file_path})
        logger.info(f"Ingestion complete - Type: {ingestion_result.get('file_type')}, Pages: {ingestion_result.get('pages')}")
        
        indexing_result = self.indexing_agent.process(ingestion_result)
        logger.info(f"Indexing complete - Chunks: {indexing_result.get('chunks')}")
        
        return {
            "filename": os.path.basename(file_path),
            "file_type": ingestion_result.get("file_type", "unknown"),
            "pages": ingestion_result.get("pages", 1),
            "ingestion_status": "success",
            "indexing_status": indexing_result.get("status"),
            "chunks_indexed": indexing_result.get("chunks", 0)
        }

    def handle_query(self, query: str) -> dict:

        logger.info(f"Processing query: {query[:50]}...")
        result = self.qa_agent.process({"query": query})
        logger.info(f"Query complete - Sources: {len(result.get('sources', []))}")
        return result
