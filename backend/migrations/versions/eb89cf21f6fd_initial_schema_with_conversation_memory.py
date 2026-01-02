"""Initial schema with conversation memory

Revision ID: eb89cf21f6fd
Revises: 
Create Date: 2026-01-02 18:20:46.840138

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb89cf21f6fd'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create slack_messages table
    op.create_table(
        'slack_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('channel_id', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.String(), nullable=False),
        sa.Column('msg_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_slack_messages_channel_id'), 'slack_messages', ['channel_id'])
    op.create_index(op.f('ix_slack_messages_user_id'), 'slack_messages', ['user_id'])
    
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('doc_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create conversation_history table
    op.create_table(
        'conversation_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('message_ts', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversation_history_conversation_id'), 'conversation_history', ['conversation_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_conversation_history_conversation_id'), table_name='conversation_history')
    op.drop_table('conversation_history')
    op.drop_table('documents')
    op.drop_index(op.f('ix_slack_messages_user_id'), table_name='slack_messages')
    op.drop_index(op.f('ix_slack_messages_channel_id'), table_name='slack_messages')
    op.drop_table('slack_messages')
