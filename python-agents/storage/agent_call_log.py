"""
Agent Call Log Storage
Comprehensive logging for all agent interactions
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import json
import uuid
from sqlalchemy import text
from utils.logger import logger
from storage.database import db_manager


class AgentCallLogger:
    """Manages agent call logging to database"""
    
    def __init__(self):
        """Initialize agent call logger"""
        self.db = db_manager
        
    def generate_message_id(self) -> str:
        """
        Generate unique message ID for tracking a user message
        across multiple agent calls
        
        Returns:
            Unique message ID (UUID)
        """
        return f"msg_{uuid.uuid4().hex[:16]}"
    
    def generate_session_id(self) -> str:
        """
        Generate unique session ID for tracking broader conversation session
        
        Returns:
            Unique session ID (UUID)
        """
        return f"sess_{uuid.uuid4().hex[:16]}"
    
    async def start_agent_call(
        self,
        user_id: str,
        agent_name: str,
        model_name: str,
        message_id: str,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        agent_version: Optional[str] = None,
        input_message: Optional[str] = None,
        tools_enabled: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Start logging an agent call
        
        Args:
            user_id: User identifier
            agent_name: Name of the agent (e.g., "planner", "task_manager")
            model_name: LLM model being used
            message_id: Unique message ID (tracks across multiple agent calls)
            conversation_id: Optional conversation ID
            session_id: Optional session ID
            agent_type: Type/category of agent
            agent_version: Version of the agent
            input_message: Input prompt/message
            tools_enabled: Whether tools are enabled
            metadata: Additional metadata
            tags: Tags for filtering
            
        Returns:
            Agent call log ID
        """
        try:
            async with self.db.get_session() as session:
                query = text("""
                    INSERT INTO "AgentCallLog" (
                        id, "userId", "conversationId", "messageId", "sessionId",
                        "agentName", "agentType", "agentVersion",
                        "modelName", "modelProvider",
                        "inputMessage", "toolsEnabled",
                        status, "startedAt", metadata, tags,
                        "createdAt", "updatedAt"
                    )
                    VALUES (:id, :userId, :conversationId, :messageId, :sessionId,
                           :agentName, :agentType, :agentVersion,
                           :modelName, :modelProvider,
                           :inputMessage, :toolsEnabled,
                           :status, :startedAt, CAST(:metadata AS jsonb), :tags,
                           :createdAt, :updatedAt)
                    RETURNING id
                """)
                
                log_id = f"acl_{uuid.uuid4().hex[:16]}"
                now = datetime.now(timezone.utc)
                
                # Prepare metadata
                meta_json = json.dumps(metadata) if metadata else None
                tags_array = tags if tags else []
                
                result = await session.execute(
                    query,
                    {
                        "id": log_id,
                        "userId": user_id,
                        "conversationId": conversation_id,
                        "messageId": message_id,
                        "sessionId": session_id,
                        "agentName": agent_name,
                        "agentType": agent_type,
                        "agentVersion": agent_version,
                        "modelName": model_name,
                        "modelProvider": "openai",
                        "inputMessage": input_message,
                        "toolsEnabled": tools_enabled,
                        "status": "IN_PROGRESS",
                        "startedAt": now.replace(tzinfo=None),  # Remove timezone for DB
                        "metadata": meta_json,
                        "tags": tags_array,
                        "createdAt": now.replace(tzinfo=None),  # Remove timezone for DB
                        "updatedAt": now.replace(tzinfo=None)   # Remove timezone for DB
                    }
                )
                await session.commit()
                
                logger.info(f"Started agent call log: {log_id} for agent={agent_name}, message_id={message_id}")
                return log_id
            
        except Exception as e:
            logger.error(f"Failed to start agent call log: {str(e)}")
            # Return a fallback ID so the agent can continue
            return f"acl_fallback_{uuid.uuid4().hex[:8]}"
    
    async def complete_agent_call(
        self,
        log_id: str,
        output_message: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Complete an agent call with success
        
        Args:
            log_id: Agent call log ID
            output_message: Agent's response/output
            tool_calls: List of tool calls made
            tool_results: Results from tool calls
            prompt_tokens: Token count for prompt
            completion_tokens: Token count for completion
            total_tokens: Total tokens used
            metadata: Additional metadata to merge
        """
        try:
            async with self.db.get_session() as session:
                completed_at = datetime.now(timezone.utc).replace(tzinfo=None)  # Remove timezone for DB
                
                # Update query - calculate duration using NOW()
                update_query = text("""
                    UPDATE "AgentCallLog"
                    SET 
                        status = :status,
                        "completedAt" = :completedAt,
                        "durationMs" = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - "startedAt")) * 1000,
                        "outputMessage" = :outputMessage,
                        "toolCalls" = CAST(:toolCalls AS jsonb),
                        "toolResults" = CAST(:toolResults AS jsonb),
                        "promptTokens" = :promptTokens,
                        "completionTokens" = :completionTokens,
                        "totalTokens" = :totalTokens,
                        metadata = COALESCE(metadata, '{}'::jsonb) || CAST(:metadata AS jsonb),
                        "updatedAt" = :updatedAt
                    WHERE id = :log_id
                """)
                
                await session.execute(
                    update_query,
                    {
                        "status": "COMPLETED",
                        "completedAt": completed_at,
                        "outputMessage": output_message,
                        "toolCalls": json.dumps(tool_calls) if tool_calls else None,
                        "toolResults": json.dumps(tool_results) if tool_results else None,
                        "promptTokens": prompt_tokens,
                        "completionTokens": completion_tokens,
                        "totalTokens": total_tokens,
                        "metadata": json.dumps(metadata) if metadata else "{}",
                        "updatedAt": completed_at,
                        "log_id": log_id
                    }
                )
                await session.commit()
                
                logger.info(f"Completed agent call log: {log_id}")
            
        except Exception as e:
            logger.error(f"Failed to complete agent call log {log_id}: {str(e)}")
    
    async def fail_agent_call(
        self,
        log_id: str,
        error: str,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Mark an agent call as failed
        
        Args:
            log_id: Agent call log ID
            error: Error message
            error_type: Type of error
            stack_trace: Stack trace if available
            metadata: Additional metadata
        """
        try:
            async with self.db.get_session() as session:
                completed_at = datetime.now(timezone.utc).replace(tzinfo=None)  # Remove timezone for DB
                
                # Update query - calculate duration using CURRENT_TIMESTAMP
                update_query = text("""
                    UPDATE "AgentCallLog"
                    SET 
                        status = :status,
                        "completedAt" = :completedAt,
                        "durationMs" = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - "startedAt")) * 1000,
                        error = :error,
                        "errorType" = :errorType,
                        "stackTrace" = :stackTrace,
                        metadata = COALESCE(metadata, '{}'::jsonb) || CAST(:metadata AS jsonb),
                        "updatedAt" = :updatedAt
                    WHERE id = :log_id
                """)
                
                await session.execute(
                    update_query,
                    {
                        "status": "FAILED",
                        "completedAt": completed_at,
                        "error": error,
                        "errorType": error_type,
                        "stackTrace": stack_trace,
                        "metadata": json.dumps(metadata) if metadata else "{}",
                        "updatedAt": completed_at,
                        "log_id": log_id
                    }
                )
                await session.commit()
                
                logger.error(f"Failed agent call log: {log_id} - {error}")
            
        except Exception as e:
            logger.error(f"Failed to update agent call log {log_id} as failed: {str(e)}")
    
    async def update_tool_calls(
        self,
        log_id: str,
        tool_calls: List[Dict[str, Any]]
    ):
        """
        Update tool calls for an in-progress agent call
        
        Args:
            log_id: Agent call log ID
            tool_calls: List of tool calls
        """
        try:
            async with self.db.get_session() as session:
                query = text("""
                    UPDATE "AgentCallLog"
                    SET "toolCalls" = CAST(:toolCalls AS jsonb), "updatedAt" = :updatedAt
                    WHERE id = :log_id
                """)
                
                await session.execute(
                    query,
                    {
                        "toolCalls": json.dumps(tool_calls),
                        "updatedAt": datetime.now(timezone.utc).replace(tzinfo=None),
                        "log_id": log_id
                    }
                )
                await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to update tool calls for {log_id}: {str(e)}")
    
    async def update_tool_results(
        self,
        log_id: str,
        tool_results: List[Dict[str, Any]]
    ):
        """
        Update tool results for an in-progress agent call
        
        Args:
            log_id: Agent call log ID
            tool_results: List of tool results
        """
        try:
            async with self.db.get_session() as session:
                query = text("""
                    UPDATE "AgentCallLog"
                    SET "toolResults" = CAST(:toolResults AS jsonb), "updatedAt" = :updatedAt
                    WHERE id = :log_id
                """)
                
                await session.execute(
                    query,
                    {
                        "toolResults": json.dumps(tool_results),
                        "updatedAt": datetime.now(timezone.utc).replace(tzinfo=None),
                        "log_id": log_id
                    }
                )
                await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to update tool results for {log_id}: {str(e)}")
    
    async def get_logs_by_message(
        self,
        message_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all agent call logs for a specific message ID
        (traces the complete journey of a user message)
        
        Args:
            message_id: Message identifier
            
        Returns:
            List of agent call logs ordered by startedAt
        """
        try:
            async with self.db.get_session() as session:
                query = text("""
                    SELECT * FROM "AgentCallLog"
                    WHERE "messageId" = :message_id
                    ORDER BY "startedAt" ASC
                """)
                
                result = await session.execute(query, {"message_id": message_id})
                rows = result.fetchall()
                
                # Convert rows to dictionaries
                logs = []
                for row in rows:
                    logs.append(dict(row._mapping))
                
                return logs
            
        except Exception as e:
            logger.error(f"Failed to get logs for message {message_id}: {str(e)}")
            return []
    
    async def get_logs_by_conversation(
        self,
        conversation_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all agent call logs for a conversation
        
        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of logs to return
            
        Returns:
            List of agent call logs ordered by startedAt
        """
        try:
            async with self.db.get_session() as session:
                query = text("""
                    SELECT * FROM "AgentCallLog"
                    WHERE "conversationId" = :conversation_id
                    ORDER BY "startedAt" DESC
                    LIMIT :limit
                """)
                
                result = await session.execute(query, {"conversation_id": conversation_id, "limit": limit})
                rows = result.fetchall()
                
                # Convert rows to dictionaries
                logs = []
                for row in rows:
                    logs.append(dict(row._mapping))
                
                return logs
            
        except Exception as e:
            logger.error(f"Failed to get logs for conversation {conversation_id}: {str(e)}")
            return []
    
    async def get_logs_by_agent(
        self,
        agent_name: str,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent logs for a specific agent
        
        Args:
            agent_name: Name of the agent
            user_id: Optional user filter
            limit: Maximum number of logs
            
        Returns:
            List of agent call logs
        """
        try:
            async with self.db.get_session() as session:
                if user_id:
                    query = text("""
                        SELECT * FROM "AgentCallLog"
                        WHERE "agentName" = :agent_name AND "userId" = :user_id
                        ORDER BY "startedAt" DESC
                        LIMIT :limit
                    """)
                    result = await session.execute(query, {"agent_name": agent_name, "user_id": user_id, "limit": limit})
                else:
                    query = text("""
                        SELECT * FROM "AgentCallLog"
                        WHERE "agentName" = :agent_name
                        ORDER BY "startedAt" DESC
                        LIMIT :limit
                    """)
                    result = await session.execute(query, {"agent_name": agent_name, "limit": limit})
                
                rows = result.fetchall()
                
                # Convert rows to dictionaries
                logs = []
                for row in rows:
                    logs.append(dict(row._mapping))
                
                return logs
            
        except Exception as e:
            logger.error(f"Failed to get logs for agent {agent_name}: {str(e)}")
            return []


# Singleton instance
agent_call_logger = AgentCallLogger()
