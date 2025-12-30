from app.agents.base import BaseAgent
from typing import Dict, Any
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings
import os


class IndexingAgent(BaseAgent):
    """
    Agent responsible for text chunking and vector store management.
    Uses FAISS for vector storage and OpenAI for embeddings.
    """
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        self.index_path = os.path.join(settings.STORAGE_DIR, "faiss_index")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=100
        )
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        text = input_data.get('text')
        metadata = input_data.get('metadata')
        
        if not text:
            return {"status": "no_content", "chunks": 0}

        docs = self.text_splitter.create_documents([text], metadatas=[metadata])
        
        if os.path.exists(self.index_path):
            try:
                vectorstore = FAISS.load_local(
                    self.index_path, 
                    self.embeddings, 
                    allow_dangerous_deserialization=True
                )
                vectorstore.add_documents(docs)
            except Exception:
                vectorstore = FAISS.from_documents(docs, self.embeddings)
        else:
            vectorstore = FAISS.from_documents(docs, self.embeddings)
            
        vectorstore.save_local(self.index_path)
        
        return {"status": "success", "chunks": len(docs)}
