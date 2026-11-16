"""
Chroma vector store integration for RAG
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict, Any
from app.config import settings
import logging

logger = logging.getLogger(__name__)


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
            logger.error("Error initializing vector store: %s", e)
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
            logger.error("Error initializing vector store: %s", e)
            raise
    
    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]] = None,
                      *, ids: List[str] = None):
        """Add chunks, replacing existing chunks when stable IDs are supplied."""
        self._ensure_initialized()
        if self.vector_store is None:
            raise RuntimeError("Vector store not initialized")
        
        options = {"ids": ids} if ids is not None else {}
        return self.vector_store.add_texts(texts=texts, metadatas=metadatas, **options)

    def replace_document(self, document_id: int, texts: List[str],
                         metadatas: List[Dict[str, Any]]):
        """Upsert owned chunks before removing obsolete chunks for a saved document.

        Existing chunks are not deleted before the upsert succeeds. Cleanup
        failures propagate so the caller can retry the same stable IDs.
        Unowned legacy chunks and other documents are never removed.
        """
        if not texts:
            raise ValueError("A document must contain at least one chunk")
        self._ensure_initialized()
        if self.vector_store is None:
            raise RuntimeError("Vector store not initialized")

        previous = self.vector_store.get(where={"document_id": document_id}, include=[])
        ids = [f"document:{document_id}:{i}" for i in range(len(texts))]
        owned_metadata = [{**metadata, "document_id": document_id} for metadata in metadatas]
        self.add_documents(texts, owned_metadata, ids=ids)
        obsolete = sorted(set(previous["ids"]) - set(ids))
        if obsolete:
            self.vector_store.delete(ids=obsolete)

    def delete_document(self, document_id: int):
        """Remove only chunks explicitly owned by a saved document.

        Deleting an empty set is safe to retry after a database failure.
        Titles and sources cannot identify ownership of historical chunks.
        """
        self._ensure_initialized()
        if self.vector_store is None:
            raise RuntimeError("Vector store not initialized")
        self.vector_store.delete(where={"document_id": document_id})
    
    def similarity_search(self, query: str, k: int = None, *,
                          channel_id: str = None) -> List[Dict[str, Any]]:
        """Return nearest chunks with raw distances, excluding weak matches if configured.

        Channel scope is applied before top-k. Lower Chroma distances are closer;
        the optional cutoff is inclusive and does not change the ranking.
        """
        self._ensure_initialized()
        if self.vector_store is None:
            raise RuntimeError("Vector store not initialized")
        
        k = k or settings.RETRIEVAL_TOP_K
        search_options = {"filter": {"channel_id": channel_id}} if channel_id else {}
        results = self.vector_store.similarity_search_with_score(query, k=k, **search_options)
        max_distance = settings.RETRIEVAL_MAX_DISTANCE
        
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "distance": float(distance),
            }
            for doc, distance in results
            if max_distance is None or distance <= max_distance
        ]
    
    def delete_collection(self):
        """Delete the collection"""
        self._ensure_initialized()
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception as e:
            logger.error("Error deleting collection: %s", e)


# Global instance
vector_store = VectorStore()
