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
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # AI Model API Keys
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str = ""  # Optional: for Claude models
    
    # Service Authentication
    INTERNAL_API_SECRET: str
    JWT_SECRET: str = "your-secret-key-change-in-production"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_DAY: int = 1000
    
    # Context Storage
    CONTEXT_STORAGE_PATH: str = "/app/agent_context"

    # Agent Call Log Storage (file-based, mirrors AgentCallLog table)
    AGENT_CALL_LOG_PATH: str = "/app/agent_call_logs"
    
    # Agent Configuration
    ENABLE_OPENAI_TOOLS: bool = True
    USE_DUMMY_AI: bool = False  # When True, returns dummy responses without AI API calls
    
    # Workflow Orchestrator Configuration
    USE_WORKFLOW_ORCHESTRATOR: bool = False  # When True, uses Plan→Execute→Synthesize→Replan pattern
    MAX_WORKFLOW_ITERATIONS: int = 3  # Maximum iterations before forcing completion
    
    # Agent Model Configuration
    PLANNER_MODEL: str = "gpt-4"
    CONTEXT_MANAGER_MODEL: str = "gpt-4"
    
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
