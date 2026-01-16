"""
Model Orchestrator
Selects appropriate AI model based on task type and context
"""
from typing import Literal
from utils.logger import logger

ModelType = Literal["gpt-3.5-turbo", "gpt-4", "claude-3.5-sonnet"]


class ModelOrchestrator:
    """Orchestrates model selection based on task requirements"""
    
    # Model cost per 1M tokens (input / output)
    MODEL_COSTS = {
        "gpt-3.5-turbo": (0.50, 1.50),
        "gpt-4": (10.00, 30.00),
        "claude-3.5-sonnet": (3.00, 15.00),
    }
    
    @staticmethod
    def select_model(
        task_type: str,
        context_length: int = 0,
        complexity: str = "medium"
    ) -> ModelType:
        """
        Select appropriate model based on task characteristics
        
        Args:
            task_type: Type of task (onboarding_initial, onboarding_final, planning, chat)
            context_length: Length of context in tokens
            complexity: Task complexity (low, medium, high)
            
        Returns:
            Selected model identifier
        """
        logger.info(f"Selecting model for task_type={task_type}, context_length={context_length}, complexity={complexity}")
        
        # Onboarding - start with cheaper model
        if task_type == "onboarding_initial":
            return "gpt-3.5-turbo"
        
        # Onboarding - final synthesis requires nuance
        if task_type == "onboarding_final":
            return "gpt-4"
        
        # Planning with long context
        if task_type == "planning" and context_length > 8000:
            return "claude-3.5-sonnet"
        
        # Planning with standard context
        if task_type == "planning":
            return "gpt-5"
        
        # High complexity tasks
        if complexity == "high":
            return "gpt-5"
        
        # General chat - use efficient model
        if task_type == "chat":
            return "gpt-3.5-turbo"
        
        # Default to cost-effective option
        return "gpt-3.5-turbo"
    
    @staticmethod
    def calculate_cost(
        model: ModelType,
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
            logger.warning(f"Unknown model: {model}, using default cost")
            return 0.0
        
        input_cost_per_m, output_cost_per_m = ModelOrchestrator.MODEL_COSTS[model]
        
        input_cost = (input_tokens / 1_000_000) * input_cost_per_m
        output_cost = (output_tokens / 1_000_000) * output_cost_per_m
        
        total_cost = input_cost + output_cost
        
        logger.debug(f"Cost calculation: {model} = ${total_cost:.6f}")
        return total_cost
    
    @staticmethod
    def should_upgrade_model(
        current_model: ModelType,
        error_rate: float,
        quality_score: float
    ) -> ModelType:
        """
        Determine if model should be upgraded for better quality
        
        Args:
            current_model: Current model in use
            error_rate: Recent error rate (0-1)
            quality_score: Quality assessment score (0-1)
            
        Returns:
            Recommended model (may be same or upgraded)
        """
        # High error rate or low quality - upgrade
        if error_rate > 0.2 or quality_score < 0.6:
            if current_model == "gpt-3.5-turbo":
                logger.info("Upgrading from GPT-3.5 to GPT-4 due to quality issues")
                return "gpt-4"
            if current_model == "gpt-4":
                logger.info("Upgrading from GPT-4 to Claude due to quality issues")
                return "claude-3.5-sonnet"
        
        # Current model is performing well
        return current_model
