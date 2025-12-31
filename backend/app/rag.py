"""
RAG (Retrieval Augmented Generation) implementation
"""
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from typing import Dict, Any, List
from app.config import settings
from app.vector_store import vector_store


class RAGEngine:
    """RAG engine for answering questions based on retrieved context"""
    
    def __init__(self):
        """Initialize RAG components"""
        # Initialize LLM
        api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        
        # Use OpenRouter if available, otherwise OpenAI
        if settings.OPENROUTER_API_KEY:
            self.llm = ChatOpenAI(
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                openai_api_key=settings.OPENROUTER_API_KEY,
                openai_api_base="https://openrouter.ai/api/v1"
            )
        else:
            self.llm = ChatOpenAI(
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                openai_api_key=settings.OPENAI_API_KEY
            )
        
        # Define prompt template
        self.prompt_template = PromptTemplate(
            template="""You are Wingman, a helpful Slack support assistant. 
Use the following context from Slack threads and documentation to answer the question.
If you cannot find the answer in the context, say so and provide general guidance.

Context:
{context}

Question: {question}

Answer:""",
            input_variables=["context", "question"]
        )
    
    def generate_response(self, question: str, channel_id: str = None) -> Dict[str, Any]:
        """
        Generate a response using RAG
        
        Args:
            question: The user's question
            channel_id: Optional channel ID to filter context
            
        Returns:
            Dictionary with response and metadata
        """
        # Search for relevant context
        results = vector_store.similarity_search(question)
        
        # Filter by channel if specified
        if channel_id:
            results = [r for r in results if r.get("metadata", {}).get("channel_id") == channel_id]
        
        # Build context from results
        context = "\n\n".join([
            f"From {r['metadata'].get('source', 'unknown')}:\n{r['content']}"
            for r in results
        ])
        
        # Generate response
        prompt = self.prompt_template.format(context=context, question=question)
        response = self.llm.invoke(prompt)
        
        return {
            "answer": response.content,
            "sources": [r["metadata"] for r in results],
            "confidence": "high" if results else "low"
        }
    
    def index_slack_thread(self, messages: List[Dict[str, Any]], channel_id: str):
        """
        Index a Slack thread for retrieval
        
        Args:
            messages: List of message dictionaries
            channel_id: Channel ID where the thread exists
        """
        texts = []
        metadatas = []
        
        for msg in messages:
            texts.append(msg.get("text", ""))
            metadatas.append({
                "source": "slack",
                "channel_id": channel_id,
                "message_ts": msg.get("ts"),
                "user_id": msg.get("user"),
                "thread_ts": msg.get("thread_ts")
            })
        
        if texts:
            vector_store.add_documents(texts, metadatas)
    
    def index_document(self, title: str, content: str, source: str = "docs"):
        """
        Index a document for retrieval
        
        Args:
            title: Document title
            content: Document content
            source: Source of the document
        """
        # Split content into chunks if needed
        chunks = self._split_text(content)
        
        metadatas = [
            {
                "source": source,
                "title": title,
                "chunk": i
            }
            for i in range(len(chunks))
        ]
        
        vector_store.add_documents(chunks, metadatas)
    
    def _split_text(self, text: str) -> List[str]:
        """Simple text splitter"""
        # Simple implementation - split by paragraphs or size
        chunk_size = settings.CHUNK_SIZE
        overlap = settings.CHUNK_OVERLAP
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
        
        return chunks


# Global instance
rag_engine = RAGEngine()
