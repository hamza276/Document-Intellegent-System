from app.agents.base import BaseAgent
from typing import Dict, Any
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from app.core.config import settings
import os


class QAAgent(BaseAgent):
    """
    Agent responsible for question answering using RAG.
    Retrieves relevant context and generates answers.
    """
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        self.llm = ChatOpenAI(
            temperature=0, 
            openai_api_key=settings.OPENAI_API_KEY, 
            model="gpt-3.5-turbo"
        )
        self.index_path = os.path.join(settings.STORAGE_DIR, "faiss_index")
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        query = input_data.get('query')
        
        if not query:
            return {"answer": "Please provide a question.", "sources": []}
            
        if not os.path.exists(self.index_path):
            return {"answer": "No documents have been indexed yet.", "sources": []}
            
        try:
            vectorstore = FAISS.load_local(
                self.index_path, 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
        except Exception as e:
            return {"answer": f"Error loading index: {str(e)}", "sources": []}
            
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(),
            return_source_documents=True
        )
        
        result = qa_chain.invoke({"query": query})
        
        answer = result.get('result', '')
        source_docs = result.get('source_documents', [])
        sources = list(set([
            doc.metadata.get('source', 'unknown') 
            for doc in source_docs
        ]))
        
        return {"answer": answer, "sources": sources}
