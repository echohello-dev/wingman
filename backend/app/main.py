"""
FastAPI main application
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
import logging

from app.config import settings
from app.database import get_db, init_db, SlackMessage, Document
from app.rag import rag_engine
from app.slack_bot import slack_bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Slack Support Assistant with RAG capabilities"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class QuestionRequest(BaseModel):
    question: str
    channel_id: str = None


class QuestionResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence: str


class DocumentRequest(BaseModel):
    title: str
    content: str
    source: str = "api"


class MessageResponse(BaseModel):
    id: int
    message_ts: str
    channel_id: str
    user_id: str
    text: str
    
    class Config:
        from_attributes = True


# Startup/Shutdown Events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Wingman backend...")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Could start Slack bot here if needed
    # Note: For production, run Slack bot as a separate process


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Wingman backend...")


# API Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/api/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question and get an AI-generated response
    """
    try:
        response = rag_engine.generate_response(
            question=request.question,
            channel_id=request.channel_id
        )
        return QuestionResponse(**response)
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/documents")
async def add_document(doc: DocumentRequest, db: Session = Depends(get_db)):
    """
    Add a document to the knowledge base
    """
    try:
        # Store in database
        db_doc = Document(
            title=doc.title,
            content=doc.content,
            source=doc.source
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        
        # Index in vector store
        rag_engine.index_document(doc.title, doc.content, doc.source)
        
        return {
            "id": db_doc.id,
            "message": "Document added successfully"
        }
    except Exception as e:
        logger.error(f"Error adding document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents")
async def list_documents(db: Session = Depends(get_db)):
    """
    List all documents in the knowledge base
    """
    try:
        documents = db.query(Document).all()
        return [
            {
                "id": doc.id,
                "title": doc.title,
                "source": doc.source,
                "created_at": doc.created_at
            }
            for doc in documents
        ]
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/messages", response_model=List[MessageResponse])
async def list_messages(
    limit: int = 100,
    channel_id: str = None,
    db: Session = Depends(get_db)
):
    """
    List recent Slack messages
    """
    try:
        query = db.query(SlackMessage)
        
        if channel_id:
            query = query.filter(SlackMessage.channel_id == channel_id)
        
        messages = query.order_by(SlackMessage.created_at.desc()).limit(limit).all()
        return messages
    except Exception as e:
        logger.error(f"Error listing messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/index/thread")
async def index_thread(
    channel_id: str,
    thread_ts: str,
    db: Session = Depends(get_db)
):
    """
    Index a Slack thread for retrieval
    """
    try:
        # Get messages from database
        messages = db.query(SlackMessage).filter(
            SlackMessage.channel_id == channel_id,
            SlackMessage.thread_ts == thread_ts
        ).all()
        
        if not messages:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Convert to dict format
        message_dicts = [
            {
                "text": msg.text,
                "ts": msg.message_ts,
                "user": msg.user_id,
                "thread_ts": msg.thread_ts
            }
            for msg in messages
        ]
        
        # Index thread
        rag_engine.index_slack_thread(message_dicts, channel_id)
        
        return {
            "message": f"Indexed {len(messages)} messages",
            "thread_ts": thread_ts
        }
    except Exception as e:
        logger.error(f"Error indexing thread: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
