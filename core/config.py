"""Configuration management for Code Assistant"""
import os
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Config(BaseModel):
    """Application configuration"""
    
    # API Keys
    google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
    groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
    github_token: Optional[str] = os.getenv("GITHUB_TOKEN")
    
    # LLM Settings
    model_name: str = "openai/gpt-oss-120b"
    gemini_model_name: str = "gemini-2.5-flash"
    temperature: float = 0.0
    
    # Agent Settings
    max_retries: int = 3
    recursion_limit: int = 20
    max_tool_rounds: int = 8
    llm_rate_limit_retries: int = 2
    recent_message_limit: int = 5
    memory_summary_max_chars: int = 4000
    memory_compression_input_max_chars: int = 6000
    
    # File Settings
    supported_extensions: list[str] = ['.py', '.js', '.ts', '.txt', '.md', '.json', '.yml', '.yaml']
    
    def validate_api_keys(self) -> bool:
        """Validate required API keys are present"""
        return bool(self.google_api_key or self.groq_api_key)

config = Config()
