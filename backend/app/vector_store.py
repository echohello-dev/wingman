"""
Chroma vector store integration for RAG
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict, Any
from app.config import settings


class VectorStore:
    """Manages vector storage and retrieval using Chroma"""
    
    def __init__(self):
        """Initialize Chroma client and vector store"""
        self.client = None
        self.embeddings = None
        self.collection_name = settings.CHROMA_COLLECTION
        self.vector_store = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazily initialize the vector store on first use"""
        if self._initialized:
            return
        
        try:
            # Connect to Chroma server
            self.client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT
            )
            
            # Initialize embeddings
            self.embeddings = OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL,
                openai_api_key=settings.OPENAI_API_KEY or settings.OPENROUTER_API_KEY
            )
            
            self._init_vector_store()
            self._initialized = True
        except Exception as e:
            print(f"Error initializing vector store: {e}")
            raise
    
    def _init_vector_store(self):
        """Initialize the vector store"""
        try:
            self.vector_store = Chroma(
                client=self.client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings
            )
        except Exception as e:
            print(f"Error initializing vector store: {e}")
            raise
    
    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]] = None):
        """Add documents to the vector store"""
        self._ensure_initialized()
        if not self.vector_store:
            raise RuntimeError("Vector store not initialized")
        
        return self.vector_store.add_texts(texts=texts, metadatas=metadatas)
    
    def similarity_search(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        self._ensure_initialized()
        if not self.vector_store:
            raise RuntimeError("Vector store not initialized")
        
        k = k or settings.RETRIEVAL_TOP_K
        results = self.vector_store.similarity_search(query, k=k)
        
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in results
        ]
    
    def delete_collection(self):
        """Delete the collection"""
        self._ensure_initialized()
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception as e:
            print(f"Error deleting collection: {e}")


# Global instance
vector_store = VectorStore()
