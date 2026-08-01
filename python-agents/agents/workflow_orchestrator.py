"""
Workflow Orchestrator
Implements the Plan → Execute → Synthesize → Replan iterative pattern
Manages state machine, iteration tracking, and agent coordination
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
import json
import traceback

from agents.planner import PlanningAgent
from agents.synthesizer import SynthesizerAgent
from agents.task_executor import TaskExecutor
from utils.logger import logger
from storage.agent_call_log import agent_call_logger


@dataclass
class WorkflowState:
    """Represents the current state of a workflow execution"""
    
    # Core identifiers
    conversation_id: int
    message_id: str
    user_id: str
    
    # Workflow control
    iteration: int = 1
    max_iterations: int = 5
    current_phase: str = "PLANNING"  # PLANNING, EXECUTING, SYNTHESIZING, REPLANNING, COMPLETED
    goal_achieved: bool = False
    
    # Execution tracking
    planner_response: Optional[Dict[str, Any]] = None
    execution_results: List[Dict[str, Any]] = field(default_factory=list)
    synthesis_report: Optional[Dict[str, Any]] = None
    
    # Context accumulation
    user_query: str = ""
    replan_context: Optional[Dict[str, Any]] = None
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_tasks_executed: int = 0
    total_agent_calls: int = 0
    total_tool_calls: int = 0
    
    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for storage"""
        return asdict(self)


