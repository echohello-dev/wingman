"""
Configuration management for Wingman backend
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Wingman"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Slack Configuration
    SLACK_BOT_TOKEN: str  # xoxb-* token
    SLACK_APP_TOKEN: Optional[str] = None  # xapp-* token for Socket Mode
    SLACK_SIGNING_SECRET: str
    SLACK_USER_TOKEN: Optional[str] = None  # xoxp-* token for user actions
    SLACK_CLIENT_ID: Optional[str] = None
    SLACK_CLIENT_SECRET: Optional[str] = None
    
    # OpenRouter/OpenAI Configuration
    OPENROUTER_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "openai/gpt-4-turbo-preview"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000
    
    # Database
    DATABASE_URL: str = "postgresql://wingman:wingman@localhost:5432/wingman"
    
    # Chroma Vector Store
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION: str = "slack_messages"
    
    # RAG Configuration
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    RETRIEVAL_TOP_K: int = 5
    
    # Conversation Memory
    CONVERSATION_MEMORY_WINDOW: int = 10  # Number of recent messages to include
    CONVERSATION_TIMEOUT_MINUTES: int = 30  # How long to consider a conversation active
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
