"""
Context Manager Conversation Logging
Handles database operations for logging context manager agent conversations
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import ENUM
from storage.database import Base
from utils.logger import logger


# Define conversation status enum
conversation_status_enum = ENUM(
    'IN_PROGRESS',
    'COMPLETED',
    'FAILED',
    name='ConversationStatus',
    create_type=False
)


class ContextManagerConversation(Base):
    """Model for context manager conversation logs"""
    
    __tablename__ = 'ContextManagerConversation'
    
    id = Column(String, primary_key=True)
    userId = Column(String, nullable=False, index=True)
    conversationId = Column(String, nullable=True, index=True)
    agentName = Column(String, nullable=False, default='context_manager', index=True)
    
    # Message content
    userMessage = Column(Text, nullable=False)
    assistantMessage = Column(Text, nullable=True)
    
    # Tool execution logs
    toolCalls = Column(JSON, nullable=True)  # Array of {name, arguments, timestamp}
    toolResults = Column(JSON, nullable=True)  # Array of {tool_call_id, result, success, timestamp}
    
    # Metadata - using Column with name to avoid conflict with SQLAlchemy's metadata
    meta = Column('metadata', JSON, nullable=True)
    status = Column(conversation_status_enum, nullable=False, default='COMPLETED')
    errorMessage = Column(Text, nullable=True)
    
    # Timestamps
    startedAt = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completedAt = Column(DateTime, nullable=True)
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow)
    updatedAt = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes are defined in columns above using index=True
    __table_args__ = (
        Index('idx_context_manager_userId_startedAt', 'userId', 'startedAt'),
    )


class ContextManagerLogger:
    """Service for logging context manager conversations"""
    
    def __init__(self, db_session):
        """
        Initialize context manager logger
        
        Args:
            db_session: SQLAlchemy async session
        """
        self.db_session = db_session
    
    async def create_log(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
        conversation_link_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new conversation log entry
        
        Args:
            conversation_id: Unique ID for this conversation log
            user_id: User identifier
            user_message: User's message to the context manager
            conversation_link_id: Optional link to parent Conversation table
            metadata: Optional metadata (model, tokens, etc.)
            
        Returns:
            conversation_id: ID of the created log entry
        """
        try:
            log_entry = ContextManagerConversation(
                id=conversation_id,
                userId=user_id,
                conversationId=conversation_link_id,
                agentName='context_manager',
                userMessage=user_message,
                status='IN_PROGRESS',
                meta=metadata,
                startedAt=datetime.utcnow()
            )
            
            self.db_session.add(log_entry)
            await self.db_session.commit()
            
            logger.info(f"Created context manager log: {conversation_id} for user {user_id}")
            return conversation_id
            
        except Exception as e:
            logger.error(f"Error creating context manager log: {e}")
            await self.db_session.rollback()
            raise
    
    async def update_log(
        self,
        conversation_id: str,
        assistant_message: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        status: str = 'COMPLETED',
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Update an existing conversation log
        
        Args:
            conversation_id: ID of the log entry to update
            assistant_message: Assistant's response
            tool_calls: List of tool calls made
            tool_results: List of tool execution results
            status: Conversation status (IN_PROGRESS, COMPLETED, FAILED)
            error_message: Error message if status is FAILED
            metadata: Additional metadata to merge
        """
        try:
            from sqlalchemy import select, update
            
            # Build update dict
            update_data = {
                'updatedAt': datetime.utcnow()
            }
            
            if assistant_message is not None:
                update_data['assistantMessage'] = assistant_message
            
            if tool_calls is not None:
                update_data['toolCalls'] = tool_calls
            
            if tool_results is not None:
                update_data['toolResults'] = tool_results
            
            if status:
                update_data['status'] = status
                if status in ['COMPLETED', 'FAILED']:
                    update_data['completedAt'] = datetime.utcnow()
            
            if error_message is not None:
                update_data['errorMessage'] = error_message
            
            if metadata is not None:
                # Merge with existing metadata
                stmt = select(ContextManagerConversation).where(
                    ContextManagerConversation.id == conversation_id
                )
                result = await self.db_session.execute(stmt)
                log_entry = result.scalar_one_or_none()
                
                if log_entry and log_entry.meta:
                    merged_metadata = {**log_entry.meta, **metadata}
                    update_data['meta'] = merged_metadata
                else:
                    update_data['meta'] = metadata
            
            # Execute update
            stmt = (
                update(ContextManagerConversation)
                .where(ContextManagerConversation.id == conversation_id)
                .values(**update_data)
            )
            
            await self.db_session.execute(stmt)
            await self.db_session.commit()
            
            logger.info(f"Updated context manager log: {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error updating context manager log: {e}")
            await self.db_session.rollback()
            raise
    
    async def get_user_logs(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get conversation logs for a user
        
        Args:
            user_id: User identifier
            limit: Maximum number of logs to return
            offset: Number of logs to skip
            
        Returns:
            List of conversation log dictionaries
        """
        try:
            from sqlalchemy import select
            
            stmt = (
                select(ContextManagerConversation)
                .where(ContextManagerConversation.userId == user_id)
                .order_by(ContextManagerConversation.startedAt.desc())
                .limit(limit)
                .offset(offset)
            )
            
            result = await self.db_session.execute(stmt)
            logs = result.scalars().all()
            
            return [
                {
                    'id': log.id,
                    'userId': log.userId,
                    'conversationId': log.conversationId,
                    'agentName': log.agentName,
                    'userMessage': log.userMessage,
                    'assistantMessage': log.assistantMessage,
                    'toolCalls': log.toolCalls,
                    'toolResults': log.toolResults,
                    'metadata': log.meta,
                    'status': log.status,
                    'errorMessage': log.errorMessage,
                    'startedAt': log.startedAt.isoformat() if log.startedAt else None,
                    'completedAt': log.completedAt.isoformat() if log.completedAt else None
                }
                for log in logs
            ]
            
        except Exception as e:
            logger.error(f"Error fetching user logs: {e}")
            raise
