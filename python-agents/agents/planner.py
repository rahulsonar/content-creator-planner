"""
Planning Agent
Generates content project plans and task breakdowns
"""
from typing import Dict, Any, Optional
from agents.base import BaseAgent
from config.prompts import (
    PLANNING_SYSTEM_PROMPT, 
    PLANNING_TASK_FORMAT_EXAMPLE,
    PLANNING_CONVERSATION_EXAMPLES
)
from utils.logger import logger
from utils.task_inserter import insert_tasks_to_db


class PlanningAgent(BaseAgent):
    """Agent for content planning and task generation"""
    
    def __init__(self, model_client):
        super().__init__(model_client, "planning")
        
        # Define task insertion tool (Anthropic format)
        self.tools_anthropic = [
            {
                "name": "insert_tasks_to_db",
                "description": "Insert generated tasks into the PostgreSQL database. Use this when you've created a set of tasks and are ready to save them to the database. The tasks will be marked as AI-generated and assigned TODO status.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["create_tasks"],
                            "description": "Must be 'create_tasks'"
                        },
                        "tasks": {
                            "type": "array",
                            "description": "Array of task objects to insert",
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
                                        "description": "Your reasoning for including this task"
                                    },
                                    "dependencies": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "List of task titles this depends on"
                                    }
                                },
                                "required": ["title", "description", "priority", "estimatedHours"]
                            }
                        }
                    },
                    "required": ["action", "tasks"]
                }
            }
        ]
        
        # Define task insertion tool (OpenAI format)
        self.tools_openai = [
            {
                "type": "function",
                "function": {
                    "name": "insert_tasks_to_db",
                    "description": "Insert generated tasks into the PostgreSQL database. Use this when you've created a set of tasks and are ready to save them to the database. The tasks will be marked as AI-generated and assigned TODO status.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["create_tasks"],
                                "description": "Must be 'create_tasks'"
                            },
                            "tasks": {
                                "type": "array",
                                "description": "Array of task objects to insert",
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
                                            "description": "Your reasoning for including this task"
                                        },
                                        "dependencies": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "List of task titles this depends on"
                                        }
                                    },
                                    "required": ["title", "description", "priority", "estimatedHours"]
                                }
                            }
                        },
                        "required": ["action", "tasks"]
                    }
                }
            }
        ]
        
        # Initialize with system prompt
        self.add_to_history("system", PLANNING_SYSTEM_PROMPT)
        self.add_to_history("system", f"Task Format Example:\n{PLANNING_TASK_FORMAT_EXAMPLE}")
        self.add_to_history("system", f"Conversation Examples:\n{PLANNING_CONVERSATION_EXAMPLES}")
        self.add_to_history("system", "\n**CRITICAL REMINDER**: You have access to the insert_tasks_to_db tool. When you've created a task plan and the user confirms they like it (e.g., 'yes', 'looks great', 'sounds good', 'perfect'), you MUST immediately call the tool to save tasks. DO NOT just acknowledge - take action and call the tool!")
    
    async def generate_plan(
        self,
        project_description: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a complete project plan with tasks
        
        Args:
            project_description: User's project description
            user_context: User's profile context
            
        Returns:
            Structured plan with tasks
        """
        logger.info(f"Generating plan for: {project_description[:50]}...")
        
        # Build context-aware prompt
        prompt = self._build_planning_prompt(project_description, user_context)
        self.add_to_history("user", prompt)
        
        try:
            # Generate plan
            response = await self.model_client.generate_completion(
                messages=self.conversation_history,
                temperature=0.7,
                max_tokens=2000
            )
            
            self.add_to_history("assistant", response)
            
            # Parse response into structured format
            plan = self._parse_plan_response(response)
            
            logger.info(f"Generated plan with {len(plan.get('tasks', []))} tasks")
            return plan
            
        except Exception as e:
            logger.error(f"Error generating plan: {e}")
            raise
    
    async def process_message(
        self,
        user_message: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process planning-related questions with tool support
        
        Args:
            user_message: User's question or request
            user_context: User's profile context
            
        Returns:
            Agent's response
        """
        self.add_to_history("user", user_message)
        
        try:
            # Check if Anthropic client
            if hasattr(self.model_client, 'client') and hasattr(self.model_client.client, 'messages'):
                response = await self._generate_with_tools_anthropic()
                
                # Handle tool use
                if response.stop_reason == "tool_use":
                    tool_results = await self._execute_tools_anthropic(response.content)
                    
                    # Add to history and get follow-up response
                    self.add_to_history("assistant", response.content)
                    self.add_to_history("user", tool_results)
                    
                    follow_up = await self.model_client.generate_completion(
                        messages=self.conversation_history,
                        temperature=0.7,
                        max_tokens=800
                    )
                    
                    self.add_to_history("assistant", follow_up)
                    return follow_up
                else:
                    # Regular text response
                    text_response = ""
                    for block in response.content:
                        if hasattr(block, 'text'):
                            text_response += block.text
                    
                    self.add_to_history("assistant", text_response)
                    return text_response
            # Check if OpenAI client
            elif hasattr(self.model_client, 'client') and hasattr(self.model_client.client, 'chat'):
                response = await self._generate_with_tools_openai()
                
                message = response.choices[0].message
                
                # Handle tool calls
                if message.tool_calls:
                    tool_results = await self._execute_tools_openai(message.tool_calls)
                    
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
                    
                    # Add tool results
                    for tool_call, result in zip(message.tool_calls, tool_results):
                        self.add_to_history("tool", result, tool_call.id)
                    
                    # Get follow-up response
                    follow_up = await self.model_client.generate_completion(
                        messages=self.conversation_history,
                        temperature=0.7,
                        max_tokens=800
                    )
                    
                    self.add_to_history("assistant", follow_up)
                    return follow_up
                else:
                    # Regular text response
                    self.add_to_history("assistant", message.content)
                    return message.content
            else:
                # Fallback for clients without tool support
                response = await self.model_client.generate_completion(
                    messages=self.conversation_history,
                    temperature=0.7,
                    max_tokens=800
                )
                
                self.add_to_history("assistant", response)
                return response
            
        except Exception as e:
            logger.error(f"Error in planning agent: {e}")
            return "I encountered an error while processing your request. Please try again."
    
    async def stream_response(
        self,
        user_message: str,
        user_context: Optional[Dict[str, Any]] = None
    ):
        """
        Stream planning response in real-time with tool support
        
        Args:
            user_message: User's request
            user_context: User's profile context
            
        Yields:
            Response tokens
        """
        self.add_to_history("user", user_message)
        
        full_response = ""
        try:
            # Check if model_client supports tools (Anthropic does)
            if hasattr(self.model_client, 'client') and hasattr(self.model_client.client, 'messages'):
                # Use tools parameter for Anthropic API
                response = await self._generate_with_tools()
                
                # Handle tool use
                if response.stop_reason == "tool_use":
                    tool_results = await self._execute_tools(response.content)
                    
                    # Yield confirmation message
                    confirmation = f"\n\n✓ Created {len(tool_results)} tasks in database\n"
                    full_response += confirmation
                    yield confirmation
                    
                    # Continue conversation with tool results
                    self.add_to_history("assistant", response.content)
                    self.add_to_history("user", tool_results)
                    
                    # Get follow-up response
                    async for token in self.model_client.stream_completion(
                        messages=self.conversation_history,
                        temperature=0.7,
                        max_tokens=800
                    ):
                        full_response += token
                        yield token
                else:
                    # Regular text response
                    for block in response.content:
                        if hasattr(block, 'text'):
                            full_response += block.text
                            yield block.text
            else:
                # Fallback for non-Anthropic clients
                async for token in self.model_client.stream_completion(
                    messages=self.conversation_history,
                    temperature=0.7,
                    max_tokens=800
                ):
                    full_response += token
                    yield token
            
            self.add_to_history("assistant", full_response)
            
        except Exception as e:
            logger.error(f"Error streaming planning response: {e}")
            yield "I encountered an error. Please try again."
    
    async def _generate_with_tools_anthropic(self):
        """Generate response with tool support for Anthropic"""
        # Extract system message
        system_message = None
        filtered_messages = []
        for msg in self.conversation_history:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                filtered_messages.append(msg)
        
        response = await self.model_client.client.messages.create(
            model=self.model_client.model,
            messages=filtered_messages,
            system=system_message,
            tools=self.tools_anthropic,
            temperature=0.7,
            max_tokens=2000
        )
        
        return response
    
    async def _generate_with_tools_openai(self):
        """Generate response with tool support for OpenAI"""
        response = await self.model_client.generate_completion(
            messages=self.conversation_history,
            temperature=0.7,
            max_tokens=2000,
            tools=self.tools_openai
        )
        
        return response
    
    async def _execute_tools_anthropic(self, content) -> str:
        """Execute tool calls and return results for Anthropic"""
        results = []
        
        for block in content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                
                logger.info(f"Executing tool: {tool_name}")
                
                if tool_name == "insert_tasks_to_db":
                    try:
                        task_ids = await insert_tasks_to_db(tool_input)
                        results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Successfully created {len(task_ids)} tasks with IDs: {', '.join(task_ids)}"
                        })
                    except Exception as e:
                        logger.error(f"Error executing tool: {e}")
                        results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {str(e)}"
                        })
        
        return str(results)
    
    async def _execute_tools_openai(self, tool_calls) -> list:
        """Execute tool calls and return results for OpenAI"""
        import json
        results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_input = json.loads(tool_call.function.arguments)
            
            logger.info(f"Executing tool: {tool_name}")
            
            if tool_name == "insert_tasks_to_db":
                try:
                    task_ids = await insert_tasks_to_db(tool_input)
                    results.append(f"Successfully created {len(task_ids)} tasks with IDs: {', '.join(task_ids)}")
                except Exception as e:
                    logger.error(f"Error executing tool: {e}")
                    results.append(f"Error: {str(e)}")
        
        return results
    
    def _build_planning_prompt(
        self,
        project_description: str,
        user_context: Dict[str, Any]
    ) -> str:
        """
        Build context-aware planning prompt
        
        Args:
            project_description: Project description
            user_context: User context data
            
        Returns:
            Formatted prompt
        """
        context_summary = f"""
User Context:
- Channel: {user_context.get('channelName', 'Unknown')}
- Content Type: {user_context.get('channelType', 'Unknown')}
- Upload Frequency: {user_context.get('uploadFrequency', 'Unknown')}
- Goals: {user_context.get('contentGoals', 'Not specified')}

Project Request:
{project_description}

Please create a detailed project plan with 5-15 actionable tasks. Include task titles, descriptions, priorities, estimated hours, dependencies, research notes, and your reasoning for each task.
"""
        return context_summary
    
    def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured plan format
        
        Args:
            response: Raw LLM response
            
        Returns:
            Structured plan dictionary
        """
        # TODO: Implement robust parsing logic
        # This would parse the response and extract:
        # - Plan overview
        # - Individual tasks with all fields
        # - Dependencies
        
        logger.debug("Parsing plan response")
        
        # Placeholder return structure
        return {
            "overview": response[:200],
            "tasks": [],
            "totalEstimatedHours": 0,
            "rawResponse": response
        }
