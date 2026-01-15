"""
Base Agent Class
Abstract base class for all AI agents
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from utils.logger import logger
from utils.token_counter import count_tokens


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, model_client, agent_type: str):
        """
        Initialize base agent
        
        Args:
            model_client: LLM client (OpenAI or Anthropic)
            agent_type: Type identifier (e.g., "onboarding", "planning")
        """
        self.model_client = model_client
        self.agent_type = agent_type
        self.conversation_history: List[Dict[str, str]] = []
    
    @abstractmethod
    async def process_message(
        self, 
        user_message: str, 
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process a user message and return agent response
        
        Args:
            user_message: User's input message
            user_context: Optional user context data
            
        Returns:
            Agent's response message
        """
        pass
    
    @abstractmethod
    async def stream_response(
        self,
        user_message: str,
        user_context: Optional[Dict[str, Any]] = None
    ):
        """
        Stream response tokens in real-time
        
        Args:
            user_message: User's input message
            user_context: Optional user context data
            
        Yields:
            Response tokens as they're generated
        """
        pass
    
    def add_to_history(self, role: str, content: str):
        """
        Add message to conversation history
        
        Args:
            role: Message role (user/assistant/system)
            content: Message content
        """
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        logger.debug(f"Added {role} message to {self.agent_type} history")
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history"""
        return self.conversation_history
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info(f"Cleared {self.agent_type} conversation history")
    
    def get_token_count(self) -> int:
        """
        Calculate total tokens in conversation history
        
        Returns:
            Total token count
        """
        total = 0
        for message in self.conversation_history:
            total += count_tokens(message["content"])
        return total
    
    def truncate_history(self, max_messages: int = 20):
        """
        Truncate conversation history to last N messages
        Keep system message if present
        
        Args:
            max_messages: Maximum number of messages to keep
        """
        if len(self.conversation_history) <= max_messages:
            return
        
        # Keep system message if it exists
        system_msg = None
        if self.conversation_history[0]["role"] == "system":
            system_msg = self.conversation_history[0]
            history = self.conversation_history[1:]
        else:
            history = self.conversation_history
        
        # Keep last N messages
        truncated = history[-max_messages:]
        
        # Rebuild history
        if system_msg:
            self.conversation_history = [system_msg] + truncated
        else:
            self.conversation_history = truncated
        
        logger.info(f"Truncated {self.agent_type} history to {len(self.conversation_history)} messages")