class WorkflowOrchestrator:
    """
    Orchestrates the Plan → Execute → Synthesize → Replan workflow.
    
    This orchestrator implements a unified iterative pattern that handles:
    - Simple Q&A (direct answers in 1 iteration)
    - Straightforward tasks (tool calls in 1 iteration)
    - Complex multi-step reasoning (multiple iterations with replanning)
    
    The workflow continues iterating until:
    1. Goal is achieved (synthesizer determines completion)
    2. Max iterations reached (returns partial result)
    3. Unrecoverable error occurs
    """
    
    def __init__(
        self,
        planner_agent: PlanningAgent,
        model_client,  # For creating SynthesizerAgent instances
        redis_client,
        conversation_storage,
        context_manager_agent=None,
        websocket_manager=None,
        max_iterations: int = 5
    ):
        """
        Initialize workflow orchestrator.
        
        Args:
            planner_agent: PlanningAgent instance
            model_client: LLM client for creating Synthesizer
            redis_client: Redis client for state persistence
            conversation_storage: Conversation history storage
            context_manager_agent: Optional context manager for file operations
            websocket_manager: Optional WebSocket manager for real-time updates
            max_iterations: Maximum iterations before forcing completion (default: 3)
        """
        self.planner_agent = planner_agent
        self.model_client = model_client
        self.redis_client = redis_client
        self.conversation_storage = conversation_storage
        self.context_manager_agent = context_manager_agent
        self.websocket_manager = websocket_manager
        self.max_iterations = max_iterations
        
        # Initialize TaskExecutor
        self.task_executor = TaskExecutor(
            redis_client=redis_client,
            model_client=model_client,
            context_manager_agent=context_manager_agent
        )
        
        # Initialize SynthesizerAgent
        self.synthesizer = SynthesizerAgent(model_client=model_client)
        
        logger.info(f"WorkflowOrchestrator initialized (max_iterations={max_iterations})")
    
    async def execute_workflow(
        self,
        user_query: str,
        conversation_id: int,
        message_id: str,
        user_id: str,
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute the complete Plan → Execute → Synthesize → Replan workflow.
        
        This is the main entry point for processing user queries. It implements
        an iterative loop that continues until the goal is achieved or max iterations
        is reached.
        
        Args:
            user_query: User's question or request
            conversation_id: Conversation identifier (integer)
            message_id: Message identifier
            user_id: User identifier
            user_name: Optional user name for context
            
        Returns:
            Dict containing:
                - message: Final response to user
                - metadata: Execution metadata (iterations, tasks, costs)
                - state: Final workflow state
        """
        # Initialize workflow state
        state = WorkflowState(
            conversation_id=conversation_id,
            message_id=message_id,
            user_id=user_id,
            user_query=user_query,
            max_iterations=self.max_iterations
        )
        
        logger.info(
            f"[Workflow] Starting execution for conversation={conversation_id}, "
            f"message={message_id}, user={user_id}"
        )
        
        try:
            # Store initial state in Redis
            await self._store_workflow_state(state)
            
            # Main iteration loop
            while not state.goal_achieved and state.iteration <= state.max_iterations:
                logger.info(f"[Workflow] === Iteration {state.iteration}/{state.max_iterations} ===")
                await self._notify_websocket(
                    conversation_id, 
                    f"Processing (iteration {state.iteration})..."
                )
                
                # Phase 1: PLANNING
                state.current_phase = "PLANNING"
                await self._planning_phase(state, user_query)
                
                # Check if we got a direct answer (no execution needed)
                if self._is_direct_answer(state.planner_response):
                    logger.info("[Workflow] Direct answer provided - skipping execution")
                    state.goal_achieved = True
                    state.current_phase = "COMPLETED"
                    break
                
                # Phase 2: EXECUTING
                state.current_phase = "EXECUTING"
                await self._execution_phase(state)
                
                # Phase 3: SYNTHESIZING
                state.current_phase = "SYNTHESIZING"
                await self._synthesis_phase(state)
                
                # Decision based on synthesis
                if state.synthesis_report:
                    action = state.synthesis_report.get('action', 'publish')
                    
                    if action == 'publish':
                        state.goal_achieved = True
                        state.current_phase = "COMPLETED"
                        await self._notify_websocket(conversation_id, "Completed!")
                        
                    elif action == 'partial_publish':
                        state.goal_achieved = True
                        state.current_phase = "COMPLETED"
                        await self._notify_websocket(conversation_id, "Completed with notes")
                        
                    elif action == 'replan':
                        # Check if we've hit max iterations
                        if state.iteration >= state.max_iterations:
                            logger.warning(
                                f"[Workflow] Max iterations ({state.max_iterations}) reached - "
                                "forcing completion with partial results"
                            )
                            state.goal_achieved = True
                            state.current_phase = "COMPLETED"
                            await self._notify_websocket(
                                conversation_id, 
                                f"Max iterations reached - providing best available result"
                            )
                            break
                        
                        # Continue to next iteration
                        state.iteration += 1
                        state.current_phase = "REPLANNING"
                        state.replan_context = state.synthesis_report.get('replan_context', {})
                        await self._notify_websocket(
                            conversation_id, 
                            f"Replanning (iteration {state.iteration})..."
                        )
                        
                        # Store updated state
                        await self._store_workflow_state(state)
                    else:
                        logger.error(f"[Workflow] Unknown synthesis action: {action}")
                        state.goal_achieved = True
                        state.current_phase = "COMPLETED"
            
            # Mark completion
            state.completed_at = datetime.now(timezone.utc).isoformat()
            await self._store_workflow_state(state)
            
            # Compile final response
            final_response = await self._compile_final_response(state)
            
            logger.info(
                f"[Workflow] Completed in {state.iteration} iteration(s), "
                f"{state.total_tasks_executed} tasks executed"
            )
            
            return final_response
            
        except Exception as e:
            logger.error(f"[Workflow] Fatal error: {e}")
            logger.error(traceback.format_exc())
            
            # Return error response
            return {
                "message": f"An error occurred while processing your request: {str(e)}",
                "error": True,
                "metadata": {
                    "iteration": state.iteration,
                    "phase": state.current_phase,
                    "error_message": str(e)
                },
                "state": state.to_dict()
            }
    
    async def _planning_phase(self, state: WorkflowState, user_query: str) -> None:
        """
        Execute the Planning phase.
        
        Calls PlanningAgent with:
        - Original user query
        - Replan context (if replanning)
        - Previous execution results (if replanning)
        
        Updates state.planner_response with the plan.
        """
        logger.info(f"[Workflow] Phase 1: PLANNING (iteration {state.iteration})")
        
        try:
            # Build context for planner
            planning_context = {
                "user_id": state.user_id,
                "conversation_id": state.conversation_id,
                "message_id": state.message_id
            }
            
            # Build the message to send to planner
            planner_message = self._build_planner_message({
                "user_query": user_query,
                "iteration": state.iteration,
                "is_replanning": state.iteration > 1,
                "previous_gaps": state.replan_context.get('gaps', []) if state.replan_context else [],
                "previous_results": state.execution_results if state.iteration > 1 else [],
                "replan_reason": state.replan_context.get('reason', '') if state.replan_context else '',
                "suggested_approach": state.replan_context.get('suggested_approach', '') if state.replan_context else ''
            })
            
            logger.info(f"[Workflow] Calling PlanningAgent with message length: {len(planner_message)}")
            
            # Call planner agent (returns text response since tools are disabled)
            planner_response_text = await self.planner_agent.process_message(
                planner_message,
                planning_context
            )
            
            # Parse response - planner should return JSON or direct answer
            try:
                # Try to parse as JSON (task plan)
                planner_response = json.loads(planner_response_text)
                logger.info(f"[Workflow] Planner returned structured JSON: {planner_response.get('response_type')}")
            except json.JSONDecodeError:
                # Direct text answer - wrap it
                logger.info("[Workflow] Planner returned direct text answer")
                planner_response = {
                    "response_type": "direct_answer",
                    "direct_response": planner_response_text
                }
            
            state.planner_response = planner_response
            state.total_agent_calls += 1
            
            logger.info(
                f"[Workflow] Planning complete: "
                f"response_type={planner_response.get('response_type')}"
            )
            
        except Exception as e:
            logger.error(f"[Workflow] Planning phase failed: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def _execution_phase(self, state: WorkflowState) -> None:
        """
        Execute the Execution phase using TaskExecutor.
        
        Processes all tasks from the planner response:
        - Resolves dependencies using topological sort
        - Executes tool_call tasks directly
        - Spawns ExecutorAgent instances for agent_call tasks
        - Stores results in Redis and state
        """
        logger.info(f"[Workflow] Phase 2: EXECUTING (iteration {state.iteration})")
        
        if not state.planner_response:
            logger.warning("[Workflow] No planner response to execute")
            return
        
        tasks = state.planner_response.get('tasks', [])
        if not tasks:
            logger.info("[Workflow] No tasks to execute")
            return
        
        dependency_graph = state.planner_response.get('dependency_graph', {})
        
        try:
            # Use TaskExecutor for dependency-aware execution
            execution_results = await self.task_executor.execute_with_dependencies(
                tasks=tasks,
                dependency_graph=dependency_graph,
                conversation_id=state.conversation_id,
                message_id=state.message_id,
                user_id=state.user_id,
                iteration=state.iteration
            )
            
            # Update state
            state.execution_results.extend(execution_results)
            state.total_tasks_executed += len(execution_results)
            
            # Count tool vs agent calls
            for result in execution_results:
                task_type = result.get('task_type', 'unknown')
                if task_type == 'tool_call':
                    state.total_tool_calls += 1
                elif task_type == 'agent_call':
                    state.total_agent_calls += 1
            
            logger.info(
                f"[Workflow] Execution complete: {len(execution_results)} tasks executed, "
                f"{sum(1 for r in execution_results if r.get('success'))} successful"
            )
            
        except Exception as e:
            logger.error(f"[Workflow] Execution phase failed: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def _synthesis_phase(self, state: WorkflowState) -> None:
        """
        Execute the Synthesis phase using SynthesizerAgent.
        
        Calls SynthesizerAgent to:
        - Evaluate task results against goals
        - Calculate completion score and confidence
        - Determine if goal is achieved
        - Identify gaps if replanning needed
        - Provide replan context for next iteration
        
        Updates state.synthesis_report with the assessment.
        """
        logger.info(f"[Workflow] Phase 3: SYNTHESIZING (iteration {state.iteration})")
        
        try:
            # Call SynthesizerAgent
            synthesis_report = await self.synthesizer.synthesize(
                user_query=state.user_query,
                iteration=state.iteration,
                planner_response=state.planner_response,
                execution_results=state.execution_results,
                conversation_history=state.conversation_history,
                user_id=state.user_id,
                conversation_id=state.conversation_id,
                message_id=state.message_id
            )
            
            state.synthesis_report = synthesis_report
            state.total_agent_calls += 1
            
            logger.info(
                f"[Workflow] Synthesis complete: "
                f"action={synthesis_report.get('action')}, "
                f"completion_score={synthesis_report.get('completion_score')}, "
                f"goal_achieved={synthesis_report.get('goal_achieved')}"
            )
            
        except Exception as e:
            logger.error(f"[Workflow] Synthesis phase failed: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def _compile_final_response(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Compile the final response to return to the user.
        
        Args:
            state: Final workflow state
            
        Returns:
            Final response dict with message, metadata, and state
        """
        # Extract final message
        if self._is_direct_answer(state.planner_response):
            message = state.planner_response.get('direct_response', '')
        elif state.synthesis_report:
            final_response = state.synthesis_report.get('final_response') or {}
            message = final_response.get('message', 'Task completed.')
        else:
            message = "Request processed."
        
        return {
            "message": message,
            "metadata": {
                "iterations": state.iteration,
                "total_tasks_executed": state.total_tasks_executed,
                "total_agent_calls": state.total_agent_calls,
                "total_tool_calls": state.total_tool_calls,
                "goal_achieved": state.goal_achieved,
                "started_at": state.started_at,
                "completed_at": state.completed_at
            },
            "state": state.to_dict()
        }
    
    # Helper methods
    
    def _is_direct_answer(self, planner_response: Optional[Dict[str, Any]]) -> bool:
        """Check if planner provided a direct answer"""
        if not planner_response:
            return False
        return planner_response.get('response_type') == 'direct_answer'
    
    def _build_planner_message(self, context: Dict[str, Any]) -> str:
        """Build the message to send to PlanningAgent"""
        user_query = context.get('user_query', '')
        
        if context.get('is_replanning'):
            # Build replan message with gaps context
            gaps = context.get('previous_gaps', [])
            reason = context.get('replan_reason', '')
            suggested = context.get('suggested_approach', '')
            
            message = f"{user_query}\n\n"
            message += f"[REPLAN CONTEXT]\n"
            message += f"Iteration: {context.get('iteration', 1)}\n"
            message += f"Reason: {reason}\n"
            if suggested:
                message += f"Suggested approach: {suggested}\n"
            if gaps:
                message += f"\nGaps identified:\n"
                for gap in gaps[:3]:  # Show top 3 gaps
                    message += f"- {gap.get('description', 'Unknown gap')}\n"
            
            return message
        
        return user_query
    
    async def _store_workflow_state(self, state: WorkflowState) -> None:
        """Store workflow state in Redis"""
        if not self.redis_client:
            return
        
        key = f"workflow_state:{state.conversation_id}:{state.user_id}"
        value = state.to_dict()
        
        # TTL: 4 hours (14400 seconds)
        await self.redis_client.set(key, value, ttl=14400)
        logger.debug(f"[Workflow] State stored: {key}")
    
    async def _store_task_result(
        self, 
        task_id: str, 
        result: Dict[str, Any], 
        state: WorkflowState
    ) -> None:
        """Store individual task result in Redis"""
        if not self.redis_client:
            return
        
        key = f"task:{state.conversation_id}:{state.message_id}:{task_id}:{state.user_id}"
        
        task_result_object = {
            "task_id": task_id,
            "conversation_id": state.conversation_id,
            "message_id": state.message_id,
            "user_id": state.user_id,
            "plan_iteration": state.iteration,
            "execution": {
                "status": "completed" if result.get('success') else "failed",
                "completed_at": datetime.now(timezone.utc).isoformat()
            },
            "result": result,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # TTL: 2 hours (7200 seconds)
        await self.redis_client.set(key, task_result_object, ttl=7200)
        logger.debug(f"[Workflow] Task result stored: {key}")
    
    async def _notify_websocket(self, conversation_id: int, message: str) -> None:
        """Send notification via WebSocket if available"""
        if not self.websocket_manager:
            return
        
        try:
            # TODO: Implement websocket notification
            logger.debug(f"[Workflow] WebSocket notification: {message}")
        except Exception as e:
            logger.warning(f"[Workflow] WebSocket notification failed: {e}")
