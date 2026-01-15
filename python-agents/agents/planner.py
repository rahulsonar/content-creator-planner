"""
Planning Agent
Generates content project plans and task breakdowns
"""
from typing import Dict, Any, Optional, List
from agents.base import BaseAgent
from config.prompts import PLANNING_SYSTEM_PROMPT, PLANNING_TASK_FORMAT_EXAMPLE
from utils.logger import logger


class PlanningAgent(BaseAgent):
    """Agent for content planning and task generation"""
    
    def __init__(self, model_client):
        super().__init__(model_client, "planning")
        
        # Initialize with system prompt
        self.add_to_history("system", PLANNING_SYSTEM_PROMPT)
        self.add_to_history("system", f"Task Format Example:\n{PLANNING_TASK_FORMAT_EXAMPLE}")
    
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
        Process planning-related questions
        
        Args:
            user_message: User's question or request
            user_context: User's profile context
            
        Returns:
            Agent's response
        """
        self.add_to_history("user", user_message)
        
        try:
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
        Stream planning response in real-time
        
        Args:
            user_message: User's request
            user_context: User's profile context
            
        Yields:
            Response tokens
        """
        self.add_to_history("user", user_message)
        
        full_response = ""
        try:
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
