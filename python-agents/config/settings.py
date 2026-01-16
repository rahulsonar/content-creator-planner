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
    
    # Agent Configuration
    ENABLE_OPENAI_TOOLS: bool = True
    USE_DUMMY_AI: bool = False  # When True, returns dummy responses without AI API calls
    
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
