"""
Agent Call Log Storage
Comprehensive logging for all agent interactions

Writes to both the "AgentCallLog" table and a mirrored file under
AGENT_CALL_LOG_PATH/<conversationId>/<messageId>.log (JSON Lines, one
event per start/update/complete/fail call) so calls can be traced
without querying the database.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
import json
import uuid
from sqlalchemy import text
from utils.logger import logger
from storage.database import db_manager
from config.settings import settings


class AgentCallLogger:
    """Manages agent call logging to database and to per-message log files"""

    def __init__(self):
        """Initialize agent call logger"""
        self.db = db_manager
        self.log_dir = Path(settings.AGENT_CALL_LOG_PATH)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        # log_id -> (conversation_id, message_id), so update/complete/fail
        # calls (which only receive log_id) know which file to append to
        self._log_locations: Dict[int, tuple] = {}

    def _write_log_event(
        self,
        conversation_id: Optional[int],
        message_id: str,
        event: Dict[str, Any]
    ):
        """Append a JSON-line event to conversationId/messageId.log"""
        try:
            conversation_dir = self.log_dir / (str(conversation_id) if conversation_id is not None else "no_conversation")
            conversation_dir.mkdir(parents=True, exist_ok=True)
            log_file = conversation_dir / f"{message_id}.log"

            event_with_timestamp = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **event
            }
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_with_timestamp, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to write agent call log file for message {message_id}: {str(e)}")

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
        user_id: int,
        agent_name: str,
        model_name: str,
        message_id: str,
        conversation_id: Optional[int] = None,
        session_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        agent_version: Optional[str] = None,
        input_message: Optional[str] = None,
        tools_enabled: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        iteration_number: Optional[int] = None,
        workflow_phase: Optional[str] = None,
        parent_call_id: Optional[str] = None,
        task_id: Optional[str] = None,
        task_type: Optional[str] = None
    ) -> int:
        """
        Start logging an agent call
        
        Args:
            user_id: User identifier (integer)
            agent_name: Name of the agent (e.g., "planner", "task_manager")
            model_name: LLM model being used
            message_id: Unique message ID (tracks across multiple agent calls)
            conversation_id: Optional conversation ID (integer)
            session_id: Optional session ID
            agent_type: Type/category of agent
            agent_version: Version of the agent
            input_message: Input prompt/message
            tools_enabled: Whether tools are enabled
            metadata: Additional metadata
            tags: Tags for filtering
            iteration_number: Which iteration in the workflow (1, 2, 3...)
            workflow_phase: "planning" | "executing" | "synthesizing" | "replanning"
            parent_call_id: Link to parent agent call (for replanning chains)
            task_id: Reference to task being executed (from Redis)
            task_type: "tool_call" | "agent_call" (if executing a task)
            
        Returns:
            Agent call log ID
        """
        try:
            async with self.db.get_session() as session:
                query = text("""
                    INSERT INTO "AgentCallLog" (
                        "userId", "conversationId", "messageId", "sessionId",
                        "agentName", "agentType", "agentVersion",
                        "modelName", "modelProvider",
                        "inputMessage", "toolsEnabled",
                        "iterationNumber", "workflowPhase", "parentCallId",
                        "taskId", "taskType",
                        status, "startedAt", metadata, tags,
                        "createdAt", "updatedAt"
                    )
                    VALUES (:userId, :conversationId, :messageId, :sessionId,
                           :agentName, :agentType, :agentVersion,
                           :modelName, :modelProvider,
                           :inputMessage, :toolsEnabled,
                           :iterationNumber, :workflowPhase, :parentCallId,
                           :taskId, :taskType,
                           :status, :startedAt, CAST(:metadata AS jsonb), :tags,
                           :createdAt, :updatedAt)
                    RETURNING id
                """)
                
                now = datetime.now(timezone.utc)
                
                # Prepare metadata
                meta_json = json.dumps(metadata) if metadata else None
                tags_array = tags if tags else []
                
                result = await session.execute(
                    query,
                    {
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
                        "iterationNumber": iteration_number,
                        "workflowPhase": workflow_phase,
                        "parentCallId": parent_call_id,
                        "taskId": task_id,
                        "taskType": task_type,
                        "status": "IN_PROGRESS",
                        "startedAt": now.replace(tzinfo=None),  # Remove timezone for DB
                        "metadata": meta_json,
                        "tags": tags_array,
                        "createdAt": now.replace(tzinfo=None),  # Remove timezone for DB
                        "updatedAt": now.replace(tzinfo=None)   # Remove timezone for DB
                    }
                )
                
                # Get the auto-generated ID
                row = result.fetchone()
                log_id = row[0] if row else None
                
                await session.commit()
                
                if log_id:
                    logger.info(f"Started agent call log: {log_id} for agent={agent_name}, message_id={message_id}")

                    self._log_locations[log_id] = (conversation_id, message_id)
                    self._write_log_event(conversation_id, message_id, {
                        "event": "start",
                        "logId": log_id,
                        "userId": user_id,
                        "conversationId": conversation_id,
                        "messageId": message_id,
                        "sessionId": session_id,
                        "agentName": agent_name,
                        "agentType": agent_type,
                        "agentVersion": agent_version,
                        "modelName": model_name,
                        "inputMessage": input_message,
                        "toolsEnabled": tools_enabled,
                        "iterationNumber": iteration_number,
                        "workflowPhase": workflow_phase,
                        "parentCallId": parent_call_id,
                        "taskId": task_id,
                        "taskType": task_type,
                        "metadata": metadata,
                        "tags": tags
                    })

                    return log_id
                else:
                    raise Exception("Failed to get generated ID from INSERT")
            
        except Exception as e:
            logger.error(f"Failed to start agent call log: {str(e)}")
            raise
    
    async def complete_agent_call(
        self,
        log_id: int,
        output_message: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        tool_calls_detailed: Optional[List[Dict[str, Any]]] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        completion_score: Optional[float] = None,
        synthesis_action: Optional[str] = None,
        gaps_identified: Optional[int] = None
    ):
        """
        Complete an agent call with success
        
        Args:
            log_id: Agent call log ID
            output_message: Agent's response/output
            tool_calls: List of tool calls made
            tool_results: Results from tool calls
            tool_calls_detailed: Detailed tool execution info (input, output, exception, duration)
            prompt_tokens: Token count for prompt
            completion_tokens: Token count for completion
            total_tokens: Total tokens used
            metadata: Additional metadata to merge
            completion_score: (Synthesizer only) 0-1 score for goal achievement
            synthesis_action: (Synthesizer only) "publish" | "partial_publish" | "replan"
            gaps_identified: (Synthesizer only) Number of gaps found
        """
        try:
            async with self.db.get_session() as session:
                completed_at = datetime.now(timezone.utc).replace(tzinfo=None)  # Remove timezone for DB
                
                # Update query - calculate duration using completedAt
                update_query = text("""
                    UPDATE "AgentCallLog"
                    SET 
                        status = :status,
                        "completedAt" = :completedAt,
                        "durationMs" = EXTRACT(EPOCH FROM (:completedAt - "startedAt")) * 1000,
                        "outputMessage" = :outputMessage,
                        "toolCalls" = CAST(:toolCalls AS jsonb),
                        "toolResults" = CAST(:toolResults AS jsonb),
                        "toolCallsDetailed" = CAST(:toolCallsDetailed AS jsonb),
                        "promptTokens" = :promptTokens,
                        "completionTokens" = :completionTokens,
                        "totalTokens" = :totalTokens,
                        "completionScore" = :completionScore,
                        "synthesisAction" = :synthesisAction,
                        "gapsIdentified" = :gapsIdentified,
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
                        "toolCallsDetailed": json.dumps(tool_calls_detailed) if tool_calls_detailed else None,
                        "promptTokens": prompt_tokens,
                        "completionTokens": completion_tokens,
                        "totalTokens": total_tokens,
                        "completionScore": completion_score,
                        "synthesisAction": synthesis_action,
                        "gapsIdentified": gaps_identified,
                        "metadata": json.dumps(metadata) if metadata else "{}",
                        "updatedAt": completed_at,
                        "log_id": log_id
                    }
                )
                await session.commit()

                logger.info(f"Completed agent call log: {log_id}")

                conversation_id, message_id = self._log_locations.pop(log_id, (None, None))
                if message_id:
                    self._write_log_event(conversation_id, message_id, {
                        "event": "complete",
                        "logId": log_id,
                        "outputMessage": output_message,
                        "toolCalls": tool_calls,
                        "toolResults": tool_results,
                        "toolCallsDetailed": tool_calls_detailed,
                        "promptTokens": prompt_tokens,
                        "completionTokens": completion_tokens,
                        "totalTokens": total_tokens,
                        "completionScore": completion_score,
                        "synthesisAction": synthesis_action,
                        "gapsIdentified": gaps_identified,
                        "metadata": metadata
                    })

        except Exception as e:
            logger.error(f"Failed to complete agent call log {log_id}: {str(e)}")
    
    async def fail_agent_call(
        self,
        log_id: int,
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

                conversation_id, message_id = self._log_locations.pop(log_id, (None, None))
                if message_id:
                    self._write_log_event(conversation_id, message_id, {
                        "event": "fail",
                        "logId": log_id,
                        "error": error,
                        "errorType": error_type,
                        "stackTrace": stack_trace,
                        "metadata": metadata
                    })

        except Exception as e:
            logger.error(f"Failed to update agent call log {log_id} as failed: {str(e)}")
    
    async def update_tool_calls(
        self,
        log_id: int,
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

                conversation_id, message_id = self._log_locations.get(log_id, (None, None))
                if message_id:
                    self._write_log_event(conversation_id, message_id, {
                        "event": "update_tool_calls",
                        "logId": log_id,
                        "toolCalls": tool_calls
                    })

        except Exception as e:
            logger.error(f"Failed to update tool calls for {log_id}: {str(e)}")
    
    async def update_tool_results(
        self,
        log_id: int,
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

                conversation_id, message_id = self._log_locations.get(log_id, (None, None))
                if message_id:
                    self._write_log_event(conversation_id, message_id, {
                        "event": "update_tool_results",
                        "logId": log_id,
                        "toolResults": tool_results
                    })

        except Exception as e:
            logger.error(f"Failed to update tool results for {log_id}: {str(e)}")
    
    async def update_tool_calls_detailed(
        self,
        log_id: int,
        tool_calls_detailed: List[Dict[str, Any]]
    ):
        """
        Update detailed tool call information including input, output, exceptions
        
        Args:
            log_id: Agent call log ID
            tool_calls_detailed: List of detailed tool call records with:
                - tool_call_id: Unique identifier for the tool call
                - name: Tool name
                - input: Tool input arguments (JSON)
                - output: Tool execution result
                - exception: Exception message if tool failed
                - started_at: ISO timestamp when tool execution started
                - completed_at: ISO timestamp when tool execution completed
                - duration_ms: Execution duration in milliseconds
                - success: Boolean indicating if tool succeeded
        """
        try:
            async with self.db.get_session() as session:
                query = text("""
                    UPDATE "AgentCallLog"
                    SET "toolCallsDetailed" = CAST(:toolCallsDetailed AS jsonb), "updatedAt" = :updatedAt
                    WHERE id = :log_id
                """)
                
                await session.execute(
                    query,
                    {
                        "toolCallsDetailed": json.dumps(tool_calls_detailed),
                        "updatedAt": datetime.now(timezone.utc).replace(tzinfo=None),
                        "log_id": log_id
                    }
                )
                await session.commit()
                logger.debug(f"Updated detailed tool calls for {log_id}: {len(tool_calls_detailed)} records")

                conversation_id, message_id = self._log_locations.get(log_id, (None, None))
                if message_id:
                    self._write_log_event(conversation_id, message_id, {
                        "event": "update_tool_calls_detailed",
                        "logId": log_id,
                        "toolCallsDetailed": tool_calls_detailed
                    })

        except Exception as e:
            logger.error(f"Failed to update detailed tool calls for {log_id}: {str(e)}")
    
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
        conversation_id: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all agent call logs for a conversation
        
        Args:
            conversation_id: Conversation identifier (integer)
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
        user_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent logs for a specific agent
        
        Args:
            agent_name: Name of the agent
            user_id: Optional user filter (integer)
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
