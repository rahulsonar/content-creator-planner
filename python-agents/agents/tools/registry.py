"""
Tool Registry - Single source of truth for all available tools.

This module defines all tools that PlanningAgent can reference in task plans
and TaskExecutor can invoke during execution.
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class ToolDefinition:
    """Defines a tool's structure, parameters, and usage patterns."""
    
    name: str
    type: str  # "tool_call" or "agent_call"
    description: str
    parameters: Dict  # JSON schema for parameters
    use_cases: List[str]
    examples: List[Dict] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []


class ToolRegistry:
    """Central registry of all available tools for agents."""
    
    @classmethod
    def get_all_tools(cls) -> List[ToolDefinition]:
        """Returns complete list of all available tools."""
        return [
            # ===== TOOL CALLS (Deterministic Operations) =====

            ToolDefinition(
                name="manage_tasks",
                type="tool_call",
                description="Create, read, update, list, or delete the user's tasks in the database",
                parameters={
                    "action": {
                        "type": "string",
                        "enum": ["create", "update", "get", "list", "delete"],
                        "required": True
                    },
                    "tasks": {
                        "type": "array",
                        "description": "For action=create: list of task objects (title required; description, priority, estimatedHours, projectId, tags, notes optional)",
                        "optional": True
                    },
                    "task_id": {
                        "type": "integer",
                        "description": "For action=update/get/delete: ID of the task",
                        "optional": True
                    },
                    "updates": {
                        "type": "object",
                        "description": "For action=update: fields to update (title, description, status, priority, estimatedHours, actualHours, projectId, dueDate, tags, ...)",
                        "optional": True
                    },
                    "status": {
                        "type": "string",
                        "description": "For action=list: filter by status (TODO, IN_PROGRESS, REVIEW, BLOCKED, COMPLETED, CANCELLED)",
                        "optional": True
                    },
                    "priority": {
                        "type": "string",
                        "description": "For action=list: filter by priority (LOW, MEDIUM, HIGH, URGENT)",
                        "optional": True
                    },
                    "project_id": {
                        "type": "integer",
                        "description": "For action=list: filter by project ID",
                        "optional": True
                    },
                    "limit": {
                        "type": "integer",
                        "description": "For action=list: max tasks to return (default 50, max 200)",
                        "optional": True
                    }
                },
                use_cases=[
                    "Create production pipeline tasks for a content project",
                    "Update a task's status or priority",
                    "List a user's tasks, optionally filtered by project/status",
                    "Look up a specific task by ID",
                    "Delete a task"
                ],
                examples=[{
                    "id": "task_5",
                    "type": "tool_call",
                    "tool_name": "manage_tasks",
                    "description": "Create production pipeline tasks for Episode 1",
                    "goal": "User has actionable tasks to move Ep1 from outline to publish",
                    "depends_on": [],
                    "context": {
                        "action": "create",
                        "tasks": [
                            {
                                "title": "Write Episode 1 script",
                                "description": "Draft full script for Episode 1",
                                "priority": "HIGH",
                                "estimatedHours": 4,
                                "projectId": "${task_1.result.project_id}"
                            }
                        ]
                    }
                }]
            ),

            ToolDefinition(
                name="manage_projects",
                type="tool_call",
                description="Create, read, list, or delete the user's projects in the database",
                parameters={
                    "action": {
                        "type": "string",
                        "enum": ["create", "get", "list", "delete"],
                        "required": True
                    },
                    "projects": {
                        "type": "array",
                        "description": "For action=create: list of project objects (name required; description, status, color, icon, tags optional)",
                        "optional": True
                    },
                    "project_id": {
                        "type": "integer",
                        "description": "For action=get/delete: ID of the project",
                        "optional": True
                    },
                    "status": {
                        "type": "string",
                        "description": "For action=list: filter by status (ACTIVE, ON_HOLD, COMPLETED, ARCHIVED, CANCELLED)",
                        "optional": True
                    },
                    "new_project_id": {
                        "type": "integer",
                        "description": "For action=delete: project ID to transfer the deleted project's tasks to. If omitted, tasks transfer to the user's default project if one exists, otherwise they're orphaned (projectId set to null)",
                        "optional": True
                    }
                },
                use_cases=[
                    "Create a new project for a content series",
                    "Look up a specific project by ID",
                    "List a user's projects",
                    "Delete a project, moving its tasks to another project or the default project"
                ],
                examples=[{
                    "id": "task_1",
                    "type": "tool_call",
                    "tool_name": "manage_projects",
                    "description": "Create the Deccan Atlas project",
                    "goal": "Project exists to attach tasks to",
                    "depends_on": [],
                    "context": {
                        "action": "create",
                        "projects": [
                            {"name": "Deccan Atlas", "description": "History/travel video series"}
                        ]
                    }
                }]
            ),

            ToolDefinition(
                name="manage_context_files",
                type="tool_call",
                description="Read/write user context markdown files for preferences, goals, and notes",
                parameters={
                    "action": {
                        "type": "string",
                        "enum": ["list", "read", "write", "append"],
                        "required": True
                    },
                    "filename": {
                        "type": "string",
                        "description": "Context file name (e.g., 'preferences.md', 'goals.md')",
                        "optional": True
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write/append to file",
                        "optional": True
                    }
                },
                use_cases=[
                    "Store user preferences for future reference",
                    "Retrieve user's stated goals",
                    "Save meeting notes or insights",
                    "Update user context with new information"
                ],
                examples=[{
                    "id": "task_1",
                    "type": "tool_call",
                    "tool_name": "manage_context_files",
                    "description": "Read user's content goals",
                    "goal": "Retrieve goals.md content",
                    "depends_on": [],
                    "context": {
                        "action": "read",
                        "filename": "goals.md"
                    }
                }]
            ),
            
            ToolDefinition(
                name="redis_storage",
                type="tool_call",
                description="Store/retrieve temporary data in Redis with TTL",
                parameters={
                    "operation": {
                        "type": "string",
                        "enum": ["set", "get", "delete", "keys"],
                        "required": True
                    },
                    "key": {
                        "type": "string",
                        "description": "Redis key",
                        "required": True
                    },
                    "value": {
                        "type": "any",
                        "description": "Value to store (for set operation)",
                        "optional": True
                    },
                    "ttl": {
                        "type": "integer",
                        "description": "Time-to-live in seconds (default: 7200)",
                        "optional": True
                    }
                },
                use_cases=[
                    "Cache intermediate computation results",
                    "Store session state temporarily",
                    "Share data between tasks in a plan"
                ],
                examples=[{
                    "id": "task_2",
                    "type": "tool_call",
                    "tool_name": "redis_storage",
                    "description": "Cache project analysis results",
                    "goal": "Analysis results stored for 2 hours",
                    "depends_on": ["task_1"],
                    "context": {
                        "operation": "set",
                        "key": "analysis:project_123",
                        "value": "${task_1.result.analysis}",
                        "ttl": 7200
                    }
                }]
            ),
            
            # ===== AGENT CALLS (Requires LLM Reasoning) =====
            
            ToolDefinition(
                name="executor_agent",
                type="agent_call",
                description="Spawn child agent with LLM reasoning for analysis, decisions, content generation",
                parameters={
                    "task_description": {
                        "type": "string",
                        "description": "Clear description of what the agent should do",
                        "required": True
                    },
                    "context": {
                        "type": "object",
                        "description": "Contextual data needed for the task",
                        "required": True
                    },
                    "expected_output": {
                        "type": "string",
                        "description": "Description of expected output format/content",
                        "required": True
                    }
                },
                use_cases=[
                    "Analyze why a metric dropped",
                    "Generate content outline or draft",
                    "Decide task priority based on dependencies and blockers",
                    "Recommend strategy based on historical data",
                    "Interpret complex user requirements",
                    "Synthesize information from multiple sources"
                ],
                examples=[
                    {
                        "id": "task_3",
                        "type": "agent_call",
                        "description": "Analyze engagement drop on recent posts",
                        "goal": "Identify 3 main reasons for engagement decrease",
                        "depends_on": ["task_1", "task_2"],
                        "context": {
                            "task_description": "Analyze why engagement dropped 40% in the last 2 weeks",
                            "context": {
                                "posts": "${task_1.result.posts}",
                                "metrics": "${task_2.result.analytics}",
                                "time_period": "2026-01-15 to 2026-01-28"
                            },
                            "expected_output": "List of 3-5 main contributing factors with supporting data"
                        }
                    },
                    {
                        "id": "task_5",
                        "type": "agent_call",
                        "description": "Generate content outline for video topic",
                        "goal": "Structured outline with 5-7 main points",
                        "depends_on": ["task_4"],
                        "context": {
                            "task_description": "Create detailed outline for tutorial on AI productivity tips",
                            "context": {
                                "topic": "AI Productivity Tips for Content Creators",
                                "target_audience": "YouTube creators, 25-40 years old",
                                "video_length": "10-12 minutes",
                                "user_preferences": "${task_4.result.preferences}"
                            },
                            "expected_output": "Markdown outline with introduction, 5-7 main points, and conclusion"
                        }
                    }
                ]
            )
        ]
    
    @classmethod
    def format_for_prompt(cls, compact: bool = False) -> str:
        """
        Generate markdown documentation for PlanningAgent system prompt.
        
        Args:
            compact: If True, generates condensed version without examples
        """
        tools = cls.get_all_tools()
        
        if compact:
            # Condensed format - no examples, minimal parameters
            output = "## Tools\n\n"
            for i, tool in enumerate(tools, 1):
                output += f"**{i}. {tool.name}** ({tool.type})\n"
                output += f"{tool.description}\n"
                
                # Compact parameter format
                params = []
                for param, schema in tool.parameters.items():
                    enum_values = schema.get("enum")
                    if enum_values:
                        params.append(f"`{param}`: {', '.join(enum_values)}")
                    else:
                        optional = " (opt)" if schema.get("optional") else ""
                        params.append(f"`{param}`{optional}")
                
                if params:
                    output += f"Params: {' | '.join(params)}\n"
                output += "\n"
            
            return output
        else:
            # Full detailed format with examples
            output = "## Available Tools (Reference Only - Do NOT Execute)\n\n"
            output += "You create task plans that reference these tools. The TaskExecutor will execute them.\n\n"
            
            for i, tool in enumerate(tools, 1):
                output += f"### {i}. {tool.name}\n"
                output += f"- **Type**: `{tool.type}`\n"
                output += f"- **Description**: {tool.description}\n"
                output += f"- **Parameters**:\n"
                
                for param, schema in tool.parameters.items():
                    optional_flag = " (optional)" if schema.get("optional") else ""
                    param_type = schema.get("type", "any")
                    enum_values = schema.get("enum")
                    enum_str = f" - Options: {', '.join(enum_values)}" if enum_values else ""
                    output += f"  - `{param}`: {param_type}{optional_flag}{enum_str}\n"
                
                output += f"- **Use When**: {' | '.join(tool.use_cases)}\n"
                
                if tool.examples:
                    output += f"- **Example**:\n```json\n{json.dumps(tool.examples[0], indent=2)}\n```\n"
                output += "\n"
            
            return output
    
    @classmethod
    def get_tool_schema(cls, tool_name: str) -> Dict:
        """Get JSON schema for ToolExecutor validation."""
        tools = cls.get_all_tools()
        for tool in tools:
            if tool.name == tool_name:
                return tool.parameters
        raise ValueError(f"Tool '{tool_name}' not found in registry")
    
    @classmethod
    def get_tool(cls, tool_name: str) -> Optional[ToolDefinition]:
        """Get full tool definition by name."""
        tools = cls.get_all_tools()
        for tool in tools:
            if tool.name == tool_name:
                return tool
        return None
    
    @classmethod
    def list_tool_names(cls) -> List[str]:
        """Get list of all tool names."""
        return [tool.name for tool in cls.get_all_tools()]
