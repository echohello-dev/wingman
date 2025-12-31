"""
Slack Bot implementation using Slack Bolt
"""
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from typing import Dict, Any
import logging
from app.config import settings
from app.rag import rag_engine
from app.database import SessionLocal, SlackMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SlackBot:
    """Wingman Slack Bot with RAG capabilities"""
    
    def __init__(self):
        """Initialize Slack Bot"""
        self.app = App(
            token=settings.SLACK_BOT_TOKEN,
            signing_secret=settings.SLACK_SIGNING_SECRET
        )
        self.client = WebClient(token=settings.SLACK_BOT_TOKEN)
        
        # Register event handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register Slack event handlers"""
        
        @self.app.event("app_mention")
        def handle_mention(event, say):
            """Handle @mentions of the bot"""
            logger.info(f"Received mention: {event}")
            
            try:
                # Extract question from message
                text = event.get("text", "")
                # Remove bot mention
                question = text.split(">", 1)[-1].strip()
                
                # Get channel and thread info
                channel_id = event.get("channel")
                thread_ts = event.get("thread_ts") or event.get("ts")
                
                # If in a thread, get thread context
                if thread_ts:
                    thread_messages = self._get_thread_messages(channel_id, thread_ts)
                    # Index thread for context
                    rag_engine.index_slack_thread(thread_messages, channel_id)
                
                # Generate response using RAG
                response = rag_engine.generate_response(question, channel_id)
                
                # Store message in database
                self._store_message(event)
                
                # Reply in thread
                say(
                    text=response["answer"],
                    thread_ts=thread_ts
                )
                
            except Exception as e:
                logger.error(f"Error handling mention: {e}")
                say(
                    text=f"Sorry, I encountered an error: {str(e)}",
                    thread_ts=event.get("thread_ts") or event.get("ts")
                )
        
        @self.app.event("message")
        def handle_message(event, say):
            """Handle direct messages"""
            # Only respond to DMs, not channel messages
            if event.get("channel_type") == "im":
                logger.info(f"Received DM: {event}")
                
                try:
                    question = event.get("text", "")
                    
                    # Generate response
                    response = rag_engine.generate_response(question)
                    
                    # Store message
                    self._store_message(event)
                    
                    # Reply
                    say(text=response["answer"])
                    
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    say(text=f"Sorry, I encountered an error: {str(e)}")
        
        @self.app.command("/wingman")
        def handle_command(ack, command, say):
            """Handle /wingman slash command"""
            ack()
            logger.info(f"Received command: {command}")
            
            try:
                question = command.get("text", "")
                
                if not question:
                    say(text="How can I help you? Please provide a question.")
                    return
                
                # Generate response
                response = rag_engine.generate_response(question)
                
                # Reply
                say(text=response["answer"])
                
            except Exception as e:
                logger.error(f"Error handling command: {e}")
                say(text=f"Sorry, I encountered an error: {str(e)}")
        
        @self.app.event("reaction_added")
        def handle_reaction(event):
            """Handle reactions to learn from user feedback"""
            logger.info(f"Reaction added: {event}")
            # Could use reactions like ✅ or ❌ to train the model
            pass
    
    def _get_thread_messages(self, channel_id: str, thread_ts: str) -> list:
        """Retrieve all messages in a thread"""
        try:
            result = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts
            )
            return result.get("messages", [])
        except Exception as e:
            logger.error(f"Error getting thread messages: {e}")
            return []
    
    def _store_message(self, event: Dict[str, Any]):
        """Store message in database"""
        try:
            db = SessionLocal()
            message = SlackMessage(
                message_ts=event.get("ts"),
                channel_id=event.get("channel"),
                user_id=event.get("user"),
                text=event.get("text"),
                thread_ts=event.get("thread_ts"),
                metadata=event
            )
            db.add(message)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Error storing message: {e}")
    
    def start(self):
        """Start the bot"""
        if settings.SLACK_APP_TOKEN:
            # Use Socket Mode for local development
            logger.info("Starting bot in Socket Mode...")
            handler = SocketModeHandler(self.app, settings.SLACK_APP_TOKEN)
            handler.start()
        else:
            logger.info("Socket Mode not enabled. Use Socket Mode for local development.")
            logger.info("For production, use a web server to handle events.")


# Global bot instance
slack_bot = SlackBot()
