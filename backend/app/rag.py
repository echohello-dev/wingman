"""
RAG (Retrieval Augmented Generation) implementation
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.config import settings
from app.database import ConversationHistory, SessionLocal
from app.vector_store import vector_store
from app import agent_runtime

logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG engine for answering questions based on retrieved context"""
    
    def get_conversation_history(self, conversation_id: str) -> str:
        """
        Retrieve recent conversation history
        
        Args:
            conversation_id: Unique identifier for the conversation
            
        Returns:
            Formatted conversation history string
        """
        try:
            db = SessionLocal()
            
            # Calculate timeout threshold
            timeout_threshold = datetime.utcnow() - timedelta(minutes=settings.CONVERSATION_TIMEOUT_MINUTES)
            
            # Retrieve recent messages in chronological order
            history = db.query(ConversationHistory).filter(
                ConversationHistory.conversation_id == conversation_id,
                ConversationHistory.created_at >= timeout_threshold
            ).order_by(
                ConversationHistory.created_at.asc()
            ).limit(settings.CONVERSATION_MEMORY_WINDOW).all()
            
            db.close()
            
            if not history:
                return ""
            
            # Format history
            formatted_history = "Previous conversation:\n"
            for entry in history:
                role_label = "User" if entry.role == "user" else "Assistant"
                formatted_history += f"{role_label}: {entry.message}\n"
            
            formatted_history += "\n"
            return formatted_history
            
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return ""
    
    def _store_conversation_turn(self, conversation_id: str, user_id: str, channel_id: str, 
                                  role: str, message: str, message_ts: Optional[str] = None):
        """
        Store a conversation turn in the database
        
        Args:
            conversation_id: Unique identifier for the conversation
            user_id: Slack user ID
            channel_id: Slack channel ID
            role: "user" or "assistant"
            message: The message content
            message_ts: Optional Slack timestamp
        """
        try:
            db = SessionLocal()
            
            entry = ConversationHistory(
                conversation_id=conversation_id,
                user_id=user_id,
                channel_id=channel_id,
                role=role,
                message=message,
                message_ts=message_ts
            )
            
            db.add(entry)
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error(f"Error storing conversation turn: {e}")
    
    def _agent_payload(self, question: str, channel_id=None, conversation_id=None,
                       request_id=None, slack=None):
        results = vector_store.similarity_search(question)
        if channel_id:
            results = [r for r in results if r.get("metadata", {}).get("channel_id") == channel_id]
        identifier = request_id or agent_runtime.request_id()
        payload = {
            "request_id": identifier,
            "conversation_id": conversation_id or f"request:{identifier}",
            "question": question,
            "context": "\n\n".join(
                f"From {r['metadata'].get('source', 'unknown')}:\n{r['content']}"
                for r in results
            ),
            "sources": [r["metadata"] for r in results],
        }
        if slack:
            payload["slack"] = slack
        return payload

    def generate_response(self, question: str, channel_id: str = None,
                         conversation_id: Optional[str] = None,
                         user_id: Optional[str] = None,
                         message_ts: Optional[str] = None,
                         request_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve context, then wait for a persisted Pi Durable answer.

        Legacy PostgreSQL history remains available for audit; Pi owns new turns.
        API callers should supply a request ID to retry an interrupted wait safely.
        """
        return agent_runtime.generate(self._agent_payload(
            question, channel_id, conversation_id,
            request_id or (f"slack:{channel_id}:{message_ts}" if message_ts else None),
        ))

    def submit_slack(self, question, channel_id, conversation_id, request_id, thread_ts):
        """Durably enqueue generation and delivery before returning to Slack Bolt."""
        return agent_runtime.submit(self._agent_payload(
            question, channel_id, conversation_id, request_id,
            slack={"channel": channel_id, "thread_ts": thread_ts},
        ))

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
