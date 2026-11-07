"""LLM initialization and management"""
from typing import Optional
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from .config import config

class LLMManager:
    """Manages LLM initialization and configuration"""
    
    def __init__(self):
        self.llm = None
        self.llm_with_tools = None
        self.fallback_llm = None
        self.fallback_llm_with_tools = None
        self.last_invocation_provider = ""
        self.last_invocation_used_fallback = False
        self.primary_provider = ""
    
    def initialize_llm(self) -> None:
        """Initialize the LLM based on available API keys"""
        if config.groq_api_key:
            self.primary_provider = "Groq"
            self.llm = ChatGroq(
                model=config.model_name,
                temperature=config.temperature,
            )
            if config.google_api_key:
                self.fallback_llm = ChatGoogleGenerativeAI(
                    model=config.gemini_model_name,
                    temperature=config.temperature,
                )
        elif config.google_api_key:
            self.primary_provider = "Gemini"
            self.llm = ChatGoogleGenerativeAI(
                model=config.gemini_model_name,
                temperature=config.temperature,
            )
        else:
            raise ValueError("No valid API key found. Please set GROQ_API_KEY or GOOGLE_API_KEY")
    
    def bind_tools(self, tools: list) -> None:
        """Bind tools to the LLM"""
        if not self.llm:
            raise ValueError("LLM not initialized. Call initialize_llm() first")
        self.llm_with_tools = self.llm.bind_tools(tools)
        if self.fallback_llm:
            self.fallback_llm_with_tools = self.fallback_llm.bind_tools(tools)
    
    def get_llm(self):
        """Get the initialized LLM"""
        return self.llm
    
    def get_llm_with_tools(self):
        """Get the LLM with tools bound"""
        return self.llm_with_tools

    def invoke(self, messages):
        """Invoke the base model, falling back to Gemini on Groq quota limits."""
        return self._invoke_with_fallback(self.llm, self.fallback_llm, messages)

    def invoke_with_tools(self, messages):
        """Invoke the tool-bound model, falling back to Gemini on Groq quota limits."""
        return self._invoke_with_fallback(
            self.llm_with_tools, self.fallback_llm_with_tools, messages
        )

    def _invoke_with_fallback(self, primary, fallback, messages):
        self.last_invocation_used_fallback = False
        try:
            response = primary.invoke(messages)
            self.last_invocation_provider = self.primary_provider
            return response
        except Exception as error:
            is_quota_error = "429" in str(error) or "rate_limit" in str(error).lower()
            if fallback and is_quota_error:
                self.last_invocation_used_fallback = True
                self.last_invocation_provider = "Gemini"
                return fallback.invoke(messages)
            raise

    @property
    def has_gemini_fallback(self) -> bool:
        return self.fallback_llm is not None
