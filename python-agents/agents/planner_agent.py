"""
Planner Agent Runner
One LLM in a tool-calling loop: call model → run requested tools → feed
results back → repeat until the model answers without tools.

Replaces the Plan → Execute → Synthesize → Replan pipeline. The model
sees every tool result before choosing its next step, so there is no
up-front plan, no ${task.result} templating, and no separate synthesizer.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import json
import re
import asyncio
import traceback

from agents.tools.handlers import manage_tasks, manage_projects
from config.prompts import PLANNER_AGENT_SYSTEM_PROMPT
from models.anthropic_client import AnthropicClient, RAW_CONTENT_KEY
from storage.agent_call_log import agent_call_logger
from utils.logger import logger
from utils.user_context_manager import (
    read_user_context,
    write_user_context,
    update_user_context,
    list_user_context_files,
    get_user_context_path,
)


# Tool results larger than this are truncated before going back to the model
MAX_TOOL_RESULT_CHARS = 20000

# Context filenames must be plain names inside the user's directory
CONTEXT_FILENAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._\- ]*")


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "manage_tasks",
            "description": "Create, read, update, list, or delete the user's tasks in the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["create", "update", "get", "list", "delete"]},
                    "tasks": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "For action=create: task objects (title required; description, priority, estimatedHours, projectId, tags, notes optional)"
                    },
                    "task_id": {"type": "integer", "description": "For action=update/get/delete: ID of the task"},
                    "updates": {
                        "type": "object",
                        "description": "For action=update: fields to update (title, description, status, priority, estimatedHours, actualHours, projectId, dueDate, tags, ...)"
                    },
                    "status": {"type": "string", "description": "For action=list: filter by status (TODO, IN_PROGRESS, REVIEW, BLOCKED, COMPLETED, CANCELLED)"},
                    "priority": {"type": "string", "description": "For action=list: filter by priority (LOW, MEDIUM, HIGH, URGENT)"},
                    "project_id": {"type": "integer", "description": "For action=list: filter by project ID"},
                    "limit": {"type": "integer", "description": "For action=list: max tasks to return (default 50, max 200)"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_projects",
            "description": "Create, read, list, or delete the user's projects in the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["create", "get", "list", "delete"]},
                    "projects": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "For action=create: project objects (name required; description, status, color, icon, tags optional)"
                    },
                    "project_id": {"type": "integer", "description": "For action=get/delete: ID of the project"},
                    "status": {"type": "string", "description": "For action=list: filter by status (ACTIVE, ON_HOLD, COMPLETED, ARCHIVED, CANCELLED)"},
                    "new_project_id": {
                        "type": "integer",
                        "description": "For action=delete: project ID to move the deleted project's tasks to. If omitted, tasks move to the default project, or are orphaned if there is none"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_context_files",
            "description": "List, read, write (overwrite), or append to the user's markdown context files: profile, goals, preferences, saved scripts and notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "read", "write", "append"]},
                    "filename": {"type": "string", "description": "File name, e.g. 'preferences.md'. Required for read/write/append."},
                    "content": {"type": "string", "description": "Content for write/append"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_todos",
            "description": "Replace your working checklist for the current request. Use for requests with 3+ steps; send the full list each time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}
                            },
                            "required": ["content", "status"]
                        }
                    }
                },
                "required": ["todos"]
            }
        }
    }
]


class PlannerAgentRunner:
    """
    Runs one request through a single tool-calling agent.

    Works with both OpenAIClient and AnthropicClient: messages are kept in
    OpenAI format (AnthropicClient converts them) and responses from either
    provider are normalized by _parse_response.
    """

    def __init__(self, model_client, model_name: str, max_steps: int = 15):
        """
        Initialize the runner.

        Args:
            model_client: OpenAIClient or AnthropicClient
            model_name: Model identifier (for logging)
            max_steps: Maximum model turns before forcing a final answer
        """
        self.model_client = model_client
        self.model_name = model_name
        self.max_steps = max_steps
        self._todos: List[Dict[str, str]] = []

    async def run(
        self,
        user_message: str,
        user_id: str,
        conversation_id: int,
        message_id: str,
        conversation_messages: Optional[List[Dict[str, Any]]] = None,
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process one user message to completion.

        Returns:
            Dict with 'message' (final reply) and 'metadata' (steps, tool calls, tokens)
        """
        self._todos = []
        messages = self._build_messages(user_message, user_id, conversation_messages, user_name)

        tool_calls_detailed: List[Dict[str, Any]] = []
        usage_totals = {"prompt_tokens": 0, "completion_tokens": 0}
        final_text: Optional[str] = None
        steps = 0

        log_id: Optional[int] = None
        try:
            log_id = await agent_call_logger.start_agent_call(
                user_id=user_id,
                agent_name="planner_agent",
                model_name=self.model_name,
                message_id=message_id,
                conversation_id=conversation_id,
                agent_type="planner_agent",
                agent_version="1.0.0",
                input_message=user_message,
                tools_enabled=True,
                metadata={"max_steps": self.max_steps, "history_length": len(messages)},
                tags=["planner_agent"]
            )
        except Exception as e:
            logger.error(f"[PlannerAgent] Failed to start agent call logging: {e}")

        try:
            while steps < self.max_steps:
                steps += 1
                response = await self.model_client.generate_completion(messages=messages, tools=TOOLS)
                text, tool_calls, usage = self._parse_response(response)
                for key in usage_totals:
                    usage_totals[key] += usage.get(key, 0)

                if not tool_calls:
                    final_text = text
                    break

                messages.append(self._assistant_message(text, tool_calls, response))
                logger.info(
                    f"[PlannerAgent] Step {steps}: {', '.join(tc['name'] for tc in tool_calls)}"
                )

                # Independent calls in the same turn run concurrently
                results = await asyncio.gather(*[
                    self._run_tool(tc, user_id) for tc in tool_calls
                ])
                for tool_call, (output, record) in zip(tool_calls, results):
                    record["step"] = steps
                    tool_calls_detailed.append(record)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": output
                    })

            hit_step_limit = final_text is None
            if hit_step_limit:
                final_text = await self._force_final_answer(messages, usage_totals)

            metadata = {
                "steps": steps,
                "hit_step_limit": hit_step_limit,
                "tool_calls": len(tool_calls_detailed),
                "failed_tool_calls": sum(1 for r in tool_calls_detailed if not r["success"]),
                **usage_totals
            }

            if log_id:
                try:
                    await agent_call_logger.complete_agent_call(
                        log_id=log_id,
                        output_message=final_text,
                        tool_calls_detailed=tool_calls_detailed,
                        prompt_tokens=usage_totals["prompt_tokens"],
                        completion_tokens=usage_totals["completion_tokens"],
                        total_tokens=usage_totals["prompt_tokens"] + usage_totals["completion_tokens"],
                        metadata=metadata
                    )
                except Exception as e:
                    logger.error(f"[PlannerAgent] Failed to complete agent call log: {e}")

            logger.info(
                f"[PlannerAgent] Done in {steps} step(s), {len(tool_calls_detailed)} tool call(s)"
            )
            return {"message": final_text, "metadata": metadata}

        except Exception as e:
            logger.error(f"[PlannerAgent] Run failed: {e}")
            if log_id:
                try:
                    await agent_call_logger.fail_agent_call(
                        log_id=log_id,
                        error=str(e),
                        stack_trace=traceback.format_exc(),
                        metadata={"steps": steps, "tool_calls": len(tool_calls_detailed)}
                    )
                except Exception as log_error:
                    logger.error(f"[PlannerAgent] Failed to log agent call failure: {log_error}")
            raise

    # ========== Message Handling ==========

    def _build_messages(
        self,
        user_message: str,
        user_id: str,
        conversation_messages: Optional[List[Dict[str, Any]]],
        user_name: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Build system prompt + prior conversation + current user message."""
        system = PLANNER_AGENT_SYSTEM_PROMPT
        system += f"\n\nToday's date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        if user_name:
            system += f"\nYou are talking to {user_name}."
        system += f"\n\n{self._describe_context_files(user_id)}"

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system}]
        for msg in conversation_messages or []:
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})

        # Conversation history from storage may already include the current message
        if messages[-1].get("role") != "user" or messages[-1].get("content") != user_message:
            messages.append({"role": "user", "content": user_message})

        return messages

    @staticmethod
    def _describe_context_files(user_id: str) -> str:
        """List the user's context files with sizes so the model knows what to read."""
        try:
            files = sorted(list_user_context_files(user_id))
        except Exception as e:
            logger.error(f"[PlannerAgent] Failed to list context files: {e}")
            return "Context files: unavailable."

        if not files:
            return "Context files: none yet (this may be a new user)."

        lines = []
        for name in files:
            size = get_user_context_path(user_id, name).stat().st_size
            lines.append(f"- {name} ({size} bytes)")
        return "Context files:\n" + "\n".join(lines)

    @staticmethod
    def _parse_response(response: Any) -> Tuple[str, List[Dict[str, str]], Dict[str, int]]:
        """
        Normalize a model response to (text, tool_calls, usage).

        OpenAIClient returns a ChatCompletion when tools are passed;
        AnthropicClient returns a Message on tool_use and a plain string
        otherwise. tool_calls entries are {id, name, arguments(JSON string)}.
        """
        if isinstance(response, str):
            return response, [], {}

        # OpenAI ChatCompletion
        if hasattr(response, "choices"):
            message = response.choices[0].message
            tool_calls = [
                {"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments or "{}"}
                for tc in (message.tool_calls or [])
            ]
            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens or 0,
                    "completion_tokens": response.usage.completion_tokens or 0
                }
            return message.content or "", tool_calls, usage

        # Anthropic Message
        text = "".join(block.text for block in response.content if block.type == "text")
        tool_calls = [
            {"id": block.id, "name": block.name, "arguments": json.dumps(block.input)}
            for block in response.content if block.type == "tool_use"
        ]
        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens
        }
        return text, tool_calls, usage

    @staticmethod
    def _assistant_message(
        text: str,
        tool_calls: List[Dict[str, str]],
        response: Any = None
    ) -> Dict[str, Any]:
        """
        Assistant turn in OpenAI format (AnthropicClient converts it).

        For Claude responses the original content blocks ride along so
        thinking blocks are passed back unchanged on the next step.
        """
        message = {
            "role": "assistant",
            "content": text or None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]}
                }
                for tc in tool_calls
            ]
        }
        if response is not None and not hasattr(response, "choices") and not isinstance(response, str):
            message[RAW_CONTENT_KEY] = AnthropicClient.raw_content(response)
        return message

    async def _force_final_answer(
        self,
        messages: List[Dict[str, Any]],
        usage_totals: Dict[str, int]
    ) -> str:
        """Step limit reached: ask the model to wrap up without further tool use."""
        logger.warning(f"[PlannerAgent] Hit step limit ({self.max_steps}), forcing final answer")
        messages.append({
            "role": "user",
            "content": (
                "[System] Step limit reached. Do not call any more tools. Reply to the user now: "
                "summarize what you completed and what still remains."
            )
        })
        # Tools stay defined: Anthropic rejects histories containing tool_use without them
        response = await self.model_client.generate_completion(messages=messages, tools=TOOLS)
        text, _, usage = self._parse_response(response)
        for key in usage_totals:
            usage_totals[key] += usage.get(key, 0)
        return text or (
            "I ran out of steps before finishing this request. "
            "Please try again with a narrower request."
        )

    # ========== Tool Execution ==========

    async def _run_tool(self, tool_call: Dict[str, str], user_id: str) -> Tuple[str, Dict[str, Any]]:
        """
        Execute one tool call. Errors are returned to the model as tool
        output (not raised) so it can correct itself.

        Returns:
            (output string for the model, detailed record for logging)
        """
        name = tool_call["name"]
        start = datetime.now(timezone.utc)
        record: Dict[str, Any] = {"tool_call_id": tool_call["id"], "name": name}

        try:
            args = json.loads(tool_call["arguments"] or "{}")
            record["input"] = args

            if name == "manage_tasks":
                result = await manage_tasks(args, user_id)
            elif name == "manage_projects":
                result = await manage_projects(args, user_id)
            elif name == "manage_context_files":
                result = self._manage_context_files(args, user_id)
            elif name == "update_todos":
                result = self._update_todos(args)
            else:
                raise ValueError(f"Unknown tool: {name}")

            output = json.dumps(result, default=str) if not isinstance(result, str) else result
            record["success"] = True
        except Exception as e:
            logger.error(f"[PlannerAgent] Tool {name} failed: {e}")
            output = json.dumps({"error": f"{type(e).__name__}: {e}"})
            record["success"] = False
            record["error"] = str(e)

        if len(output) > MAX_TOOL_RESULT_CHARS:
            output = output[:MAX_TOOL_RESULT_CHARS] + f"\n...[truncated, {len(output)} chars total]"

        record["output"] = output[:2000]
        record["duration_seconds"] = (datetime.now(timezone.utc) - start).total_seconds()
        return output, record

    @staticmethod
    def _manage_context_files(args: Dict[str, Any], user_id: str) -> Any:
        """Direct file operations on agent_context/{user_id}/ (no LLM)."""
        action = args.get("action")

        if action == "list":
            return {"files": sorted(list_user_context_files(user_id))}

        filename = (args.get("filename") or "").strip()
        if not CONTEXT_FILENAME_PATTERN.fullmatch(filename):
            raise ValueError(
                f"Invalid filename '{filename}': use a plain name like 'preferences.md' (no paths)"
            )

        if action == "read":
            content = read_user_context(user_id, filename)
            if content is None:
                raise ValueError(f"File '{filename}' does not exist")
            return content

        content = args.get("content")
        if not content:
            raise ValueError(f"content is required for action={action}")

        if action == "write":
            write_user_context(user_id, filename, content)
            return {"status": "written", "filename": filename, "chars": len(content)}
        elif action == "append":
            update_user_context(user_id, filename, content)
            return {"status": "appended", "filename": filename, "chars": len(content)}
        else:
            raise ValueError(f"Unknown manage_context_files action: {action}")

    def _update_todos(self, args: Dict[str, Any]) -> str:
        """Replace the working checklist and echo it back."""
        todos = args.get("todos")
        if not isinstance(todos, list):
            raise ValueError("todos must be a list")
        self._todos = todos

        marks = {"completed": "[x]", "in_progress": "[~]", "pending": "[ ]"}
        checklist = "\n".join(
            f"{marks.get(t.get('status'), '[ ]')} {t.get('content', '')}" for t in todos
        )
        logger.info(f"[PlannerAgent] Todos:\n{checklist}")
        return checklist
