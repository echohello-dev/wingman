"""
FastAPI main application
"""
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, StringConstraints
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
import logging

from app.config import settings
from app.logging import configure_logging
from app.logging_config import WideEventMiddleware

configure_logging(service="wingman-backend")

from app.database import ConversationHistory, get_db, init_db, SlackMessage, Document
from app.rag import rag_engine
from app.slack_bot import slack_bot
from app.vector_store import vector_store

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Slack Support Assistant with RAG capabilities"
)

app.add_middleware(WideEventMiddleware, sample_rate=settings.LOG_WIDE_EVENT_SAMPLE_RATE, slow_ms=settings.LOG_SLOW_MS)

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
    conversation_id: str | None = None
    request_id: str | None = None


class QuestionResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence: str


NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class RetrievalPreviewRequest(BaseModel):
    question: NonBlankString
    channel_id: NonBlankString | None = None


class RetrievedChunk(BaseModel):
    content: str
    metadata: Dict[str, Any]
    distance: float


class RetrievalPreviewResponse(BaseModel):
    question: str
    channel_id: str | None
    top_k: int
    max_distance: float | None
    items: List[RetrievedChunk]


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


class ConversationSummary(BaseModel):
    conversation_id: str
    channel_id: Optional[str] = None
    message_count: int
    first_message_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    last_message_preview: Optional[str] = None


class ConversationListResponse(BaseModel):
    items: List[ConversationSummary]
    total: int
    limit: int
    offset: int


class ConversationTurn(BaseModel):
    id: int
    conversation_id: str
    user_id: Optional[str] = None
    channel_id: Optional[str] = None
    role: str
    message: str
    message_ts: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    conversation_id: str
    items: List[ConversationTurn]
    total: int
    limit: int
    offset: int


class DocumentSummary(BaseModel):
    id: int
    title: str
    source: str
    created_at: Optional[datetime] = None
    content_preview: Optional[str] = None


class DocumentListResponse(BaseModel):
    items: List[DocumentSummary]
    total: int
    limit: int
    offset: int


class DocumentDetail(BaseModel):
    id: int
    title: str
    content: str
    source: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

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
        response = await run_in_threadpool(
            rag_engine.generate_response,
            question=request.question,
            channel_id=request.channel_id,
            conversation_id=request.conversation_id,
            request_id=request.request_id,
        )
        return QuestionResponse(**response)
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/retrieval/preview", response_model=RetrievalPreviewResponse)
def preview_retrieval(request: RetrievalPreviewRequest):
    """Inspect selected chunks and distances without generating an answer."""
    try:
        items = vector_store.similarity_search(
            request.question, channel_id=request.channel_id,
        )
        return RetrievalPreviewResponse(
            question=request.question,
            channel_id=request.channel_id,
            top_k=settings.RETRIEVAL_TOP_K,
            max_distance=settings.RETRIEVAL_MAX_DISTANCE,
            items=items,
        )
    except Exception:
        logger.exception("Retrieval preview failed")
        raise HTTPException(status_code=503, detail="Retrieval is unavailable")


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


@app.get("/api/documents", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    source: str = None,
    db: Session = Depends(get_db),
):
    """List documents in the knowledge base, most recently created first."""
    base = db.query(Document)
    if source:
        base = base.filter(Document.source == source)

    total = base.count()
    documents = (
        base.order_by(Document.created_at.desc(), Document.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = [
        DocumentSummary(
            id=doc.id,
            title=doc.title,
            source=doc.source,
            created_at=doc.created_at,
            content_preview=doc.content[:120] if doc.content else None,
        )
        for doc in documents
    ]
    return DocumentListResponse(items=items, total=total, limit=limit, offset=offset)


@app.get("/api/documents/{document_id}", response_model=DocumentDetail)
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """Return one document with its full content."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


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


@app.get("/api/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    channel_id: str = None,
    db: Session = Depends(get_db),
):
    """List one summary per conversation, most recently active first."""
    base = db.query(ConversationHistory)
    if channel_id:
        base = base.filter(ConversationHistory.channel_id == channel_id)

    total = base.with_entities(
        func.count(func.distinct(ConversationHistory.conversation_id))
    ).scalar() or 0

    rows = (
        base.with_entities(
            ConversationHistory.conversation_id,
            func.max(ConversationHistory.channel_id),
            func.count(ConversationHistory.id),
            func.min(ConversationHistory.created_at),
            func.max(ConversationHistory.created_at),
        )
        .group_by(ConversationHistory.conversation_id)
        .order_by(func.max(ConversationHistory.created_at).desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for conversation_id, row_channel_id, count, first_at, last_at in rows:
        last_row = (
            base.filter(ConversationHistory.conversation_id == conversation_id)
            .order_by(
                ConversationHistory.created_at.desc(), ConversationHistory.id.desc()
            )
            .first()
        )
        preview = None
        if last_row is not None and last_row.message:
            preview = last_row.message[:120]
        items.append(
            ConversationSummary(
                conversation_id=conversation_id,
                channel_id=row_channel_id,
                message_count=count,
                first_message_at=first_at,
                last_message_at=last_at,
                last_message_preview=preview,
            )
        )
    return ConversationListResponse(items=items, total=total, limit=limit, offset=offset)


@app.get("/api/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Return the turns of one conversation in chronological order."""
    total = (
        db.query(ConversationHistory)
        .filter(ConversationHistory.conversation_id == conversation_id)
        .count()
    )
    if total == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    turns = (
        db.query(ConversationHistory)
        .filter(ConversationHistory.conversation_id == conversation_id)
        .order_by(ConversationHistory.created_at.asc(), ConversationHistory.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return ConversationDetailResponse(
        conversation_id=conversation_id,
        items=turns,
        total=total,
        limit=limit,
        offset=offset,
    )


@app.post("/api/index/thread")
async def index_thread(
    channel_id: str,
    thread_ts: str,
    db: Session = Depends(get_db)
):
    """
    Index a saved Slack root message and its replies for retrieval
    """
    try:
        # Slack root events can omit thread_ts, so include the root by its
        # own timestamp. Keep channel scope outside the OR for both paths.
        messages = db.query(SlackMessage).filter(
            SlackMessage.channel_id == channel_id,
            or_(
                SlackMessage.message_ts == thread_ts,
                SlackMessage.thread_ts == thread_ts,
            ),
        ).order_by(SlackMessage.message_ts.asc(), SlackMessage.id.asc()).all()
        
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
    except HTTPException:
        raise
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
