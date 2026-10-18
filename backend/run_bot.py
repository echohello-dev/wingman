"""
Script to run the Slack bot
"""
import logging
from app.logging import configure_logging

configure_logging(service="wingman-bot")
from app.slack_bot import slack_bot
from app.database import init_db

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Initializing Wingman Slack Bot...")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Start the bot
    logger.info("Starting Slack bot...")
    slack_bot.start()
