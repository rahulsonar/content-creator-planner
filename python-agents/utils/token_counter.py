"""
Token Counter Utility
Estimates token counts for text (approximate)
"""



def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Estimate token count for text
    
    This is a simple approximation. For precise counting, use tiktoken library.
    Rule of thumb: ~4 characters per token for English text
    
    Args:
        text: Text to count
        model: Model identifier (for future precise counting)
        
    Returns:
        Approximate token count
    """
    if not text:
        return 0
    
    # Simple approximation: 4 chars per token
    # Adjust for whitespace and punctuation
    words = len(text.split())
    chars = len(text)
    
    # Average between word-based and char-based estimation
    word_estimate = words * 1.3  # ~1.3 tokens per word
    char_estimate = chars / 4     # ~4 chars per token
    
    estimated = int((word_estimate + char_estimate) / 2)
    
    return max(estimated, 1)  # Minimum 1 token


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str
) -> float:
    """
    Estimate cost for API call
    
    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model identifier
        
    Returns:
        Estimated cost in USD
    """
    # Cost per 1M tokens (input, output)
    costs = {
        "gpt-3.5-turbo": (0.50, 1.50),
        "gpt-4": (10.00, 30.00),
        "gpt-4-turbo": (10.00, 30.00),
        "claude-3-5-sonnet": (3.00, 15.00),
        "claude-3.5-sonnet": (3.00, 15.00),
    }
    
    if model not in costs:
        # Default to GPT-3.5 pricing
        model = "gpt-3.5-turbo"
    
    input_cost_per_m, output_cost_per_m = costs[model]
    
    input_cost = (input_tokens / 1_000_000) * input_cost_per_m
    output_cost = (output_tokens / 1_000_000) * output_cost_per_m
    
    return input_cost + output_cost


def truncate_text(
    text: str,
    max_tokens: int,
    model: str = "gpt-3.5-turbo"
) -> str:
    """
    Truncate text to fit within token limit
    
    Args:
        text: Text to truncate
        max_tokens: Maximum token count
        model: Model identifier
        
    Returns:
        Truncated text
    """
    current_tokens = count_tokens(text, model)
    
    if current_tokens <= max_tokens:
        return text
    
    # Approximate ratio to truncate by
    ratio = max_tokens / current_tokens
    target_chars = int(len(text) * ratio * 0.9)  # 90% to be safe
    
    truncated = text[:target_chars]
    
    # Try to end at sentence boundary
    last_period = truncated.rfind('.')
    last_newline = truncated.rfind('\n')
    
    cutoff = max(last_period, last_newline)
    if cutoff > target_chars * 0.8:  # If we found a good boundary
        truncated = truncated[:cutoff + 1]
    
    return truncated + "..."
