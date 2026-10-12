"""
Configuration Settings Management
Uses pydantic-settings for environment variable handling
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    DATABASE_URL: str
    
    # AI Model API Keys
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str = ""  # Optional: for Claude models

    # Claude Configuration (used when a *_MODEL setting starts with "claude-")
    ANTHROPIC_DEFAULT_MODEL: str = "claude-opus-5-5"
    ANTHROPIC_EFFORT: str = "medium"  # low | medium | high | xhigh | max
    ANTHROPIC_MAX_TOKENS: int = 16000  # Covers thinking + reply; thinking is always on
    ANTHROPIC_REFUSAL_FALLBACK: bool = True  # Retry classifier refusals on a fallback model
    
    # Service Authentication
    INTERNAL_API_SECRET: str
    JWT_SECRET: str = ""  # Unused here; JWTs are issued and verified by the Next.js app
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Agent Call Log Storage (file-based, mirrors AgentCallLog table)
    AGENT_CALL_LOG_PATH: str = "/app/agent_call_logs"
    
    # Agent Configuration
    USE_DUMMY_AI: bool = False  # When True, returns dummy responses without AI API calls

    # Planner Agent Configuration
    PLANNER_AGENT_MODEL: str = "claude-opus-5-5"
    PLANNER_AGENT_MAX_STEPS: int = 15  # Maximum model turns before forcing a final answer
    
    # WebSocket Webhook
    NEXTJS_WEBHOOK_URL: str = "http://app:3000/api/chat/webhook"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"


# Global settings instance
settings = Settings()
