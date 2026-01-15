"""
Onboarding Agent
Handles user onboarding conversation flow
"""
from typing import Dict, Any, Optional
from agents.base import BaseAgent
from config.prompts import ONBOARDING_SYSTEM_PROMPT, ONBOARDING_WELCOME_MESSAGE
from utils.logger import logger


class OnboardingAgent(BaseAgent):
    """Agent for user onboarding conversations"""
    
    def __init__(self, model_client):
        super().__init__(model_client, "onboarding")
        self.current_step = "welcome"
        self.collected_data = {}
        
        # Initialize with system prompt
        self.add_to_history("system", ONBOARDING_SYSTEM_PROMPT)
    
    async def start_onboarding(self) -> str:
        """
        Start onboarding conversation
        
        Returns:
            Welcome message
        """
        logger.info("Starting onboarding conversation")
        self.add_to_history("assistant", ONBOARDING_WELCOME_MESSAGE)
        return ONBOARDING_WELCOME_MESSAGE
    
    async def process_message(
        self,
        user_message: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process user's onboarding response
        
        Args:
            user_message: User's response
            user_context: Existing user context if any
            
        Returns:
            Next question or confirmation message
        """
        # Add user message to history
        self.add_to_history("user", user_message)
        
        # Generate response using model
        try:
            response = await self.model_client.generate_completion(
                messages=self.conversation_history,
                temperature=0.7,
                max_tokens=300
            )
            
            # Add assistant response to history
            self.add_to_history("assistant", response)
            
            logger.info(f"Onboarding step: {self.current_step}")
            return response
            
        except Exception as e:
            logger.error(f"Error in onboarding agent: {e}")
            return "I apologize, but I encountered an error. Could you please try again?"
    
    async def stream_response(
        self,
        user_message: str,
        user_context: Optional[Dict[str, Any]] = None
    ):
        """
        Stream onboarding response in real-time
        
        Args:
            user_message: User's response
            user_context: Existing user context
            
        Yields:
            Response tokens
        """
        # Add user message to history
        self.add_to_history("user", user_message)
        
        # Stream response from model
        full_response = ""
        try:
            async for token in self.model_client.stream_completion(
                messages=self.conversation_history,
                temperature=0.7,
                max_tokens=300
            ):
                full_response += token
                yield token
            
            # Add complete response to history
            self.add_to_history("assistant", full_response)
            
        except Exception as e:
            logger.error(f"Error streaming onboarding response: {e}")
            yield "I apologize, but I encountered an error. Could you please try again?"
    
    def extract_context_data(self) -> Dict[str, Any]:
        """
        Extract structured data from conversation
        
        Returns:
            Dictionary of extracted context fields
        """
        # TODO: Implement context extraction logic
        # This would use the conversation history to extract:
        # - channelName, channelType, contentGoals, etc.
        logger.info("Extracting context data from onboarding conversation")
        return self.collected_data
    
    def is_complete(self) -> bool:
        """
        Check if onboarding is complete
        
        Returns:
            True if all required information gathered
        """
        # TODO: Implement completion check
        # Check if all required fields are collected
        return len(self.conversation_history) >= 15  # Placeholder logic
