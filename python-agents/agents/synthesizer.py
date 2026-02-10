"""
Synthesizer Agent
Evaluates task execution results against user goals
Determines completion status and provides gap analysis for replanning
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import json
import traceback

from agents.base import BaseAgent
from config.prompts import SYNTHESIZER_SYSTEM_PROMPT
from utils.logger import logger
from storage.agent_call_log import agent_call_logger


class SynthesizerAgent(BaseAgent):
    """
    Agent for evaluating task results and determining goal completion.
    
    The synthesizer analyzes execution results and decides:
    1. Whether the user's goal has been achieved
    2. What gaps exist (if any)
    3. What action to take next (publish, partial_publish, or replan)
    4. What context to provide for replanning
    """
    
    def __init__(self, model_client):
        """
        Initialize synthesizer agent.
        
        Args:
            model_client: LLM client (OpenAI, Claude, etc.)
        """
        super().__init__(model_client, "synthesizer")
        
        self.metadata = {
            "agent_name": "synthesizer",
            "agent_type": "synthesizer",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "synthesis_count": 0,
            "goals_achieved_count": 0,
            "replans_triggered_count": 0,
            "model_name": getattr(model_client, 'model', 'unknown'),
            "agent_version": "1.0.0"
        }
        
        logger.info(f"SynthesizerAgent initialized with model: {self.metadata['model_name']}")
    
    async def process_message(
        self, 
        user_message: str, 
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process message - delegates to synthesize() method.
        
        This is required by BaseAgent but not the primary interface for SynthesizerAgent.
        Use synthesize() directly for workflow orchestration.
        
        Args:
            user_message: User's input message
            user_context: Optional user context data
            
        Returns:
            JSON string of synthesis report
        """
        # Extract synthesis parameters from context
        planner_response = user_context.get('planner_response', {}) if user_context else {}
        execution_results = user_context.get('execution_results', []) if user_context else []
        iteration = user_context.get('iteration', 1) if user_context else 1
        
        # Call synthesize
        synthesis_report = await self.synthesize(
            user_query=user_message,
            iteration=iteration,
            planner_response=planner_response,
            execution_results=execution_results,
            user_id=user_context.get('user_id') if user_context else None,
            conversation_id=user_context.get('conversation_id') if user_context else None,
            message_id=user_context.get('message_id') if user_context else None
        )
        
        return json.dumps(synthesis_report)
    
    async def synthesize(
        self,
        user_query: str,
        iteration: int,
        planner_response: Dict[str, Any],
        execution_results: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        conversation_id: Optional[int] = None,
        message_id: Optional[str] = None,
        parent_call_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesize execution results and determine next action.
        
        Args:
            user_query: Original user question/request
            iteration: Current iteration number
            planner_response: The plan that was executed
            execution_results: Results from task execution
            conversation_history: Optional conversation context
            user_id: User identifier for logging
            conversation_id: Conversation ID for logging (integer)
            message_id: Message ID for logging
            parent_call_id: Parent agent call ID (from planner)
            
        Returns:
            Synthesis report with:
                - completion_score: float (0-1) indicating how much of goal was met
                - confidence: float (0-1) indicating confidence in assessment
                - goal_achieved: bool
                - action: "publish" | "partial_publish" | "replan"
                - gaps: List of identified gaps (if replanning needed)
                - final_response: Final message to user (if publishing)
                - replan_context: Context for next planning iteration (if replanning)
                - summary: Execution summary
                - metadata: Additional metadata
        """
        self.metadata["synthesis_count"] += 1
        
        # Start agent call logging if user_id provided
        log_id: Optional[int] = None
        if user_id and message_id:
            try:
                log_id = await agent_call_logger.start_agent_call(
                    user_id=user_id,
                    agent_name="synthesizer",
                    model_name=self.metadata.get("model_name", "unknown"),
                    message_id=message_id,
                    conversation_id=conversation_id,
                    agent_type="synthesizing",
                    agent_version=self.metadata.get("agent_version", "1.0.0"),
                    input_message=user_query,
                    tools_enabled=False,
                    iteration_number=iteration,
                    workflow_phase="synthesizing",
                    parent_call_id=parent_call_id,
                    metadata={
                        "tasks_analyzed": len(execution_results),
                        "iteration": iteration
                    },
                    tags=["synthesis", f"iteration_{iteration}"]
                )
            except Exception as e:
                logger.warning(f"[Synthesizer] Failed to start agent call logging: {e}")
        
        logger.info(
            f"[Synthesizer] Analyzing results for iteration {iteration}: "
            f"{len(execution_results)} tasks executed"
        )
        
        try:
            # Handle direct answer case
            if planner_response.get('response_type') == 'direct_answer':
                return await self._synthesize_direct_answer(
                    user_query,
                    planner_response.get('direct_response', ''),
                    iteration
                )
            
            # Analyze task execution results
            analysis = self._analyze_execution_results(execution_results)
            
            # Build synthesis prompt
            synthesis_prompt = self._build_synthesis_prompt(
                user_query=user_query,
                iteration=iteration,
                planner_response=planner_response,
                execution_results=execution_results,
                analysis=analysis,
                conversation_history=conversation_history
            )
            
            # Call LLM for synthesis
            synthesis_response = await self._call_llm_for_synthesis(synthesis_prompt)
            
            # Parse and validate synthesis response
            synthesis_report = self._parse_synthesis_response(synthesis_response, analysis)
            
            # Update metadata
            if synthesis_report.get('goal_achieved'):
                self.metadata["goals_achieved_count"] += 1
            if synthesis_report.get('action') == 'replan':
                self.metadata["replans_triggered_count"] += 1
            
            # Complete agent call logging
            if log_id:
                try:
                    await agent_call_logger.complete_agent_call(
                        log_id=log_id,
                        output_message=json.dumps(synthesis_report.get('final_response', {})),
                        completion_score=synthesis_report.get('completion_score'),
                        synthesis_action=synthesis_report.get('action'),
                        gaps_identified=len(synthesis_report.get('gaps', [])),
                        metadata={
                            "goal_achieved": synthesis_report.get('goal_achieved'),
                            "confidence": synthesis_report.get('confidence'),
                            "iteration": iteration
                        }
                    )
                except Exception as e:
                    logger.warning(f"[Synthesizer] Failed to complete agent call logging: {e}")
            
            logger.info(
                f"[Synthesizer] Synthesis complete: "
                f"action={synthesis_report['action']}, "
                f"completion_score={synthesis_report['completion_score']}, "
                f"confidence={synthesis_report['confidence']}"
            )
            
            return synthesis_report
            
        except Exception as e:
            logger.error(f"[Synthesizer] Synthesis failed: {e}")
            logger.error(traceback.format_exc())
            
            # Log failure if logging was started
            if log_id:
                try:
                    await agent_call_logger.fail_agent_call(
                        log_id=log_id,
                        error=str(e),
                        error_type="synthesis_error",
                        stack_trace=traceback.format_exc()
                    )
                except Exception as log_error:
                    logger.warning(f"[Synthesizer] Failed to log error: {log_error}")
            
            # Return safe fallback
            return self._create_fallback_synthesis(user_query, execution_results, str(e))
    
    async def _synthesize_direct_answer(
        self,
        user_query: str,
        direct_response: str,
        iteration: int
    ) -> Dict[str, Any]:
        """
        Synthesize results for a direct answer from planner.
        
        Direct answers are usually complete in one iteration.
        
        Args:
            user_query: User's question
            direct_response: Planner's direct answer
            iteration: Current iteration
            
        Returns:
            Synthesis report indicating completion
        """
        logger.info("[Synthesizer] Processing direct answer")
        
        # For direct answers, we trust the planner and publish
        return {
            "completion_score": 1.0,
            "confidence": 0.95,
            "goal_achieved": True,
            "action": "publish",
            "gaps": [],
            "final_response": {
                "message": direct_response,
                "format": "markdown"
            },
            "summary": {
                "user_query": user_query,
                "execution_summary": "Planner provided direct answer without task execution",
                "outcome": "Question answered directly"
            },
            "metadata": {
                "iteration_number": iteration,
                "response_type": "direct_answer",
                "tasks_executed": 0
            }
        }
    
    def _analyze_execution_results(
        self, 
        execution_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze execution results to extract key metrics.
        
        Args:
            execution_results: List of task execution results
            
        Returns:
            Analysis summary with success rates, failures, etc.
        """
        total_tasks = len(execution_results)
        successful_tasks = sum(1 for r in execution_results if r.get('success', False))
        failed_tasks = total_tasks - successful_tasks
        
        # Calculate success rate
        success_rate = successful_tasks / total_tasks if total_tasks > 0 else 0.0
        
        # Group by task type
        tool_calls = [r for r in execution_results if r.get('task_type') == 'tool_call']
        agent_calls = [r for r in execution_results if r.get('task_type') == 'agent_call']
        
        # Extract failures
        failures = [
            {
                "task_id": r.get('task_id'),
                "error": r.get('error'),
                "task_type": r.get('task_type')
            }
            for r in execution_results
            if not r.get('success', False)
        ]
        
        return {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": success_rate,
            "tool_calls_count": len(tool_calls),
            "agent_calls_count": len(agent_calls),
            "failures": failures,
            "has_failures": failed_tasks > 0
        }
    
    def _build_synthesis_prompt(
        self,
        user_query: str,
        iteration: int,
        planner_response: Dict[str, Any],
        execution_results: List[Dict[str, Any]],
        analysis: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Build the synthesis prompt for the LLM.
        
        Args:
            user_query: Original user query
            iteration: Current iteration number
            planner_response: The plan that was executed
            execution_results: Task execution results
            analysis: Pre-computed analysis of results
            conversation_history: Optional conversation context
            
        Returns:
            Formatted synthesis prompt
        """
        prompt = f"""# Synthesis Task

You are evaluating whether a task execution plan successfully fulfilled the user's request.

## User's Original Request
{user_query}

## Iteration Information
- Current iteration: {iteration}
- Is this a replan: {iteration > 1}

## Execution Plan
{json.dumps(planner_response, indent=2)}

## Execution Results Summary
- Total tasks: {analysis['total_tasks']}
- Successful: {analysis['successful_tasks']}
- Failed: {analysis['failed_tasks']}
- Success rate: {analysis['success_rate']:.1%}

## Detailed Task Results
{json.dumps(execution_results, indent=2)}

## Your Task

Analyze the execution results and determine:

1. **Completion Score** (0.0 to 1.0): How much of the user's goal was achieved?
   - 1.0 = Fully completed
   - 0.7-0.9 = Mostly complete with minor gaps
   - 0.5-0.7 = Partially complete with significant gaps
   - <0.5 = Major failures or goal misunderstood

2. **Confidence** (0.0 to 1.0): How confident are you in this assessment?
   - Consider query clarity, result consistency, task success rate

3. **Goal Achieved** (boolean): Can we return this to the user as complete?
   - True if completion_score >= 0.85 AND confidence >= 0.7
   - False otherwise

4. **Action** (one of):
   - "publish": Goal fully achieved, return final result
   - "partial_publish": Acceptable result with caveats, mention gaps
   - "replan": Need another iteration to address gaps

5. **Gaps** (if action is "replan" or "partial_publish"):
   - List specific issues, missing steps, or failures
   - Categorize by severity: "critical", "major", "minor"
   - Provide recommendations for addressing each gap

6. **Final Response** (if action is "publish" or "partial_publish"):
   - Compile a user-facing response based on execution results
   - Use markdown formatting
   - Be concise but complete

7. **Replan Context** (if action is "replan"):
   - Explain why replanning is needed
   - Suggest approach for next iteration
   - Reference specific gaps to address

Return your analysis as JSON:
```json
{{
  "completion_score": 0.0-1.0,
  "confidence": 0.0-1.0,
  "goal_achieved": true/false,
  "action": "publish" | "partial_publish" | "replan",
  "gaps": [
    {{
      "type": "missing_step" | "failed_task" | "incomplete_output" | "validation_error",
      "severity": "critical" | "major" | "minor",
      "description": "...",
      "affected_task": "task_id",
      "recommendation": "..."
    }}
  ],
  "final_response": {{
    "message": "...",
    "format": "markdown"
  }},
  "replan_context": {{
    "reason": "...",
    "suggested_approach": "...",
    "priority_gaps": ["gap1", "gap2"]
  }},
  "summary": {{
    "user_query": "{user_query}",
    "execution_summary": "...",
    "outcome": "..."
  }}
}}
```

Important:
- Be objective and data-driven
- Don't replan unnecessarily - if results are good enough, publish
- Consider partial success as valid if it addresses user's core need
- Failed tasks don't always mean goal not achieved - evaluate impact
"""
        
        return prompt
    
    async def _call_llm_for_synthesis(self, prompt: str) -> str:
        """
        Call LLM to perform synthesis.
        
        Args:
            prompt: Synthesis prompt
            
        Returns:
            LLM response (JSON string)
        """
        try:
            # Build messages
            messages = [
                {"role": "system", "content": SYNTHESIZER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
            
            # Call LLM using generate_completion (the correct method name)
            # Note: Some models (e.g., o1) don't support custom temperature, so we use defaults
            response = await self.model_client.generate_completion(
                messages=messages
            )
            
            # Response is a string from generate_completion
            return response
                
        except Exception as e:
            logger.error(f"[Synthesizer] LLM call failed: {e}")
            raise
    
    def _parse_synthesis_response(
        self, 
        response: str, 
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse and validate the synthesis response from LLM.
        
        Args:
            response: Raw LLM response
            analysis: Pre-computed analysis for validation
            
        Returns:
            Validated synthesis report
        """
        try:
            # Extract JSON from response (may have markdown code blocks)
            json_str = self._extract_json_from_response(response)
            
            # Parse JSON
            synthesis = json.loads(json_str)
            
            # Validate required fields
            required_fields = [
                'completion_score', 'confidence', 'goal_achieved', 
                'action', 'gaps', 'summary'
            ]
            
            for field in required_fields:
                if field not in synthesis:
                    logger.warning(f"[Synthesizer] Missing field in response: {field}")
                    synthesis[field] = self._get_default_field_value(field)
            
            # Validate ranges
            synthesis['completion_score'] = max(0.0, min(1.0, synthesis['completion_score']))
            synthesis['confidence'] = max(0.0, min(1.0, synthesis['confidence']))
            
            # Validate action
            valid_actions = ['publish', 'partial_publish', 'replan']
            if synthesis['action'] not in valid_actions:
                logger.warning(f"[Synthesizer] Invalid action: {synthesis['action']}")
                synthesis['action'] = 'publish'
            
            # Add metadata
            synthesis['metadata'] = {
                'iteration_number': synthesis.get('metadata', {}).get('iteration_number', 1),
                'tasks_completed': analysis['successful_tasks'],
                'tasks_failed': analysis['failed_tasks'],
                'success_rate': analysis['success_rate']
            }
            
            return synthesis
            
        except json.JSONDecodeError as e:
            logger.error(f"[Synthesizer] Failed to parse JSON response: {e}")
            logger.error(f"Response was: {response[:500]}")
            raise
    
    def _extract_json_from_response(self, response: str) -> str:
        """
        Extract JSON from LLM response that may contain markdown code blocks.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Extracted JSON string
        """
        # Remove markdown code blocks if present
        if '```json' in response:
            start = response.find('```json') + 7
            end = response.find('```', start)
            return response[start:end].strip()
        elif '```' in response:
            start = response.find('```') + 3
            end = response.find('```', start)
            return response[start:end].strip()
        
        # Try to find JSON object
        if '{' in response and '}' in response:
            start = response.find('{')
            end = response.rfind('}') + 1
            return response[start:end]
        
        return response
    
    def _get_default_field_value(self, field: str) -> Any:
        """Get default value for a missing field"""
        defaults = {
            'completion_score': 0.5,
            'confidence': 0.5,
            'goal_achieved': False,
            'action': 'replan',
            'gaps': [],
            'summary': {
                'user_query': '',
                'execution_summary': 'Incomplete synthesis',
                'outcome': 'Unknown'
            },
            'final_response': {
                'message': 'Task processing incomplete',
                'format': 'markdown'
            },
            'replan_context': {
                'reason': 'Synthesis incomplete',
                'suggested_approach': 'Retry with corrected plan'
            }
        }
        return defaults.get(field)
    
    def _create_fallback_synthesis(
        self,
        user_query: str,
        execution_results: List[Dict[str, Any]],
        error_message: str
    ) -> Dict[str, Any]:
        """
        Create a safe fallback synthesis when synthesis fails.
        
        Args:
            user_query: User's query
            execution_results: Execution results
            error_message: Error that caused synthesis failure
            
        Returns:
            Fallback synthesis report
        """
        logger.warning("[Synthesizer] Creating fallback synthesis due to error")
        
        # Basic analysis
        total = len(execution_results)
        successful = sum(1 for r in execution_results if r.get('success', False))
        
        return {
            "completion_score": 0.5,
            "confidence": 0.3,
            "goal_achieved": False,
            "action": "replan",
            "gaps": [
                {
                    "type": "validation_error",
                    "severity": "critical",
                    "description": f"Synthesis agent encountered an error: {error_message}",
                    "recommendation": "Retry with simplified approach"
                }
            ],
            "final_response": {
                "message": f"I encountered an issue while processing your request. {successful}/{total} tasks completed.",
                "format": "markdown"
            },
            "replan_context": {
                "reason": f"Synthesis error: {error_message}",
                "suggested_approach": "Simplify task breakdown and retry"
            },
            "summary": {
                "user_query": user_query,
                "execution_summary": f"{successful}/{total} tasks completed before error",
                "outcome": "Synthesis failed - using fallback"
            },
            "metadata": {
                "synthesis_error": error_message,
                "fallback_used": True
            }
        }
