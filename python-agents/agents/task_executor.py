"""
Task Executor
Executes tasks from planning agent with dependency graph support.
Routes tasks to appropriate execution mode (tool_call vs agent_call).
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json
import asyncio
import traceback

from agents.executor import ExecutorAgent
from utils.logger import logger
from storage.agent_call_log import agent_call_logger


class TaskExecutor:
    """
    Executes tasks based on dependency graph.
    
    Supports:
    - Topological sorting for correct execution order
    - Parallel execution of independent tasks
    - Tool calls (direct execution) vs agent calls (LLM reasoning)
    - Result storage in Redis for cross-task dependencies
    """
    
    def __init__(
        self,
        redis_client,
        model_client,
        context_manager_agent=None
    ):
        """
        Initialize task executor.
        
        Args:
            redis_client: Redis client for result storage
            model_client: LLM client for creating ExecutorAgent instances
            context_manager_agent: Optional context manager for file operations
        """
        self.redis_client = redis_client
        self.model_client = model_client
        self.context_manager_agent = context_manager_agent
        
        logger.info("TaskExecutor initialized")
    
    async def execute_with_dependencies(
        self,
        tasks: List[Dict[str, Any]],
        dependency_graph: Dict[str, List[str]],
        conversation_id: int,
        message_id: str,
        user_id: str,
        iteration: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Execute tasks respecting dependency graph.
        
        Args:
            tasks: List of task definitions from planner
            dependency_graph: Adjacency list of dependencies
            conversation_id: Conversation ID for Redis storage (integer)
            message_id: Message ID for Redis storage
            user_id: User ID for Redis storage
            iteration: Current iteration number
            
        Returns:
            List of task execution results
        """
        logger.info(
            f"[TaskExecutor] Executing {len(tasks)} tasks with dependencies "
            f"(iteration={iteration})"
        )
        
        try:
            # Validate dependency graph
            self._validate_dependency_graph(tasks, dependency_graph)
            
            # Get topological execution order
            execution_order = self._topological_sort(dependency_graph)
            logger.info(f"[TaskExecutor] Execution order: {execution_order}")
            
            # Track results
            results = {}
            task_results = []
            
            # Execute tasks in order
            for task_id in execution_order:
                task = self._find_task_by_id(tasks, task_id)
                if not task:
                    logger.error(f"[TaskExecutor] Task {task_id} not found in task list")
                    continue
                
                logger.info(f"[TaskExecutor] Executing task: {task_id} ({task.get('type')})")
                
                try:
                    # Resolve dependencies (get previous task results)
                    task_dependencies = dependency_graph.get(task_id, [])
                    dependency_results = {
                        dep_id: results.get(dep_id) for dep_id in task_dependencies
                    }
                    
                    # Execute task
                    result = await self._execute_single_task(
                        task=task,
                        dependency_results=dependency_results,
                        conversation_id=conversation_id,
                        message_id=message_id,
                        user_id=user_id,
                        iteration=iteration
                    )
                    
                    # Store result
                    results[task_id] = result
                    task_results.append(result)
                    
                    # Store in Redis for cross-task access
                    await self._store_task_result_in_redis(
                        task_id=task_id,
                        result=result,
                        conversation_id=conversation_id,
                        message_id=message_id,
                        user_id=user_id,
                        iteration=iteration
                    )
                    
                    # Check if task failed critically
                    if not result.get('success') and task.get('critical', False):
                        logger.warning(
                            f"[TaskExecutor] Critical task {task_id} failed - "
                            "stopping execution"
                        )
                        break
                    
                except Exception as e:
                    logger.error(f"[TaskExecutor] Task {task_id} execution failed: {e}")
                    logger.error(traceback.format_exc())
                    
                    # Record failure
                    failure_result = {
                        "task_id": task_id,
                        "success": False,
                        "error": str(e),
                        "task_type": task.get('type'),
                        "tool_name": task.get('tool_name'),
                        "description": task.get('description')
                    }
                    results[task_id] = failure_result
                    task_results.append(failure_result)
            
            logger.info(
                f"[TaskExecutor] Execution complete: {len(task_results)} tasks, "
                f"{sum(1 for r in task_results if r.get('success'))} successful"
            )
            
            return task_results
            
        except Exception as e:
            logger.error(f"[TaskExecutor] Fatal execution error: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def _execute_single_task(
        self,
        task: Dict[str, Any],
        dependency_results: Dict[str, Dict[str, Any]],
        conversation_id: int,
        message_id: str,
        user_id: str,
        iteration: int
    ) -> Dict[str, Any]:
        """
        Execute a single task based on its type.
        
        Args:
            task: Task definition
            dependency_results: Results from dependencies
            conversation_id: Conversation ID (integer)
            message_id: Message ID
            user_id: User ID
            iteration: Current iteration
            
        Returns:
            Task execution result
        """
        task_type = task.get('type')
        task_id = task.get('id')
        tool_name = task.get('tool_name', 'unknown')
        description = task.get('description', '')
        
        start_time = datetime.now(timezone.utc)
        log_id: Optional[int] = None
        
        # START AGENT CALL LOGGING
        log_completed = False  # Track if we've completed the log
        try:
            agent_name = f"task_executor_{task_type}"
            log_id = await agent_call_logger.start_agent_call(
                user_id=user_id,
                agent_name=agent_name,
                model_name="direct_execution" if task_type == 'tool_call' else "gpt-4o-mini",
                message_id=f"{message_id}_{task_id}",
                conversation_id=conversation_id,
                session_id=None,
                agent_type="task_executor",
                agent_version="1.0.0",
                input_message=description or f"Execute {tool_name}",
                tools_enabled=task_type == 'tool_call',
                metadata={
                    "task_id": task_id,
                    "task_type": task_type,
                    "tool_name": tool_name,
                    "iteration": iteration,
                    "has_dependencies": len(dependency_results) > 0,
                    "dependencies_count": len(dependency_results)
                },
                tags=["task_executor", task_type, f"iteration_{iteration}"]
            )
            logger.info(f"[TaskExecutor] Started agent call log: {log_id} for task {task_id}")
        except Exception as e:
            logger.error(f"[TaskExecutor] Failed to start agent call logging for task {task_id}: {e}")
        
        try:
            if task_type == 'tool_call':
                # Direct tool execution (no LLM)
                result = await self._execute_tool_call(
                    task,
                    dependency_results,
                    user_id,
                    conversation_id,
                    message_id
                )
            elif task_type == 'agent_call':
                # Spawn child agent with LLM reasoning
                result = await self._execute_agent_call(
                    task, 
                    dependency_results, 
                    conversation_id,
                    message_id,
                    user_id
                )
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            task_result = {
                "task_id": task_id,
                "success": True,
                "task_type": task_type,
                "tool_name": tool_name,
                "description": description,
                "goal": task.get('goal'),
                "output": result,
                "started_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
                "duration_seconds": duration,
                "iteration": iteration
            }
            
            # COMPLETE AGENT CALL LOGGING
            if log_id:
                try:
                    await agent_call_logger.complete_agent_call(
                        log_id=log_id,
                        output_message=str(result)[:1000] if result else "Success",
                        metadata={
                            "success": True,
                            "duration_seconds": duration,
                            "output_size": len(str(result)) if result else 0
                        }
                    )
                    log_completed = True
                except Exception as log_error:
                    logger.error(f"[TaskExecutor] Failed to complete agent call log: {log_error}")
            
            return task_result
            
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            logger.error(f"[TaskExecutor] Task {task_id} failed: {e}")
            
            task_result = {
                "task_id": task_id,
                "success": False,
                "task_type": task_type,
                "tool_name": tool_name,
                "description": description,
                "goal": task.get('goal'),
                "error": str(e),
                "error_trace": traceback.format_exc(),
                "started_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
                "duration_seconds": duration,
                "iteration": iteration
            }
            
            # FAIL AGENT CALL LOGGING
            if log_id:
                try:
                    await agent_call_logger.fail_agent_call(
                        log_id=log_id,
                        error=str(e),
                        stack_trace=traceback.format_exc(),
                        metadata={
                            "duration_seconds": duration
                        }
                    )
                    log_completed = True
                except Exception as log_error:
                    logger.error(f"[TaskExecutor] Failed to log agent call failure: {log_error}")
            
            return task_result
        
        finally:
            # SAFETY NET: Ensure log is never left in IN_PROGRESS state
            if log_id and not log_completed:
                try:
                    logger.warning(
                        f"[TaskExecutor] Log {log_id} was not completed/failed properly - "
                        f"marking as FAILED (safety net)"
                    )
                    await agent_call_logger.fail_agent_call(
                        log_id=log_id,
                        error="Task execution did not complete normally (exception or interruption)",
                        error_type="incomplete_execution",
                        metadata={
                            "task_id": task_id,
                            "task_type": task_type,
                            "safety_net_triggered": True
                        }
                    )
                except Exception as final_error:
                    logger.error(
                        f"[TaskExecutor] Failed to mark orphaned log {log_id} as failed: {final_error}"
                    )
    
    async def _execute_tool_call(
        self,
        task: Dict[str, Any],
        dependency_results: Dict[str, Dict[str, Any]],
        user_id: str,
        conversation_id: Optional[int] = None,
        message_id: Optional[str] = None
    ) -> Any:
        """
        Execute a tool call directly (no LLM).

        Args:
            task: Task definition with tool_name and context
            dependency_results: Results from dependencies
            user_id: User ID
            conversation_id: Conversation ID (integer), for tools that log agent calls
            message_id: Message ID, for tools that log agent calls

        Returns:
            Tool execution result
        """
        tool_name = task.get('tool_name')
        context = task.get('context', {})

        logger.info(f"[TaskExecutor] Executing tool: {tool_name}")

        # Resolve variable references in context (e.g., ${task_1.result.project_id})
        resolved_context = self._resolve_variable_references(context, dependency_results)

        # Route to appropriate tool
        if tool_name == 'manage_tasks':
            return await self._execute_manage_tasks(resolved_context, user_id)
        elif tool_name == 'manage_projects':
            return await self._execute_manage_projects(resolved_context, user_id)
        elif tool_name == 'manage_context_files':
            return await self._execute_manage_context_files(
                resolved_context, user_id, conversation_id, message_id
            )
        elif tool_name == 'redis_storage':
            return await self._execute_redis_storage(resolved_context)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def _execute_agent_call(
        self,
        task: Dict[str, Any],
        dependency_results: Dict[str, Dict[str, Any]],
        conversation_id: int,
        message_id: str,
        user_id: str
    ) -> Any:
        """
        Execute an agent call (spawn child agent with LLM).
        
        Args:
            task: Task definition with description and context
            dependency_results: Results from dependencies
            conversation_id: Conversation ID (integer)
            message_id: Message ID
            user_id: User ID
            
        Returns:
            Agent execution result
        """
        logger.info(f"[TaskExecutor] Spawning child agent for task: {task.get('id')}")
        
        # ExecutorAgent is designed for subtask delegation, not direct agent calls
        # For direct LLM calls, use the model client directly
        
        # Build prompt from task description and context
        context = task.get('context', {})
        resolved_context = self._resolve_variable_references(context, dependency_results)
        
        prompt = f"""
Execute the following task:

Task: {task.get('description')}

Goal: {task.get('goal')}

Context:
{json.dumps(resolved_context, indent=2, default=str)}

Expected Output: {task.get('expected_output', 'Detailed analysis or result')}

Provide a detailed response addressing the task requirements.
"""
        
        # Use model client directly for agent_call tasks
        try:
            response = await self.model_client.generate_completion(
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant executing a specific task. Provide detailed and accurate responses."},
                    {"role": "user", "content": prompt}
                ],
                #temperature=0.7
            )
            
            return response
        except Exception as e:
            logger.error(f"[TaskExecutor] Agent call failed: {e}")
            raise
    
    # ========== Tool Execution Methods ==========
    
    @staticmethod
    def _coerce_id(value: Any) -> Any:
        """
        Cast an ID to int when possible.

        Variable references like ${task_1.result.project_id} are always
        resolved to strings (see _resolve_variable_references), but ID
        columns in the database are integers, so numeric-looking strings
        need to be converted back before hitting asyncpg.
        """
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return value

    async def _execute_manage_tasks(self, context: Dict, user_id: str) -> Any:
        """Execute manage_tasks tool."""
        from utils.task_inserter import insert_tasks_to_db
        from utils.task_updater import update_task_by_id
        from utils.task_query import get_task_by_id, list_tasks, delete_task_by_id

        action = context.get('action')
        logger.info(f"[TaskExecutor] manage_tasks action: {action}")

        if action == 'create':
            tasks = context.get('tasks', [])
            if not tasks:
                raise ValueError("tasks must be a non-empty list")
            for task in tasks:
                if 'projectId' in task:
                    task['projectId'] = self._coerce_id(task['projectId'])
            return await insert_tasks_to_db(tasks, user_id=user_id)

        elif action == 'update':
            task_id = self._coerce_id(context.get('task_id'))
            updates = context.get('updates', {})
            if not task_id:
                raise ValueError("task_id is required")
            if not updates:
                raise ValueError("updates must be a non-empty object")
            if 'projectId' in updates:
                updates['projectId'] = self._coerce_id(updates['projectId'])
            updated = await update_task_by_id(task_id, updates, user_id=user_id)
            return {"success": updated, "task_id": task_id, "updated": updated}

        elif action == 'get':
            task_id = self._coerce_id(context.get('task_id'))
            if not task_id:
                raise ValueError("task_id is required")
            return await get_task_by_id(task_id=task_id, user_id=user_id)

        elif action == 'list':
            return await list_tasks(
                user_id=user_id,
                status=context.get('status'),
                priority=context.get('priority'),
                project_id=self._coerce_id(context.get('project_id')),
                limit=context.get('limit', 50),
            )

        elif action == 'delete':
            task_id = self._coerce_id(context.get('task_id'))
            if not task_id:
                raise ValueError("task_id is required")
            return await delete_task_by_id(task_id=task_id, user_id=user_id)

        else:
            raise ValueError(f"Unknown manage_tasks action: {action}")

    async def _execute_manage_projects(self, context: Dict, user_id: str) -> Any:
        """Execute manage_projects tool."""
        from utils.project_manager import (
            insert_projects_to_db,
            get_project_by_id,
            list_projects,
            delete_project_by_id,
        )

        action = context.get('action')
        logger.info(f"[TaskExecutor] manage_projects action: {action}")

        if action == 'create':
            projects = context.get('projects', [])
            if not projects:
                raise ValueError("projects must be a non-empty list")
            return await insert_projects_to_db(projects, user_id=user_id)

        elif action == 'get':
            project_id = self._coerce_id(context.get('project_id'))
            if not project_id:
                raise ValueError("project_id is required")
            return await get_project_by_id(project_id=project_id, user_id=user_id)

        elif action == 'list':
            return await list_projects(user_id=user_id, status_filter=context.get('status', ''))

        elif action == 'delete':
            project_id = self._coerce_id(context.get('project_id'))
            if not project_id:
                raise ValueError("project_id is required")
            new_project_id = self._coerce_id(context.get('new_project_id'))
            return await delete_project_by_id(
                project_id=project_id,
                user_id=user_id,
                new_project_id=new_project_id,
            )

        else:
            raise ValueError(f"Unknown manage_projects action: {action}")
    
    async def _execute_manage_context_files(
        self,
        context: Dict,
        user_id: str,
        conversation_id: Optional[int] = None,
        message_id: Optional[str] = None
    ) -> Any:
        """Execute manage_context_files tool."""
        if not self.context_manager_agent:
            raise ValueError("ContextManager agent not configured")

        action = context.get('action')
        filename = context.get('filename')
        content = context.get('content')

        if action == 'read':
            request = f"Read context file: {filename}"
        elif action == 'write':
            request = f"Write to {filename}: {content}"
        elif action == 'append':
            request = f"Append to {filename}: {content}"
        elif action == 'list':
            request = "List all context files"
        else:
            request = f"Manage context: {action} - {json.dumps(context)}"

        result = await self.context_manager_agent.process_message(
            user_message=request,
            user_context={
                'user_id': user_id,
                'conversation_id': conversation_id,
                'message_id': message_id
            }
        )

        return result
    
    async def _execute_redis_storage(self, context: Dict) -> Any:
        """Execute redis_storage tool."""
        operation = context.get('operation')
        key = context.get('key')
        value = context.get('value')
        ttl = context.get('ttl', 7200)  # Default 2 hours
        
        if operation == 'set':
            await self.redis_client.set(key, json.dumps(value), ttl)
            return {"status": "stored", "key": key, "ttl": ttl}
        elif operation == 'get':
            data = await self.redis_client.get(key)
            return json.loads(data) if data else None
        elif operation == 'delete':
            await self.redis_client.delete(key)
            return {"status": "deleted", "key": key}
        elif operation == 'keys':
            pattern = value or '*'
            keys = await self.redis_client.keys(pattern)
            return {"keys": keys}
        else:
            raise ValueError(f"Unknown Redis operation: {operation}")
    
    # ========== Helper Methods ==========
    
    def _validate_dependency_graph(
        self,
        tasks: List[Dict[str, Any]],
        dependency_graph: Dict[str, List[str]]
    ) -> None:
        """Validate dependency graph for cycles and missing references."""
        task_ids = {task['id'] for task in tasks}
        
        # Check all task IDs exist
        for task_id, deps in dependency_graph.items():
            if task_id not in task_ids:
                raise ValueError(f"Dependency graph references unknown task: {task_id}")
            for dep in deps:
                if dep not in task_ids:
                    raise ValueError(
                        f"Task {task_id} depends on unknown task: {dep}"
                    )
        
        # Check for cycles (simplified check)
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in dependency_graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for task_id in task_ids:
            if task_id not in visited:
                if has_cycle(task_id):
                    raise ValueError("Dependency graph contains cycles")
    
    def _topological_sort(self, dependency_graph: Dict[str, List[str]]) -> List[str]:
        """
        Topological sort for task execution order.
        
        Returns tasks in order where dependencies come before dependents.
        """
        in_degree = {task: 0 for task in dependency_graph}
        
        # Calculate in-degrees
        for task, deps in dependency_graph.items():
            for dep in deps:
                in_degree[task] = in_degree.get(task, 0) + 1
        
        # Queue with zero in-degree
        queue = [task for task, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            task = queue.pop(0)
            result.append(task)
            
            # Reduce in-degree for dependent tasks
            for other_task, deps in dependency_graph.items():
                if task in deps:
                    in_degree[other_task] -= 1
                    if in_degree[other_task] == 0:
                        queue.append(other_task)
        
        if len(result) != len(dependency_graph):
            raise ValueError("Cannot resolve dependencies - possible cycle detected")
        
        return result
    
    def _find_task_by_id(
        self, 
        tasks: List[Dict[str, Any]], 
        task_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find task by ID in task list."""
        for task in tasks:
            if task.get('id') == task_id:
                return task
        return None
    
    def _resolve_variable_references(
        self,
        context: Dict[str, Any],
        dependency_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Resolve variable references like ${task_1.result.project_id}.
        
        Args:
            context: Task context with possible variable references
            dependency_results: Results from dependent tasks
            
        Returns:
            Context with variables resolved
        """
        import re
        
        def resolve_value(value):
            if isinstance(value, str) and '${' in value:
                # Pattern: ${task_id.path.to.value}
                pattern = r'\$\{([^}]+)\}'
                matches = re.findall(pattern, value)
                
                for match in matches:
                    parts = match.split('.')
                    if len(parts) < 2:
                        continue
                    
                    task_id = parts[0]
                    path = parts[1:]
                    
                    # Navigate to value
                    if task_id in dependency_results:
                        result = dependency_results[task_id]
                        for part in path:
                            if isinstance(result, dict) and part in result:
                                result = result[part]
                            else:
                                logger.warning(
                                    f"Could not resolve variable: {match}"
                                )
                                break
                        
                        # Replace in string
                        value = value.replace(f'${{{match}}}', str(result))
                
                return value
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            else:
                return value
        
        return resolve_value(context)
    
    async def _store_task_result_in_redis(
        self,
        task_id: str,
        result: Dict[str, Any],
        conversation_id: int,
        message_id: str,
        user_id: str,
        iteration: int
    ) -> None:
        """Store task result in Redis for cross-task access."""
        key = f"task:{conversation_id}:{message_id}:{task_id}:{user_id}"
        
        result_data = {
            **result,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "iteration": iteration,
            "stored_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Store with 2-hour TTL
        await self.redis_client.set(key, result_data, 7200)
        
        logger.debug(f"[TaskExecutor] Stored task result in Redis: {key}")
