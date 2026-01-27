"""
Executor Agent (Child Agent)
Handles individual sub-tasks delegated by the Planner agent
Can work independently and fetch task context from Redis
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import asyncio
import json
import traceback
from agents.base import BaseAgent
from utils.logger import logger
from storage.agent_call_log import agent_call_logger


class ExecutorAgent(BaseAgent):
    """Child agent for executing individual sub-tasks"""
    
    def __init__(
        self, 
        model_client, 
        redis_client=None,
        task_manager_agent=None,
        executor_id: Optional[str] = None
    ):
        """
        Initialize executor agent.
        
        Args:
            model_client: LLM client (OpenAI or Claude)
            redis_client: Redis client for fetching task context
            task_manager_agent: Task manager agent for database operations
            executor_id: Unique identifier for this executor instance
        """
        super().__init__(model_client, "executor")
        self.redis_client = redis_client
        self.task_manager_agent = task_manager_agent
        self.executor_id = executor_id or f"executor_{datetime.now(timezone.utc).timestamp()}"
        self._current_subtask_id = None
        self._parent_task_id = None
        
        # Initialize metadata
        self.metadata = {
            "agent_name": "executor",
            "agent_type": "executor",
            "executor_id": self.executor_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity_at": None,
            "subtasks_processed": 0,
            "subtasks_completed": 0,
            "subtasks_failed": 0,
            "model_name": getattr(model_client, 'model', 'unknown'),
            "agent_version": "1.0.0"
        }
        
        logger.info(f"ExecutorAgent initialized: {self.executor_id}")

    async def execute_subtask(
        self, 
        subtask_id: str,
        parent_task_id: str,
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a specific subtask by fetching its context from Redis.
        
        Args:
            subtask_id: Unique identifier for the subtask
            parent_task_id: Parent task identifier
            user_id: User identifier
            conversation_id: Optional conversation identifier
            
        Returns:
            Dict with execution results and status
        """
        self._current_subtask_id = subtask_id
        self._parent_task_id = parent_task_id
        self.metadata["subtasks_processed"] += 1
        self.metadata["last_activity_at"] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"[{self.executor_id}] Starting execution of subtask: {subtask_id}")
        
        try:
            # Fetch subtask context from Redis
            subtask_context = await self._fetch_subtask_context(
                subtask_id, 
                parent_task_id, 
                user_id
            )
            
            if not subtask_context:
                logger.error(f"[{self.executor_id}] No context found for subtask {subtask_id}")
                self.metadata["subtasks_failed"] += 1
                return {
                    "success": False,
                    "subtask_id": subtask_id,
                    "error": "Subtask context not found in Redis"
                }
            
            # Update subtask status to IN_PROGRESS
            await self._update_subtask_status(
                subtask_id, 
                parent_task_id, 
                user_id, 
                "in_progress"
            )
            
            # Process the subtask
            result = await self._process_subtask(subtask_context, user_id)
            
            # Update status based on result
            if result.get("success"):
                await self._update_subtask_status(
                    subtask_id, 
                    parent_task_id, 
                    user_id, 
                    "completed",
                    result.get("output")
                )
                self.metadata["subtasks_completed"] += 1
                logger.info(f"[{self.executor_id}] Completed subtask: {subtask_id}")
            else:
                await self._update_subtask_status(
                    subtask_id, 
                    parent_task_id, 
                    user_id, 
                    "failed",
                    result.get("error")
                )
                self.metadata["subtasks_failed"] += 1
                logger.error(f"[{self.executor_id}] Failed subtask: {subtask_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"[{self.executor_id}] Error executing subtask {subtask_id}: {e}")
            logger.error(traceback.format_exc())
            self.metadata["subtasks_failed"] += 1
            
            # Update status to failed
            await self._update_subtask_status(
                subtask_id, 
                parent_task_id, 
                user_id, 
                "failed",
                str(e)
            )
            
            return {
                "success": False,
                "subtask_id": subtask_id,
                "error": str(e)
            }

    async def _fetch_subtask_context(
        self, 
        subtask_id: str, 
        parent_task_id: str, 
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch subtask context from Redis.
        
        Args:
            subtask_id: Subtask identifier
            parent_task_id: Parent task identifier
            user_id: User identifier
            
        Returns:
            Subtask context dictionary or None
        """
        if not self.redis_client:
            logger.warning(f"[{self.executor_id}] No Redis client available")
            return None
        
        try:
            key = f"subtask:{parent_task_id}:{subtask_id}:{user_id}"
            context_json = await self.redis_client.get(key)
            
            if context_json:
                return json.loads(context_json)
            
            logger.warning(f"[{self.executor_id}] No context found for key: {key}")
            return None
            
        except Exception as e:
            logger.error(f"[{self.executor_id}] Error fetching subtask context: {e}")
            return None

    async def _update_subtask_status(
        self, 
        subtask_id: str, 
        parent_task_id: str, 
        user_id: str, 
        status: str,
        result: Optional[str] = None
    ):
        """
        Update subtask status in Redis.
        
        Args:
            subtask_id: Subtask identifier
            parent_task_id: Parent task identifier
            user_id: User identifier
            status: New status (pending/in_progress/completed/failed)
            result: Optional result or error message
        """
        if not self.redis_client:
            return
        
        try:
            status_key = f"subtask_status:{parent_task_id}:{subtask_id}:{user_id}"
            status_data = {
                "subtask_id": subtask_id,
                "parent_task_id": parent_task_id,
                "status": status,
                "executor_id": self.executor_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "result": result
            }
            
            await self.redis_client.set(
                status_key, 
                json.dumps(status_data),
                ex=3600  # Expire after 1 hour
            )
            
            logger.info(f"[{self.executor_id}] Updated subtask {subtask_id} status to: {status}")
            
        except Exception as e:
            logger.error(f"[{self.executor_id}] Error updating subtask status: {e}")

    async def _process_subtask(
        self, 
        subtask_context: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Process the subtask using the LLM.
        
        Args:
            subtask_context: Context containing task details
            user_id: User identifier
            
        Returns:
            Dict with processing results
        """
        try:
            # Extract subtask information
            task_description = subtask_context.get("description", "")
            task_goal = subtask_context.get("goal", "")
            additional_context = subtask_context.get("context", {})
            
            # Build system prompt for executor
            system_prompt = self._build_executor_prompt(subtask_context)
            
            # Build user message
            user_message = f"""
Execute the following subtask:

Task: {task_description}
Goal: {task_goal}

Additional Context:
{json.dumps(additional_context, indent=2)}

Provide a detailed execution plan and output for this task.
"""
            
            # Reset conversation history for this subtask
            self.conversation_history = []
            self.add_to_history("system", system_prompt)
            self.add_to_history("user", user_message)
            
            # Get response from LLM
            response = await self.model_client.chat(
                messages=self.conversation_history,
                temperature=0.7,
                max_tokens=2000
            )
            
            # Extract content
            if hasattr(response, 'content'):
                output = response.content
            elif isinstance(response, dict):
                output = response.get('content', str(response))
            else:
                output = str(response)
            
            # Store output in Redis for parent to retrieve
            await self._store_subtask_output(
                self._current_subtask_id,
                self._parent_task_id,
                user_id,
                output
            )
            
            return {
                "success": True,
                "subtask_id": self._current_subtask_id,
                "output": output,
                "executor_id": self.executor_id
            }
            
        except Exception as e:
            logger.error(f"[{self.executor_id}] Error processing subtask: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "subtask_id": self._current_subtask_id,
                "error": str(e)
            }

    def _build_executor_prompt(self, subtask_context: Dict[str, Any]) -> str:
        """
        Build system prompt for the executor agent.
        
        Args:
            subtask_context: Context for the subtask
            
        Returns:
            System prompt string
        """
        return f"""You are an Executor Agent, specialized in completing individual sub-tasks.

Your Role:
- Execute the assigned subtask with precision and detail
- Break down the task into actionable steps
- Provide comprehensive output that can be used by the parent planner
- Focus on completing this specific task without diverging

Executor ID: {self.executor_id}
Task Type: {subtask_context.get('task_type', 'general')}

Guidelines:
1. Read the task description and goal carefully
2. Consider all provided context
3. Create a step-by-step execution plan
4. Execute each step thoroughly
5. Provide detailed output including:
   - What was done
   - Key findings or results
   - Any recommendations or next steps
   - Potential issues or considerations

Be thorough, precise, and actionable in your responses.
"""

    async def _store_subtask_output(
        self,
        subtask_id: str,
        parent_task_id: str,
        user_id: str,
        output: str
    ):
        """
        Store subtask output in Redis for parent retrieval.
        
        Args:
            subtask_id: Subtask identifier
            parent_task_id: Parent task identifier
            user_id: User identifier
            output: Task output to store
        """
        if not self.redis_client:
            return
        
        try:
            output_key = f"subtask_output:{parent_task_id}:{subtask_id}:{user_id}"
            output_data = {
                "subtask_id": subtask_id,
                "parent_task_id": parent_task_id,
                "executor_id": self.executor_id,
                "output": output,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.redis_client.set(
                output_key,
                json.dumps(output_data),
                ex=3600  # Expire after 1 hour
            )
            
            logger.info(f"[{self.executor_id}] Stored output for subtask: {subtask_id}")
            
        except Exception as e:
            logger.error(f"[{self.executor_id}] Error storing subtask output: {e}")

    async def process_message(
        self, 
        user_message: str, 
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process a direct message (required by BaseAgent).
        Note: Executors primarily work via execute_subtask(), not direct messaging.
        
        Args:
            user_message: User's input message
            user_context: Optional user context data
            
        Returns:
            Agent's response message
        """
        return f"[{self.executor_id}] Executor agents work via execute_subtask() method. Use that for task execution."

    def get_metadata(self) -> Dict[str, Any]:
        """Get executor metadata"""
        return self.metadata.copy()
