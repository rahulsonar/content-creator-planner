"""
Conversation Storage
Handles database operations for conversations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import text
from storage.database import db_manager
from utils.logger import logger


class ConversationStorage:
    """Manages conversation persistence"""
    
    def __init__(self):
        """Initialize conversation storage"""
        self.db = db_manager
        logger.info("Initialized conversation storage")
    
    async def create_conversation(
        self,
        user_id: str,
        conversation_type: str = "chat",
        title: Optional[str] = None
    ) -> str:
        """
        Create new conversation record
        
        Args:
            user_id: User identifier
            conversation_type: Type (onboarding, planning, chat)
            title: Optional conversation title
            
        Returns:
            Conversation ID
        """
        try:
            async for session in self.db.get_session():
                # Insert conversation into database
                query = text("""
                    INSERT INTO "Conversation" ("id", "userId", "title", "messages", "metadata", "createdAt", "updatedAt")
                    VALUES (gen_random_uuid()::text, :userId, :title, :messages, :metadata, NOW(), NOW())
                    RETURNING id
                """)
                
                result = await session.execute(
                    query,
                    {
                        "userId": user_id,
                        "title": title or f"{conversation_type.title()} conversation",
                        "messages": "[]",  # JSON array as string
                        "metadata": f'{{"type": "{conversation_type}"}}'  # JSON object as string
                    }
                )
                await session.commit()
                
                conversation_id = result.scalar_one()
                logger.info(f"Created conversation: {conversation_id} for user {user_id}")
                return conversation_id
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            raise
    
    async def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model: Optional[str] = None,
        tokens_used: Optional[int] = None
    ):
        """
        Save message to conversation
        
        Args:
            conversation_id: Conversation identifier
            role: Message role (user/assistant/system)
            content: Message content
            model: Model used (if assistant)
            tokens_used: Token count
        """
        try:
            async for session in self.db.get_session():
                import json
                
                # Build message object
                message = {
                    "role": role,
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                }
                if model:
                    message["model"] = model
                if tokens_used:
                    message["tokens"] = tokens_used
                
                # Append message to the messages JSON array
                # Cast the parameter as JSONB using SQLAlchemy's cast function
                from sqlalchemy import cast
                from sqlalchemy.dialects.postgresql import JSONB
                
                query = text("""
                    UPDATE "Conversation"
                    SET messages = messages || CAST(:message_json AS jsonb),
                        "updatedAt" = NOW()
                    WHERE id = :conv_id
                """)
                
                await session.execute(
                    query,
                    {
                        "conv_id": conversation_id,
                        "message_json": json.dumps([message])  # Convert to JSON array string
                    }
                )
                await session.commit()
                
                logger.debug(f"Saved {role} message to conversation {conversation_id}")
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            raise
    
    async def get_conversation(
        self,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve conversation by ID
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Conversation data or None
        """
        try:
            async for session in self.db.get_session():
                query = text("""
                    SELECT id, "userId", title, messages, metadata, "createdAt", "updatedAt"
                    FROM "Conversation"
                    WHERE id = :conversationId
                """)
                
                result = await session.execute(
                    query,
                    {"conversationId": conversation_id}
                )
                row = result.fetchone()
                
                if row:
                    import json
                    # Parse messages if it's a string
                    messages = row[3]
                    if isinstance(messages, str):
                        messages = json.loads(messages)
                    
                    # Parse metadata if it's a string
                    metadata = row[4]
                    if isinstance(metadata, str):
                        metadata = json.loads(metadata) if metadata else {}
                    
                    conversation = {
                        "id": row[0],
                        "userId": row[1],
                        "title": row[2],
                        "messages": messages,
                        "metadata": metadata,
                        "createdAt": row[5].isoformat() if row[5] else None,
                        "updatedAt": row[6].isoformat() if row[6] else None
                    }
                    logger.debug(f"Retrieved conversation: {conversation_id}")
                    return conversation
                
                return None
        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            raise
    
    async def get_user_conversations(
        self,
        user_id: str,
        conversation_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get user's conversation history
        
        Args:
            user_id: User identifier
            conversation_type: Filter by type (optional)
            limit: Maximum results
            
        Returns:
            List of conversations
        """
        try:
            async for session in self.db.get_session():
                if conversation_type:
                    query = text("""
                        SELECT id, "userId", title, messages, metadata, "createdAt", "updatedAt"
                        FROM "Conversation"
                        WHERE "userId" = :userId 
                        AND metadata->>'type' = :convType
                        ORDER BY "updatedAt" DESC
                        LIMIT :limit
                    """)
                    params = {"userId": user_id, "convType": conversation_type, "limit": limit}
                else:
                    query = text("""
                        SELECT id, "userId", title, messages, metadata, "createdAt", "updatedAt"
                        FROM "Conversation"
                        WHERE "userId" = :userId
                        ORDER BY "updatedAt" DESC
                        LIMIT :limit
                    """)
                    params = {"userId": user_id, "limit": limit}
                
                result = await session.execute(query, params)
                rows = result.fetchall()
                
                conversations = []
                for row in rows:
                    conversations.append({
                        "id": row[0],
                        "userId": row[1],
                        "title": row[2],
                        "messages": row[3],
                        "metadata": row[4],
                        "createdAt": row[5].isoformat() if row[5] else None,
                        "updatedAt": row[6].isoformat() if row[6] else None
                    })
                
                logger.debug(f"Retrieved {len(conversations)} conversations for user: {user_id}")
                return conversations
        except Exception as e:
            logger.error(f"Error getting user conversations: {e}")
            raise
    
    async def update_conversation_status(
        self,
        conversation_id: str,
        status: str
    ):
        """
        Update conversation status
        
        Args:
            conversation_id: Conversation identifier
            status: New status (active, completed, abandoned)
        """
        try:
            async for session in self.db.get_session():
                import json
                
                query = text("""
                    UPDATE "Conversation"
                    SET metadata = jsonb_set(metadata, '{status}', CAST(:status_json AS jsonb)),
                        "updatedAt" = NOW()
                    WHERE id = :conv_id
                """)
                
                await session.execute(
                    query,
                    {
                        "conv_id": conversation_id,
                        "status_json": json.dumps(status)  # Convert to JSON string
                    }
                )
                await session.commit()
                
                logger.info(f"Updated conversation {conversation_id} status to {status}")
        except Exception as e:
            logger.error(f"Error updating conversation status: {e}")
            raise
    
    async def update_conversation_user(
        self,
        conversation_id: str,
        user_id: str
    ):
        """
        Update conversation userId (e.g., claim an anonymous conversation)
        
        Args:
            conversation_id: Conversation identifier
            user_id: New user ID to assign
        """
        try:
            async for session in self.db.get_session():
                query = text("""
                    UPDATE "Conversation"
                    SET "userId" = :userId,
                        "updatedAt" = NOW()
                    WHERE id = :conv_id
                """)
                
                await session.execute(
                    query,
                    {
                        "conv_id": conversation_id,
                        "userId": user_id
                    }
                )
                await session.commit()
                
                logger.info(f"Updated conversation {conversation_id} userId to {user_id}")
        except Exception as e:
            logger.error(f"Error updating conversation user: {e}")
            raise
    
    async def calculate_cost(
        self,
        conversation_id: str
    ) -> float:
        """
        Calculate total cost for conversation
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Estimated cost in USD
        """
        try:
            async for session in self.db.get_session():
                query = text("""
                    SELECT messages
                    FROM "Conversation"
                    WHERE id = :conversationId
                """)
                
                result = await session.execute(
                    query,
                    {"conversationId": conversation_id}
                )
                row = result.fetchone()
                
                if not row or not row[0]:
                    return 0.0
                
                # Calculate cost from message tokens
                total_tokens = 0
                messages = row[0] if isinstance(row[0], list) else []
                
                for msg in messages:
                    if isinstance(msg, dict) and "tokens" in msg:
                        total_tokens += msg["tokens"]
                
                # Rough cost estimate: $0.002 per 1k tokens (average)
                cost = (total_tokens / 1000) * 0.002
                
                logger.debug(f"Calculated cost for conversation {conversation_id}: ${cost:.4f}")
                return cost
        except Exception as e:
            logger.error(f"Error calculating conversation cost: {e}")
            return 0.0
