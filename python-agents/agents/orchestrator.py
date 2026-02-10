"""
Model Orchestrator
Retrieves configured models from environment and provides cost utilities
"""
from typing import Dict, Tuple
from utils.logger import logger
from config.settings import settings


class ModelOrchestrator:
    """Orchestrates model configuration and cost tracking"""
    
    # Model cost per 1M tokens (input / output)
    MODEL_COSTS: Dict[str, Tuple[float, float]] = {
        "gpt-3.5-turbo": (0.50, 1.50),
        "gpt-4": (10.00, 30.00),
        "gpt-5": (15.00, 45.00),
        "claude-sonnet-4.5": (3.00, 15.00),
        "claude-opus-4": (15.00, 75.00),
    }
    
    @staticmethod
    def get_model_for_agent(agent_type: str) -> str:
        """
        Get the configured model for an agent from environment
        
        Args:
            agent_type: Type of agent (planning, context_manager)
            
        Returns:
            Model name from env configuration
            
        Raises:
            ValueError: If agent_type is not recognized
        """
        # Map agent types to env settings
        env_mapping = {
            "planning": settings.PLANNER_MODEL,
            "context_manager": settings.CONTEXT_MANAGER_MODEL,
        }
        
        configured_model = env_mapping.get(agent_type)
        
        if not configured_model:
            raise ValueError(f"No model configured for agent type: {agent_type}")
        
        logger.info(f"Using configured model for {agent_type}: {configured_model}")
        return configured_model
    
    @staticmethod
    def calculate_cost(
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate estimated cost for a request
        
        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        if model not in ModelOrchestrator.MODEL_COSTS:
            logger.warning(f"Unknown model: {model}, cannot calculate cost")
            return 0.0
        
        input_cost_per_m, output_cost_per_m = ModelOrchestrator.MODEL_COSTS[model]
        
        input_cost = (input_tokens / 1_000_000) * input_cost_per_m
        output_cost = (output_tokens / 1_000_000) * output_cost_per_m
        
        total_cost = input_cost + output_cost
        
        logger.debug(f"Cost calculation: {model} = ${total_cost:.6f}")
        return total_cost
