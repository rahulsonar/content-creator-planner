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
from schemas.responses import TaskManagerResponse
from utils.logger import logger
from utils.task_inserter import insert_tasks_to_db
from utils.task_updater import update_task_by_id, update_tasks_batch
from utils.project_manager import insert_projects_to_db, get_project_by_id, list_projects
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
            "projects_created": 0,
            "projects_viewed": 0,
            "projects_listed": 0,
            "agent_version": "1.0.0"
        }

        logger.info(f"UserTaskManagerAgent initialized: {self.get_metadata_summary()}")

        # Define unified task management tool
        self.tools_openai = [
            {
                "type": "function",
                "function": {
                    "name": "manage_tasks",
                    "description": "Manage user's tasks with unified actions: create new tasks (with optional notes), search existing tasks (supports keywords, status, priority, project, and label/tag filters), update task details, add notes to existing tasks, or get specific task information.",
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
                                        "taskKey": {
                                            "type": "string",
                                            "description": "Optional human-friendly task key (e.g., 'CP-001'). If not provided, will be auto-generated."
                                        },
                                        "title": {
                                            "type": "string",
                                            "description": "Task title (concise, actionable)"
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "Detailed task description with steps"
                                        },
                                        "status": {
                                            "type": "string",
                                            "enum": ["TODO", "IN_PROGRESS", "REVIEW", "BLOCKED", "COMPLETED", "CANCELLED"],
                                            "description": "Task status (defaults to TODO)"
                                        },
                                        "priority": {
                                            "type": "string",
                                            "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"],
                                            "description": "Task priority level (defaults to MEDIUM)"
                                        },
                                        "startDate": {
                                            "type": "string",
                                            "description": "Task start date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                                        },
                                        "endDate": {
                                            "type": "string",
                                            "description": "Task end date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                                        },
                                        "dueDate": {
                                            "type": "string",
                                            "description": "Task due date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                                        },
                                        "estimatedHours": {
                                            "type": "number",
                                            "description": "Estimated hours to complete"
                                        },
                                        "actualHours": {
                                            "type": "number",
                                            "description": "Actual hours spent on task"
                                        },
                                        "projectId": {
                                            "type": "string",
                                            "description": "Project ID to attach this task to"
                                        },
                                        "parentId": {
                                            "type": "integer",
                                            "description": "Parent task ID for creating subtasks"
                                        },
                                        "assignedTo": {
                                            "type": "string",
                                            "description": "User ID or name of person assigned to this task"
                                        },
                                        "aiGenerated": {
                                            "type": "boolean",
                                            "description": "Whether this task was AI-generated"
                                        },
                                        "aiSuggestions": {
                                            "type": "string",
                                            "description": "AI suggestions for completing this task"
                                        },
                                        "aiContext": {
                                            "type": "string",
                                            "description": "AI context or reasoning for including this task"
                                        },
                                        "dependencies": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "taskId": {
                                                        "type": "integer",
                                                        "description": "ID of the related task"
                                                    },
                                                    "type": {
                                                        "type": "string",
                                                        "enum": ["blockedBy", "blocks"],
                                                        "description": "Dependency type: 'blockedBy' means this task is blocked by the referenced task, 'blocks' means this task blocks the referenced task"
                                                    }
                                                },
                                                "required": ["taskId", "type"]
                                            },
                                            "description": "List of task dependencies with blockedBy/blocks relationships"
                                        },
                                        "labels": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Labels to attach to this task"
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
                                "description": "Search keywords (for 'search' action). Matches title or description."
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
                            "project_filter": {
                                "type": "string",
                                "description": "Optional: Filter by project ID (for 'search' action). Leave empty for no filter."
                            },
                            "tag_filter": {
                                "type": "string",
                                "description": "Optional: Filter by tag/label (for 'search' action). Leave empty for no filter."
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
                                        "projectId": {
                                            "type": "string",
                                            "description": "Updated project ID to attach this task to"
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
                                        },
                                        "parentId": {
                                            "type": "integer",
                                            "description": "Updated parent task ID"
                                        },
                                        "aiGenerated": {
                                            "type": "boolean",
                                            "description": "Updated AI-generated flag"
                                        },
                                        "aiSuggestions": {
                                            "type": "string",
                                            "description": "Updated AI suggestions"
                                        },
                                        "aiContext": {
                                            "type": "string",
                                            "description": "Updated AI context"
                                        },
                                        "labels": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Updated labels to attach (replaces existing labels)"
                                        },
                                        "dependencies": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "taskId": {
                                                        "type": "integer",
                                                        "description": "ID of the related task"
                                                    },
                                                    "type": {
                                                        "type": "string",
                                                        "enum": ["blockedBy", "blocks"],
                                                        "description": "Dependency type: 'blockedBy' means this task is blocked by the referenced task, 'blocks' means this task blocks the referenced task"
                                                    }
                                                },
                                                "required": ["taskId", "type"]
                                            },
                                            "description": "Updated dependencies with blockedBy/blocks relationships (replaces existing dependencies)"
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
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_projects",
                    "description": "Manage user's projects with unified actions: create new projects, view a specific project, or list all projects with optional status filter.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["create", "view", "list"],
                                "description": "Project operation to perform"
                            },
                            # For 'create' action
                            "projects": {
                                "type": "array",
                                "description": "Array of new projects to create (for 'create' action)",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "Project name (concise, descriptive)"
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "Detailed project description"
                                        },
                                        "status": {
                                            "type": "string",
                                            "enum": ["ACTIVE", "ON_HOLD", "COMPLETED", "ARCHIVED", "CANCELLED"],
                                            "description": "Project status (defaults to ACTIVE)"
                                        },
                                        "color": {
                                            "type": "string",
                                            "description": "Hex color code for UI (e.g., #FF5733)"
                                        },
                                        "icon": {
                                            "type": "string",
                                            "description": "Icon name or emoji for UI (e.g., 📹, 🎬)"
                                        },
                                        "tags": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Project tags for categorization"
                                        },
                                        "startDate": {
                                            "type": "string",
                                            "description": "Project start date (ISO format: YYYY-MM-DD)"
                                        },
                                        "endDate": {
                                            "type": "string",
                                            "description": "Project end date (ISO format: YYYY-MM-DD)"
                                        },
                                        "dueDate": {
                                            "type": "string",
                                            "description": "Project due date (ISO format: YYYY-MM-DD)"
                                        },
                                        "isDefault": {
                                            "type": "boolean",
                                            "description": "Whether this project should be the default"
                                        }
                                    },
                                    "required": ["name"]
                                }
                            },
                            # For 'view' action
                            "project_id": {
                                "type": "string",
                                "description": "Project ID to view (for 'view' action)"
                            },
                            # For 'list' action
                            "status_filter": {
                                "type": "string",
                                "enum": ["ACTIVE", "ON_HOLD", "COMPLETED", "ARCHIVED", "CANCELLED", ""],
                                "description": "Optional: Filter projects by status (for 'list' action). Leave empty for no filter."
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
        self.add_to_history("system", """You are a task and project management specialist. Handle task creation, updates, searches, and project management (create, view, list) efficiently.""")
        self.add_to_history("system", "Always provide clear summaries of actions taken.")
        
        # For Anthropic clients, explicitly mention tool availability
        is_anthropic = hasattr(self.model_client, 'client_type') and self.model_client.client_type == 'anthropic'
        if is_anthropic:
            self.add_to_history("system", "You have manage_tasks and manage_projects tools available - use them to complete all operations.")

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
            f"tools={m['tool_calls_count']}, tasks_created={m['tasks_created']}, "
            f"tasks_updated={m['tasks_updated']}, projects_created={m['projects_created']}"
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
            max_iterations = 20  # Prevent infinite loops
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
                elif tool_name == "manage_projects":
                    result = await self._handle_manage_projects(tool_args)
                else:
                    result = {"status": "error", "message": f"Unknown tool: {tool_name}", "error": f"Unknown tool: {tool_name}"}
                
                logger.info(f"Tool {tool_name} completed successfully")
                # Convert dict result to JSON string for agent history
                result_str = json.dumps(result) if isinstance(result, dict) else str(result)
                results.append({
                    "tool_call_id": tool_call.id,
                    "result": result_str,
                    "success": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                logger.error(f"Tool execution failed: {tool_name} - {e}", exc_info=True)
                error_result = {"status": "error", "message": f"Error executing tool", "error": str(e)}
                results.append({
                    "tool_call_id": tool_call.id,
                    "result": json.dumps(error_result),
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

    async def _handle_manage_tasks(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle manage_tasks tool with action routing and return structured response"""
        action = args.get("action")
        
        logger.info(f"[TASK_MANAGER] Manage tasks action: {action}, args: {args}")
        
        if action == "create":
            return await self._create_tasks(args.get("tasks", []))
        elif action == "search":
            return await self._search_tasks(
                args.get("keywords", ""),
                args.get("status_filter", ""),
                args.get("priority_filter", ""),
                args.get("project_filter", ""),
                args.get("tag_filter", "")
            )
        elif action == "update":
            return await self._update_tasks(args.get("task_updates", []))
        elif action == "get_one":
            return await self._get_task(args.get("task_id", ""))
        elif action == "add_notes":
            return await self._add_notes(args.get("task_id", ""), args.get("notes", []))
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}",
                "error": f"Unknown action: {action}"
            }

    async def _create_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create new tasks in database and return structured response"""
        if not tasks:
            return {
                "status": "error",
                "action": "create",
                "message": "No tasks provided to create",
                "error": "Empty task list"
            }
        
        if not self._current_user_id:
            logger.error("No user_id available for task creation")
            return {
                "status": "error",
                "action": "create",
                "message": "Failed to create tasks",
                "error": "User ID is required to create tasks"
            }
        
        try:
            for task in tasks:
                if isinstance(task, dict) and "labels" in task and "tags" not in task:
                    task["tags"] = task.get("labels")
            logger.info(f"Creating {len(tasks)} tasks for user {self._current_user_id}")
            result = await insert_tasks_to_db(tasks, user_id=self._current_user_id)
            self.metadata["tasks_created"] += len(tasks)
            
            if result.get("success"):
                created_ids = result.get("created_ids", [])
                logger.info(f"Successfully created {len(tasks)} tasks")
                return {
                    "status": "success",
                    "action": "create",
                    "message": f"Created {len(tasks)} tasks successfully. To attach to a project, include projectId in each task",
                    "data": {
                        "created_count": len(tasks),
                        "task_ids": [str(id) for id in created_ids]
                    }
                }
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Task creation failed: {error_msg}")
                return {
                    "status": "error",
                    "action": "create",
                    "message": "Failed to create tasks",
                    "error": error_msg
                }
        except Exception as e:
            logger.error(f"Exception creating tasks: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "create",
                "message": "Error creating tasks",
                "error": str(e)
            }

    async def _search_tasks(
        self,
        keywords: str = "",
        status_filter: str = "",
        priority_filter: str = "",
        project_filter: str = "",
        tag_filter: str = ""
    ) -> Dict[str, Any]:
        """Search tasks by keywords and filters and return structured response"""
        import asyncpg
        from config.settings import settings
        
        # Log search query parameters
        logger.info(
            "Search query - keywords: '%s', status: '%s', priority: '%s', project: '%s', tag: '%s'",
            keywords,
            status_filter,
            priority_filter,
            project_filter,
            tag_filter
        )
        
        conn = None
        try:
            # Connect to database
            db_url = settings.DATABASE_URL
            conn = await asyncpg.connect(db_url)
            
            # Build search query
            where_clauses = []
            params = []
            param_index = 1
            
            # CRITICAL: Add user_id filter to only show user's tasks
            if self._current_user_id:
                where_clauses.append(f't."userId" = ${param_index}')
                params.append(self._current_user_id)
                param_index += 1
                logger.info(f"Filtering tasks by user_id: {self._current_user_id}")
            else:
                logger.warning("No user_id available - returning all tasks (this should not happen)")
            
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

            # Add project filter
            if project_filter and project_filter.strip():
                where_clauses.append(f't."projectId" = ${param_index}')
                params.append(project_filter)
                param_index += 1

            # Add keyword filter (title OR description)
            if keywords and keywords.strip():
                where_clauses.append(f'(t.title ILIKE ${param_index} OR t.description ILIKE ${param_index})')
                params.append(f"%{keywords.strip()}%")
                param_index += 1

            # Add tag/label filter (matches any tag in array)
            if tag_filter and tag_filter.strip():
                where_clauses.append(
                    f'EXISTS (SELECT 1 FROM unnest(t.tags) tag WHERE tag ILIKE ${param_index})'
                )
                params.append(tag_filter.strip())
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
            
            self.metadata["tasks_searched"] += 1
            
            # Build task list
            tasks = []
            for row in rows:
                task_dict = {
                    "id": str(row['id']),
                    "title": row['title'],
                    "status": row['status'],
                    "priority": row['priority'],
                    "estimatedHours": row['estimatedHours'],
                    "actualHours": row['actualHours'],
                    "dueDate": str(row['dueDate']) if row['dueDate'] else None,
                    "notesCount": 0
                }
                
                # Count notes safely
                if row['notes']:
                    notes = row['notes']
                    if isinstance(notes, str):
                        try:
                            notes = json.loads(notes)
                            task_dict["notesCount"] = len(notes) if isinstance(notes, list) else 0
                        except json.JSONDecodeError:
                            pass
                    elif isinstance(notes, list):
                        task_dict["notesCount"] = len(notes)
                
                tasks.append(task_dict)
            
            logger.info(f"Search returned {len(rows)} tasks")
            
            return {
                "status": "success",
                "action": "search",
                "message": f"Found {len(rows)} task(s)",
                "data": {
                    "total_count": len(rows),
                    "returned_count": min(len(rows), 100),
                    "tasks": tasks
                }
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "search",
                "message": "Error searching tasks",
                "error": str(e)
            }
        finally:
            if conn:
                await conn.close()

    async def _update_tasks(self, task_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update existing tasks and return structured response"""
        if not task_updates:
            return {
                "status": "error",
                "action": "update",
                "message": "No task updates provided",
                "error": "Empty updates list"
            }
        
        try:
            logger.info(f"Updating {len(task_updates)} tasks")
            success_count = 0
            failed_updates = []
            
            for update in task_updates:
                task_id = update.get("id")
                if not task_id:
                    logger.warning("Task update missing ID, skipping")
                    failed_updates.append({"error": "Missing task ID"})
                    continue
                
                # Remove id from update dict before passing to updater
                update_data = {k: v for k, v in update.items() if k != "id"}
                if "labels" in update_data and "tags" not in update_data:
                    update_data["tags"] = update_data.get("labels")
                    update_data.pop("labels", None)
                
                result = await update_task_by_id(task_id, update_data, user_id=self._current_user_id)
                if result:  # result is a boolean
                    success_count += 1
                else:
                    logger.warning(f"Failed to update task {task_id}")
                    failed_updates.append({"task_id": task_id, "error": "Update failed"})
            
            self.metadata["tasks_updated"] += success_count
            
            logger.info(f"Updated {success_count}/{len(task_updates)} tasks")
            
            return {
                "status": "success" if success_count == len(task_updates) else "partial",
                "action": "update",
                "message": f"Updated {success_count}/{len(task_updates)} tasks successfully",
                "data": {
                    "updated_count": success_count,
                    "total_count": len(task_updates),
                    "failed_count": len(failed_updates),
                    "failed_updates": failed_updates if failed_updates else None
                }
            }
        except Exception as e:
            logger.error(f"Exception updating tasks: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "update",
                "message": "Error updating tasks",
                "error": str(e)
            }

    async def _get_task(self, task_id: str) -> Dict[str, Any]:
        """Get a specific task and return structured response"""
        import asyncpg
        from config.settings import settings
        
        if not task_id:
            return {
                "status": "error",
                "action": "get_one",
                "message": "Task ID is required",
                "error": "Missing task_id parameter"
            }
        
        conn = None
        try:
            # Convert task_id to integer (Task.id is Int in schema)
            try:
                task_id_int = int(task_id)
            except (ValueError, TypeError):
                return {
                    "status": "error",
                    "action": "get_one",
                    "message": f"Invalid task ID: {task_id}",
                    "error": "Task ID must be a valid integer"
                }
            
            # Connect to database
            db_url = settings.DATABASE_URL
            conn = await asyncpg.connect(db_url)
            
            # Build WHERE clause with user_id filter for security
            where_clauses = ["t.id = $1"]
            params = [task_id_int]
            
            if self._current_user_id:
                where_clauses.append('t."userId" = $2')
                params.append(self._current_user_id)
                logger.info(f"Fetching task {task_id} for user {self._current_user_id}")
            else:
                logger.warning("No user_id available for task retrieval")
            
            where_sql = " AND ".join(where_clauses)
            
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
                       ) FILTER (WHERE tn.id IS NOT NULL) as notes,
                       json_agg(
                           json_build_object(
                               'taskId', td_blocked."blockingId",
                               'type', 'blockedBy'
                           )
                       ) FILTER (WHERE td_blocked.id IS NOT NULL) as blocked_by,
                       json_agg(
                           json_build_object(
                               'taskId', td_blocks."dependentId",
                               'type', 'blocks'
                           )
                       ) FILTER (WHERE td_blocks.id IS NOT NULL) as blocks
                FROM "Task" t
                LEFT JOIN "TaskNote" tn ON t.id = tn."taskId"
                LEFT JOIN "TaskDependency" td_blocked ON t.id = td_blocked."dependentId"
                LEFT JOIN "TaskDependency" td_blocks ON t.id = td_blocks."blockingId"
                WHERE {where_sql}
                GROUP BY t.id
            """
            
            row = await conn.fetchrow(query, *params)
            
            if not row:
                logger.warning(f"Task not found: {task_id}")
                return {
                    "status": "error",
                    "action": "get_one",
                    "message": f"Task {task_id} not found",
                    "error": "Task does not exist or access denied"
                }
            
            # Build task data
            task_data = {
                "id": str(row['id']),
                "title": row['title'],
                "description": row['description'] or "",
                "status": row['status'],
                "priority": row['priority'],
                "estimatedHours": row['estimatedHours'],
                "actualHours": row['actualHours'],
                "startDate": str(row['startDate']) if row['startDate'] else None,
                "endDate": str(row['endDate']) if row['endDate'] else None,
                "dueDate": str(row['dueDate']) if row['dueDate'] else None,
                "createdAt": str(row['createdAt']),
                "updatedAt": str(row['updatedAt']),
                "notes": [],
                "dependencies": []
            }
            
            # Parse notes if present
            if row['notes']:
                notes = row['notes']
                if isinstance(notes, str):
                    try:
                        notes = json.loads(notes)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse notes JSON for task {task_id}")
                        notes = []
                
                if isinstance(notes, list):
                    task_data["notes"] = notes
            
            # Parse blocked_by dependencies
            if row['blocked_by']:
                blocked_by = row['blocked_by']
                if isinstance(blocked_by, str):
                    try:
                        blocked_by = json.loads(blocked_by)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse blocked_by JSON for task {task_id}")
                        blocked_by = []
                
                if isinstance(blocked_by, list):
                    task_data["dependencies"].extend(blocked_by)
            
            # Parse blocks dependencies
            if row['blocks']:
                blocks = row['blocks']
                if isinstance(blocks, str):
                    try:
                        blocks = json.loads(blocks)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse blocks JSON for task {task_id}")
                        blocks = []
                
                if isinstance(blocks, list):
                    task_data["dependencies"].extend(blocks)

            
            logger.info(f"Successfully retrieved task: {task_id}")
            
            return {
                "status": "success",
                "action": "get_one",
                "message": f"Retrieved task {task_id}",
                "data": task_data
            }
            
        except Exception as e:
            logger.error(f"Error fetching task {task_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "get_one",
                "message": f"Error retrieving task {task_id}",
                "error": str(e)
            }
        finally:
            if conn:
                await conn.close()

    async def _add_notes(self, task_id: str, notes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add notes to an existing task and return structured response"""
        import asyncpg
        from config.settings import settings
        
        if not task_id:
            return {
                "status": "error",
                "action": "add_notes",
                "message": "Task ID is required",
                "error": "Missing task_id parameter"
            }
        
        if not notes:
            return {
                "status": "error",
                "action": "add_notes",
                "message": "At least one note is required",
                "error": "Empty notes list"
            }
        
        conn = None
        try:
            # Connect to database
            db_url = settings.DATABASE_URL
            conn = await asyncpg.connect(db_url)
            
            # Verify task exists and belongs to user
            if self._current_user_id:
                task_check = await conn.fetchval(
                    'SELECT id FROM "Task" WHERE id = $1 AND "userId" = $2',
                    task_id,
                    self._current_user_id
                )
            else:
                task_check = await conn.fetchval('SELECT id FROM "Task" WHERE id = $1', task_id)
                logger.warning("No user_id available for task note verification")
            
            if not task_check:
                logger.warning(f"Task {task_id} not found or access denied for user {self._current_user_id}")
                return {
                    "status": "error",
                    "action": "add_notes",
                    "message": f"Task {task_id} not found or access denied",
                    "error": "Task does not exist or access denied"
                }
            
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
            
            logger.info(f"Added {notes_added} notes to task {task_id}")
            
            return {
                "status": "success",
                "action": "add_notes",
                "message": f"Added {notes_added} note(s) to task {task_id}",
                "data": {
                    "task_id": task_id,
                    "notes_added": notes_added
                }
            }
            
        except Exception as e:
            logger.error(f"Error adding notes to task {task_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "add_notes",
                "message": "Error adding notes",
                "error": str(e)
            }
        finally:
            if conn:
                await conn.close()

    async def _handle_manage_projects(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle manage_projects tool with action routing and return structured response"""
        action = args.get("action")
        
        logger.info(f"[TASK_MANAGER] Manage projects action: {action}, args: {args}")
        
        if action == "create":
            return await self._create_projects(args.get("projects", []))
        elif action == "view":
            return await self._view_project(args.get("project_id", ""))
        elif action == "list":
            return await self._list_projects(args.get("status_filter", ""))
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}",
                "error": f"Unknown action: {action}"
            }

    async def _create_projects(self, projects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create new projects in database and return structured response"""
        if not projects:
            return {
                "status": "error",
                "action": "create",
                "message": "No projects provided to create",
                "error": "Empty projects list"
            }
        
        if not self._current_user_id:
            logger.error("No user_id available for project creation")
            return {
                "status": "error",
                "action": "create",
                "message": "Failed to create projects",
                "error": "User ID is required to create projects"
            }
        
        try:
            logger.info(f"Creating {len(projects)} project(s) for user {self._current_user_id}")
            result = await insert_projects_to_db(projects, user_id=self._current_user_id)
            
            if result.get("success"):
                created_ids = result.get("created_ids", [])
                self.metadata["projects_created"] += len(created_ids)

                logger.info(f"Created {len(created_ids)} project(s)")
                
                return {
                    "status": "success",
                    "action": "create",
                    "message": f"Created {len(created_ids)} project(s) successfully",
                    "data": {
                        "created_count": len(created_ids),
                        "project_ids": [str(id) for id in created_ids]
                    }
                }
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Project creation failed: {error_msg}")
                return {
                    "status": "error",
                    "action": "create",
                    "message": "Failed to create projects",
                    "error": error_msg
                }
        except Exception as e:
            logger.error(f"Exception creating projects: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "create",
                "message": "Error creating projects",
                "error": str(e)
            }

    async def _view_project(self, project_id: str) -> Dict[str, Any]:
        """Get a specific project with task statistics and return structured response"""
        if not project_id:
            return {
                "status": "error",
                "action": "view",
                "message": "Project ID is required",
                "error": "Missing project_id parameter"
            }
        
        try:
            logger.info(f"Fetching project {project_id} for user {self._current_user_id}")
            result = await get_project_by_id(project_id, user_id=self._current_user_id)
            
            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                logger.warning(f"Project not found or error: {error_msg}")
                return {
                    "status": "error",
                    "action": "view",
                    "message": f"Project {project_id} not found",
                    "error": error_msg
                }
            
            project = result.get("project", {})
            self.metadata["projects_viewed"] += 1
            
            # Build project data
            project_data = {
                "id": project['id'],
                "name": project['name'],
                "status": project['status'],
                "description": project.get('description', ''),
                "taskCount": project.get('task_count', 0),
                "completedTasks": project.get('completed_tasks', 0),
                "color": project.get('color'),
                "icon": project.get('icon'),
                "tags": project.get('tags', []),
                "createdAt": str(project.get('createdAt', '')),
                "startDate": str(project.get('startDate', '')) if project.get('startDate') else None,
                "dueDate": str(project.get('dueDate', '')) if project.get('dueDate') else None,
                "endDate": str(project.get('endDate', '')) if project.get('endDate') else None
            }
            
            logger.info(f"Successfully retrieved project: {project_id}")
            
            return {
                "status": "success",
                "action": "view",
                "message": f"Retrieved project {project_id}",
                "data": project_data
            }
            
        except Exception as e:
            logger.error(f"Error fetching project {project_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "view",
                "message": "Error retrieving project",
                "error": str(e)
            }

    async def _list_projects(self, status_filter: str = "") -> Dict[str, Any]:
        """List all projects with optional status filter and return structured response"""
        try:
            logger.info(f"Listing projects with status filter: '{status_filter}'")
            result = await list_projects(
                user_id=self._current_user_id,
                status_filter=status_filter
            )
            
            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Failed to list projects: {error_msg}")
                return {
                    "status": "error",
                    "action": "list",
                    "message": "Error listing projects",
                    "error": error_msg
                }
            
            projects = result.get("projects", [])
            self.metadata["projects_listed"] += 1
            
            if not projects:
                filter_msg = f" with status '{status_filter}'" if status_filter else ""
                return {
                    "status": "success",
                    "action": "list",
                    "message": f"No projects found{filter_msg}",
                    "data": {
                        "total_count": 0,
                        "projects": []
                    }
                }
            
            # Build project list
            project_list = []
            for project in projects:
                task_count = project.get('task_count', 0)
                completed_tasks = project.get('completed_tasks', 0)
                completion_pct = int((completed_tasks / task_count) * 100) if task_count > 0 else 0
                
                project_dict = {
                    "id": project['id'],
                    "name": project['name'],
                    "status": project['status'],
                    "taskCount": task_count,
                    "completedTasks": completed_tasks,
                    "completionPercentage": completion_pct,
                    "icon": project.get('icon', '📁'),
                    "color": project.get('color')
                }
                project_list.append(project_dict)
            
            logger.info(f"Found {len(projects)} projects")
            
            return {
                "status": "success",
                "action": "list",
                "message": f"Found {len(projects)} project(s)",
                "data": {
                    "total_count": len(projects),
                    "returned_count": min(len(projects), 100),
                    "projects": project_list
                }
            }
            
        except Exception as e:
            logger.error(f"Error listing projects: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "list",
                "message": "Error listing projects",
                "error": str(e)
            }
