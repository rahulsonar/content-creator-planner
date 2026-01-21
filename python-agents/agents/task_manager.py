"""
User Task Manager Agent
Manages user tasks: create, search, update operations
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import json
import traceback
from agents.base import BaseAgent
from config.prompts import PLANNING_SYSTEM_PROMPT
from utils.logger import logger
from utils.task_inserter import insert_tasks_to_db
from utils.task_updater import update_task_by_id, update_tasks_batch
from storage.database import db_manager
from storage.agent_call_log import agent_call_logger


class UserTaskManagerAgent(BaseAgent):
    """Agent for managing user's tasks with unified action-based tool"""
    
    def __init__(self, model_client):
        """
        Initialize user task manager agent
        
        Args:
            model_client: LLM client (OpenAI)
        """
        super().__init__(model_client, "task_manager")
        self._current_user_id = None
        self._current_conversation_id = None
        self._current_message_id = None
        self._current_log_id = None  # Track current agent call log
        self._tool_calls_log = []  # Track tool calls for logging
        self._tool_results_log = []  # Track tool results for logging

        # Initialize metadata
        self.metadata = {
            "agent_name": "task_manager",
            "agent_type": "task_management",
            "conversation_id": None,
            "user_id": None,
            "session_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity_at": None,
            "total_messages": 0,
            "total_user_messages": 0,
            "tool_calls_count": 0,
            "tools_by_type": {},  # Track count per tool type
            "enable_tools": True,
            "model_name": getattr(model_client, 'model', 'unknown'),
            "tasks_created": 0,
            "tasks_updated": 0,
            "tasks_searched": 0,
            "notes_added": 0,
            "agent_version": "1.0.0"
        }

        logger.info(f"UserTaskManagerAgent initialized: {self.get_metadata_summary()}")

        # Define unified task management tool
        self.tools_openai = [
            {
                "type": "function",
                "function": {
                    "name": "manage_tasks",
                    "description": "Manage user's tasks with unified actions: create new tasks (with optional notes), search existing tasks, update task details, add notes to existing tasks, or get specific task information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["create", "search", "update", "get_one", "add_notes"],
                                "description": "Task operation to perform"
                            },
                            # For 'create' action
                            "tasks": {
                                "type": "array",
                                "description": "Array of new tasks to create (for 'create' action)",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {
                                            "type": "string",
                                            "description": "Task title (concise, actionable)"
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "Detailed task description with steps"
                                        },
                                        "priority": {
                                            "type": "string",
                                            "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"],
                                            "description": "Task priority level"
                                        },
                                        "estimatedHours": {
                                            "type": "number",
                                            "description": "Estimated hours to complete"
                                        },
                                        "researchNotes": {
                                            "type": "string",
                                            "description": "Research findings or reference materials"
                                        },
                                        "aiReasoning": {
                                            "type": "string",
                                            "description": "Reasoning for including this task"
                                        },
                                        "dependencies": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "List of task titles this depends on"
                                        },
                                        "notes": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "content": {
                                                        "type": "string",
                                                        "description": "Note content"
                                                    },
                                                    "createdBy": {
                                                        "type": "string",
                                                        "description": "User ID who created the note (optional)"
                                                    }
                                                },
                                                "required": ["content"]
                                            },
                                            "description": "Notes to attach to this task"
                                        }
                                    },
                                    "required": ["title", "description", "priority", "estimatedHours"]
                                }
                            },
                            # For 'search' action
                            "keywords": {
                                "type": "string",
                                "description": "Search keywords (for 'search' action). Can search by title, description, status, or priority."
                            },
                            "status_filter": {
                                "type": "string",
                                "enum": ["TODO", "IN_PROGRESS", "REVIEW", "BLOCKED", "COMPLETED", "CANCELLED", ""],
                                "description": "Optional: Filter by task status (for 'search' action). Leave empty for no filter."
                            },
                            "priority_filter": {
                                "type": "string",
                                "enum": ["LOW", "MEDIUM", "HIGH", "URGENT", ""],
                                "description": "Optional: Filter by task priority (for 'search' action). Leave empty for no filter."
                            },
                            # For 'update' action
                            "task_updates": {
                                "type": "array",
                                "description": "Array of task updates (for 'update' action)",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {
                                            "type": "string",
                                            "description": "Task ID to update"
                                        },
                                        "title": {
                                            "type": "string",
                                            "description": "Updated task title"
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "Updated task description"
                                        },
                                        "status": {
                                            "type": "string",
                                            "enum": ["TODO", "IN_PROGRESS", "REVIEW", "BLOCKED", "COMPLETED", "CANCELLED"],
                                            "description": "Updated task status"
                                        },
                                        "priority": {
                                            "type": "string",
                                            "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"],
                                            "description": "Updated task priority"
                                        },
                                        "estimatedHours": {
                                            "type": "number",
                                            "description": "Updated estimated hours"
                                        },
                                        "actualHours": {
                                            "type": "number",
                                            "description": "Updated actual hours spent"
                                        },
                                        "startDate": {
                                            "type": "string",
                                            "description": "Updated start date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                                        },
                                        "endDate": {
                                            "type": "string",
                                            "description": "Updated end date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                                        },
                                        "dueDate": {
                                            "type": "string",
                                            "description": "Updated due date (ISO format)"
                                        },
                                        "completedAt": {
                                            "type": "string",
                                            "description": "Updated completion timestamp (ISO format)"
                                        },
                                        "assignedTo": {
                                            "type": "string",
                                            "description": "Updated assigned person"
                                        }
                                    }
                                }
                            },
                            # For 'get_one' action
                            "task_id": {
                                "type": "string",
                                "description": "Task ID to retrieve (for 'get_one' action) or add notes to (for 'add_notes' action)"
                            },
                            # For 'add_notes' action
                            "notes": {
                                "type": "array",
                                "description": "Array of notes to add to a task (for 'add_notes' action)",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "content": {
                                            "type": "string",
                                            "description": "Note content"
                                        },
                                        "createdBy": {
                                            "type": "string",
                                            "description": "User ID who created the note (optional)"
                                        }
                                    },
                                    "required": ["content"]
                                }
                            }
                        },
                        "required": ["action"]
                    }
                }
            }
        ]

        # Initialize with system prompt
        self._initialize_system_prompt()

    def _convert_anthropic_to_openai_format(self, anthropic_response):
        """
        Convert Anthropic tool response to OpenAI-style format for unified handling
        
        Args:
            anthropic_response: Anthropic API response with tool_use blocks
            
        Returns:
            Mock message object with OpenAI-style tool_calls attribute
        """
        class ToolCall:
            def __init__(self, tool_id, tool_name, tool_input):
                self.id = tool_id
                self.type = "function"
                
                class Function:
                    def __init__(self, name, arguments):
                        self.name = name
                        self.arguments = json.dumps(arguments)
                
                self.function = Function(tool_name, tool_input)
        
        class Message:
            def __init__(self, content_blocks):
                self.content = ""
                self.tool_calls = []
                
                # Extract text and tool calls from Anthropic content blocks
                for block in content_blocks:
                    if block.type == "text":
                        self.content += block.text
                    elif block.type == "tool_use":
                        tool_call = ToolCall(
                            tool_id=block.id,
                            tool_name=block.name,
                            tool_input=block.input
                        )
                        self.tool_calls.append(tool_call)
                
                # Set to None if no tool calls (OpenAI convention)
                if not self.tool_calls:
                    self.tool_calls = None
        
        return Message(anthropic_response.content)

    def _initialize_system_prompt(self):
        """Initialize the agent with system prompts"""
        #self.add_to_history("system", PLANNING_SYSTEM_PROMPT)
        self.add_to_history("system", """You are a task management specialist. Handle task creation, updates, and searches efficiently.""")
        self.add_to_history("system", "Always provide clear summaries of actions taken.")

    def update_metadata(self, **kwargs):
        """Update metadata fields and track last activity"""
        self.metadata.update(kwargs)
        self.metadata["last_activity_at"] = datetime.now(timezone.utc).isoformat()
        
        # Sync metadata with OpenAI client for API logging
        if hasattr(self.model_client, 'update_metadata'):
            client_metadata = {
                "conversation_id": self.metadata.get("conversation_id"),
                "user_id": self.metadata.get("user_id"),
                "session_id": self.metadata.get("session_id"),
                "agent_name": self.metadata.get("agent_name")
            }
            client_metadata = {k: v for k, v in client_metadata.items() if v is not None}
            if client_metadata:
                self.model_client.update_metadata(client_metadata)

    def get_metadata(self) -> Dict[str, Any]:
        """Get current metadata snapshot"""
        return self.metadata.copy()

    def get_metadata_summary(self) -> str:
        """Get formatted metadata summary for logging"""
        m = self.metadata
        return (
            f"agent={m['agent_name']}, conv={m['conversation_id']}, "
            f"user={m['user_id']}, msgs={m['total_messages']}, "
            f"tools={m['tool_calls_count']}, created={m['tasks_created']}, "
            f"updated={m['tasks_updated']}"
        )

    async def process_message(
        self,
        user_message: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process task management requests with unified tool
        
        Args:
            user_message: User's task request
            user_context: User context including user_id
            
        Returns:
            Agent's response confirming actions taken
        """
        # Update metadata at start
        if user_context:
            self.update_metadata(
                conversation_id=user_context.get('conversation_id'),
                user_id=user_context.get('user_id'),
                session_id=user_context.get('session_id')
            )

        # Increment counters
        self.metadata["total_messages"] += 1
        self.metadata["total_user_messages"] += 1

        logger.info(f"Processing message: {self.get_metadata_summary()}")

        # Store context for tool execution
        if user_context and 'user_id' in user_context:
            self._current_user_id = user_context['user_id']
            self._current_conversation_id = user_context.get('conversation_id')
            self._current_message_id = user_context.get('message_id')
        
        # Reset tool tracking for this message
        self._tool_calls_log = []
        self._tool_results_log = []
        
        # START AGENT CALL LOGGING
        try:
            self._current_log_id = await agent_call_logger.start_agent_call(
                user_id=self._current_user_id or "unknown",
                agent_name="task_manager",
                model_name=self.metadata.get("model_name", "unknown"),
                message_id=self._current_message_id or agent_call_logger.generate_message_id(),
                conversation_id=self._current_conversation_id,
                session_id=user_context.get('session_id') if user_context else None,
                agent_type="task_management",
                agent_version=self.metadata.get("agent_version", "1.0.0"),
                input_message=user_message,
                tools_enabled=True,
                metadata={
                    "conversation_history_length": len(self.conversation_history),
                    "has_context": bool(user_context)
                },
                tags=["task_manager", "task_management"]
            )
            logger.info(f"Started agent call log: {self._current_log_id}")
        except Exception as e:
            logger.error(f"Failed to start agent call logging: {e}")

        # Add user message to history
        if not self.conversation_history or self.conversation_history[-1].get("content") != user_message:
            self.add_to_history("user", user_message)

        try:
            # Iterative tool calling loop - continue until agent stops calling tools
            max_iterations = 5  # Prevent infinite loops
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                
                # Generate response with tools based on client type
                is_anthropic = hasattr(self.model_client, 'client_type') and self.model_client.client_type == 'anthropic'
                is_openai = hasattr(self.model_client, 'client') and hasattr(self.model_client.client, 'chat')
                
                if is_openai:
                    # OpenAI format
                    response = await self._generate_with_tools_openai()
                    message = response.choices[0].message
                elif is_anthropic:
                    # Anthropic format - pass tools and get full response
                    response = await self.model_client.generate_completion(
                        messages=self.conversation_history,
                        tools=self.tools_openai  # Will be converted to Anthropic format
                    )
                    
                    # Check if Anthropic returned a tool use response
                    if hasattr(response, 'stop_reason') and response.stop_reason == "tool_use":
                        # Convert Anthropic response to OpenAI-style format for unified handling
                        message = self._convert_anthropic_to_openai_format(response)
                    else:
                        # Regular text response
                        content = ""
                        if hasattr(response, 'content'):
                            for block in response.content:
                                if block.type == "text":
                                    content += block.text
                        else:
                            content = str(response)
                        
                        class MockMessage:
                            def __init__(self, content):
                                self.content = content
                                self.tool_calls = None
                        message = MockMessage(content)
                else:
                    # Fallback for other clients (no tool support)
                    response = await self.model_client.generate_completion(
                        messages=self.conversation_history,
                    )
                    class MockMessage:
                        def __init__(self, content):
                            self.content = content
                            self.tool_calls = None
                    message = MockMessage(response)
                
                # Handle tool calls
                if message.tool_calls:
                    logger.info(f"Tool calls detected (iteration {iteration}): {[tc.function.name for tc in message.tool_calls]}")
                    
                    # Track tool calls for logging
                    for tc in message.tool_calls:
                        self._tool_calls_log.append({
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        })
                    
                    tool_results = await self._execute_tools_openai(message.tool_calls)
                    
                    # Track tool results for logging
                    self._tool_results_log.extend(tool_results)
                    
                    # Add assistant message with tool calls to history
                    self.add_to_history("assistant", {
                        "content": message.content,
                        "tool_calls": [{
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in message.tool_calls]
                    })
                    
                    # Add tool results to history
                    for tool_result in tool_results:
                        self.add_to_history("tool", tool_result["result"], tool_result.get("tool_call_id"))
                    
                    # Continue loop to check for more tool calls
                    continue
                else:
                    # No more tool calls - return final message
                    final_response = message.content if message.content else "Task management completed."
                    if message.content:
                        self.add_to_history("assistant", message.content)
                    
                    # COMPLETE AGENT CALL LOGGING
                    try:
                        await agent_call_logger.complete_agent_call(
                            log_id=self._current_log_id,
                            output_message=final_response,
                            tool_calls=self._tool_calls_log if self._tool_calls_log else None,
                            tool_results=self._tool_results_log if self._tool_results_log else None,
                            metadata={
                                "iterations": iteration,
                                "final_history_length": len(self.conversation_history),
                                "tasks_created": self.metadata.get("tasks_created", 0),
                                "tasks_updated": self.metadata.get("tasks_updated", 0),
                                "tasks_searched": self.metadata.get("tasks_searched", 0),
                                "tool_calls_count": len(self._tool_calls_log)
                            }
                        )
                        logger.info(f"Completed agent call log: {self._current_log_id}")
                    except Exception as log_error:
                        logger.error(f"Failed to complete agent call logging: {log_error}")
                    
                    return final_response
            
            # Max iterations reached
            logger.warning(f"Max iterations ({max_iterations}) reached in tool calling loop")
            final_msg = "Task operations completed (max iterations reached)."
            
            # COMPLETE AGENT CALL LOGGING
            try:
                await agent_call_logger.complete_agent_call(
                    log_id=self._current_log_id,
                    output_message=final_msg,
                    tool_calls=self._tool_calls_log if self._tool_calls_log else None,
                    tool_results=self._tool_results_log if self._tool_results_log else None,
                    metadata={
                        "iterations": max_iterations,
                        "max_iterations_reached": True,
                        "tool_calls_count": len(self._tool_calls_log)
                    }
                )
            except Exception as log_error:
                logger.error(f"Failed to complete agent call logging: {log_error}")
            
            return final_msg
                
        except Exception as e:
            logger.error(f"Error in task manager: {e}", exc_info=True)
            error_msg = f"Error processing task request: {str(e)}"
            
            # FAIL AGENT CALL LOGGING
            try:
                await agent_call_logger.fail_agent_call(
                    log_id=self._current_log_id,
                    error=str(e),
                    error_type="processing_error",
                    stack_trace=traceback.format_exc(),
                    metadata={"error_location": "process_message"}
                )
                logger.error(f"Failed agent call log: {self._current_log_id}")
            except Exception as log_error:
                logger.error(f"Failed to log agent call failure: {log_error}")
            
            return error_msg

    async def _generate_with_tools_openai(self):
        """Generate response using OpenAI tools"""
        response = await self.model_client.generate_completion(
            messages=self.conversation_history,
            tools=self.tools_openai
        )
        return response

    async def _execute_tools_openai(self, tool_calls) -> List[Dict[str, Any]]:
        """Execute OpenAI tool calls"""
        results = []
        
        # Log tool calls
        tool_calls_data = [{
            "call_id": tc.id,
            "name": tc.function.name,
            "arguments": json.loads(tc.function.arguments),
            "timestamp": datetime.now(timezone.utc).isoformat()
        } for tc in tool_calls]
        
        try:
            await agent_call_logger.update_tool_calls(self._current_log_id, tool_calls_data)
            logger.info(f"Logged {len(tool_calls)} tool calls")
        except Exception as e:
            logger.error(f"Failed to log tool calls: {e}")
        
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            
            logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
            self.metadata["tool_calls_count"] += 1
            
            try:
                if tool_name == "manage_tasks":
                    result = await self._handle_manage_tasks(tool_args)
                else:
                    result = f"Unknown tool: {tool_name}"
                
                logger.info(f"Tool {tool_name} completed successfully")
                results.append({
                    "tool_call_id": tool_call.id,
                    "result": result,
                    "success": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                logger.error(f"Tool execution failed: {tool_name} - {e}", exc_info=True)
                results.append({
                    "tool_call_id": tool_call.id,
                    "result": f"Error executing tool: {str(e)}",
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
        
        # Log tool results
        try:
            await agent_call_logger.update_tool_results(self._current_log_id, results)
            logger.info(f"Logged {len(results)} tool results")
        except Exception as e:
            logger.error(f"Failed to log tool results: {e}")
        
        return results

    async def _handle_manage_tasks(self, args: Dict[str, Any]) -> str:
        """Handle manage_tasks tool with action routing"""
        action = args.get("action")
        
        logger.info(f"[TASK_MANAGER] Manage tasks action: {action}, args: {args}")
        
        if action == "create":
            return await self._create_tasks(args.get("tasks", []))
        elif action == "search":
            return await self._search_tasks(
                args.get("keywords", ""),
                args.get("status_filter", ""),
                args.get("priority_filter", "")
            )
        elif action == "update":
            return await self._update_tasks(args.get("task_updates", []))
        elif action == "get_one":
            return await self._get_task(args.get("task_id", ""))
        elif action == "add_notes":
            return await self._add_notes(args.get("task_id", ""), args.get("notes", []))
        else:
            return f"Unknown action: {action}"

    async def _create_tasks(self, tasks: List[Dict[str, Any]]) -> str:
        """Create new tasks in database"""
        if not tasks:
            return "No tasks provided to create."
        
        try:
            logger.info(f"Creating {len(tasks)} tasks")
            result = await insert_tasks_to_db(tasks)
            self.metadata["tasks_created"] += len(tasks)
            
            if result.get("success"):
                created_ids = result.get("created_ids", [])
                summary = f"✓ Created {len(tasks)} tasks successfully"
                if created_ids:
                    summary += f" (IDs: {', '.join(str(id)[:8] for id in created_ids)})"
                logger.info(summary)
                return summary
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Task creation failed: {error_msg}")
                return f"✗ Failed to create tasks: {error_msg}"
        except Exception as e:
            logger.error(f"Exception creating tasks: {e}", exc_info=True)
            return f"✗ Error creating tasks: {str(e)}"

    async def _search_tasks(self, keywords: str = "", status_filter: str = "", priority_filter: str = "") -> str:
        """Search tasks by keywords and filters"""
        import asyncpg
        from config.settings import settings
        
        # Log search query parameters
        logger.info(f"Search query - keywords: '{keywords}', status: '{status_filter}', priority: '{priority_filter}'")
        
        conn = None
        try:
            # Connect to database
            db_url = settings.DATABASE_URL
            conn = await asyncpg.connect(db_url)
            
            # Build search query
            where_clauses = []
            params = []
            param_index = 1
            
            # Add status filter
            if status_filter and status_filter.strip():
                where_clauses.append(f'status = ${param_index}')
                params.append(status_filter)
                param_index += 1
            
            # Add priority filter
            if priority_filter and priority_filter.strip():
                where_clauses.append(f'priority = ${param_index}')
                params.append(priority_filter)
                param_index += 1
            
            # Build WHERE clause
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f"""
                SELECT t.id, t.title, t.description, t.status, t.priority, 
                       t."estimatedHours", t."actualHours", t."startDate", t."endDate",
                       t."dueDate", t."createdAt", t."updatedAt",
                       json_agg(
                           json_build_object(
                               'id', tn.id,
                               'content', tn.content,
                               'createdBy', tn."createdBy",
                               'createdAt', tn."createdAt"
                           ) ORDER BY tn."createdAt" DESC
                       ) FILTER (WHERE tn.id IS NOT NULL) as notes
                FROM "Task" t
                LEFT JOIN "TaskNote" tn ON t.id = tn."taskId"
                WHERE {where_sql}
                GROUP BY t.id
                ORDER BY t."createdAt" DESC
                LIMIT 100
            """
            
            rows = await conn.fetch(query, *params)
            
            # Filter by keywords in both title AND description if provided
            if keywords and keywords.strip():
                keywords_lower = keywords.lower()
                logger.info(f"Filtering tasks by keywords in title and description: '{keywords_lower}'")
                filtered_rows = []
                for row in rows:
                    title = (row['title'] or "").lower()
                    description = (row['description'] or "").lower()
                    # Search in both title AND description
                    if keywords_lower in title or keywords_lower in description:
                        filtered_rows.append(row)
                logger.info(f"Keywords filter: {len(rows)} tasks -> {len(filtered_rows)} tasks matched")
                rows = filtered_rows
            
            # If no results found, fetch all tasks and note the fallback
            fallback_occurred = False
            if not rows:
                logger.info("No tasks matched search criteria, returning all tasks")
                fallback_occurred = True
                all_tasks_query = """
                    SELECT t.id, t.title, t.description, t.status, t.priority, 
                           t."estimatedHours", t."actualHours", t."startDate", t."endDate",
                           t."dueDate", t."createdAt", t."updatedAt",
                           json_agg(
                               json_build_object(
                                   'id', tn.id,
                                   'content', tn.content,
                                   'createdBy', tn."createdBy",
                                   'createdAt', tn."createdAt"
                               ) ORDER BY tn."createdAt" DESC
                           ) FILTER (WHERE tn.id IS NOT NULL) as notes
                    FROM "Task" t
                    LEFT JOIN "TaskNote" tn ON t.id = tn."taskId"
                    GROUP BY t.id
                    ORDER BY t."createdAt" DESC
                    LIMIT 100
                """
                rows = await conn.fetch(all_tasks_query)
            
            self.metadata["tasks_searched"] += 1
            
            # Format task list
            if fallback_occurred:
                summary = f"No tasks matched the search criteria (keywords: '{keywords}', status: '{status_filter}', priority: '{priority_filter}'). Showing all {len(rows)} task(s) instead:\n"
            else:
                summary = f"Found {len(rows)} task(s):\n"
            for row in rows[:10]:  # Limit to 10 tasks
                task_id = row['id']
                title = row['title']
                status = row['status']
                priority = row['priority']
                
                # Safely count notes with type checking
                notes_count = 0
                if row['notes']:
                    notes = row['notes']
                    if isinstance(notes, str):
                        try:
                            notes = json.loads(notes)
                            notes_count = len(notes) if isinstance(notes, list) else 0
                        except json.JSONDecodeError:
                            notes_count = 0
                    elif isinstance(notes, list):
                        notes_count = len(notes)
                
                notes_suffix = f" [{notes_count} notes]" if notes_count > 0 else ""
                summary += f"  • [{status}] {title} (Priority: {priority}, ID: {task_id}){notes_suffix}\n"
            
            if len(rows) > 10:
                summary += f"  ... and {len(rows) - 10} more tasks"
            
            logger.info(f"Search returned {len(rows)} tasks")
            return summary
            
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return f"✗ Error searching tasks: {str(e)}"
        finally:
            if conn:
                await conn.close()

    async def _update_tasks(self, task_updates: List[Dict[str, Any]]) -> str:
        """Update existing tasks"""
        if not task_updates:
            return "No task updates provided."
        
        try:
            logger.info(f"Updating {len(task_updates)} tasks")
            success_count = 0
            
            for update in task_updates:
                task_id = update.get("id")
                if not task_id:
                    logger.warning("Task update missing ID, skipping")
                    continue
                
                # Remove id from update dict before passing to updater
                update_data = {k: v for k, v in update.items() if k != "id"}
                
                result = await update_task_by_id(task_id, update_data)
                if result:  # result is a boolean
                    success_count += 1
                else:
                    logger.warning(f"Failed to update task {task_id}")
            
            self.metadata["tasks_updated"] += success_count
            
            summary = f"✓ Updated {success_count}/{len(task_updates)} tasks successfully"
            logger.info(summary)
            return summary
        except Exception as e:
            logger.error(f"Exception updating tasks: {e}", exc_info=True)
            return f"✗ Error updating tasks: {str(e)}"

    async def _get_task(self, task_id: str) -> str:
        """Get a specific task"""
        import asyncpg
        from config.settings import settings
        
        if not task_id:
            return "Error: task_id is required"
        
        conn = None
        try:
            # Connect to database
            db_url = settings.DATABASE_URL
            conn = await asyncpg.connect(db_url)
            
            query = """
                SELECT t.id, t.title, t.description, t.status, t.priority, 
                       t."estimatedHours", t."actualHours", t."startDate", t."endDate",
                       t."dueDate", t."createdAt", t."updatedAt",
                       json_agg(
                           json_build_object(
                               'id', tn.id,
                               'content', tn.content,
                               'createdBy', tn."createdBy",
                               'createdAt', tn."createdAt"
                           ) ORDER BY tn."createdAt" DESC
                       ) FILTER (WHERE tn.id IS NOT NULL) as notes
                FROM "Task" t
                LEFT JOIN "TaskNote" tn ON t.id = tn."taskId"
                WHERE t.id = $1
                GROUP BY t.id
            """
            
            logger.info(f"Fetching task with ID: {task_id}")
            row = await conn.fetchrow(query, task_id)
            
            if not row:
                logger.warning(f"Task not found: {task_id}")
                return f"Task {task_id} not found"
            
            # Safely extract values with type checking
            description = str(row['description'] or "")
            desc_preview = description[:100] + "..." if len(description) > 100 else description
            
            # Format notes if present
            notes_text = ""
            if row['notes']:
                # Parse notes if they're a JSON string
                notes = row['notes']
                if isinstance(notes, str):
                    try:
                        notes = json.loads(notes)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse notes JSON: {notes}")
                        notes = []
                
                if notes:
                    notes_text = f"\n  • Notes ({len(notes)}):"
                    for note in notes[:3]:  # Show first 3 notes
                        # Handle both dict and string cases
                        if isinstance(note, dict):
                            note_content = str(note.get('content', ''))
                        elif isinstance(note, str):
                            note_content = note
                        else:
                            note_content = str(note)
                        
                        note_preview = note_content[:80] + "..." if len(note_content) > 80 else note_content
                        notes_text += f"\n    - {note_preview}"
                    if len(notes) > 3:
                        notes_text += f"\n    ... and {len(notes) - 3} more notes"
            
            summary = f"""Task Details:
  • ID: {row['id']}
  • Title: {row['title']}
  • Status: {row['status']}
  • Priority: {row['priority']}
  • Estimated: {row['estimatedHours']}h
  • Actual: {row['actualHours']}h
  • Description: {desc_preview}{notes_text}"""
            
            logger.info(f"Successfully retrieved task: {task_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Error fetching task {task_id}: {e}", exc_info=True)
            return f"Error retrieving task: {str(e)}"
        finally:
            if conn:
                await conn.close()

    async def _add_notes(self, task_id: str, notes: List[Dict[str, Any]]) -> str:
        """Add notes to an existing task"""
        import asyncpg
        from config.settings import settings
        
        if not task_id:
            return "Error: task_id is required"
        
        if not notes:
            return "Error: at least one note is required"
        
        conn = None
        try:
            # Connect to database
            db_url = settings.DATABASE_URL
            conn = await asyncpg.connect(db_url)
            
            # Verify task exists
            task_check = await conn.fetchval('SELECT id FROM "Task" WHERE id = $1', task_id)
            if not task_check:
                return f"Task {task_id} not found"
            
            # Insert notes
            notes_added = 0
            for note in notes:
                if isinstance(note, dict) and note.get("content"):
                    note_query = """
                        INSERT INTO "TaskNote" (
                            id, "taskId", content, "createdBy",
                            "createdAt", "updatedAt"
                        ) VALUES (
                            gen_random_uuid()::text, $1, $2, $3,
                            NOW(), NOW()
                        )
                    """
                    await conn.execute(
                        note_query,
                        task_id,
                        note.get("content"),
                        note.get("createdBy")
                    )
                    notes_added += 1
                    logger.info(f"Added note to task: {task_id}")
            
            self.metadata["notes_added"] += notes_added
            
            summary = f"✓ Added {notes_added} note(s) to task {task_id[:8]}..."
            logger.info(summary)
            return summary
            
        except Exception as e:
            logger.error(f"Error adding notes to task {task_id}: {e}", exc_info=True)
            return f"✗ Error adding notes: {str(e)}"
        finally:
            if conn:
                await conn.close()
