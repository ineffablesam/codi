"""Multi-model LLM provider factory.

Supports:
- OpenAI: GPT-5.2, GPT-4.1
- Anthropic: Claude Opus 4.5, Claude Sonnet 4.5
- Google: Gemini 3 Flash, Gemini 3 Pro
"""
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Model provider mapping
PROVIDER_MODELS = {
    "openai": ["gpt-5.2", "gpt-4.1", "gpt-4.1-turbo"],
    "anthropic": ["claude-opus-4-5", "claude-sonnet-4-5"],
    "gemini": ["gemini-3-pro-preview", "gemini-3-flash-preview", "gemini-3-pro-high"],
}

# Default temperature for Gemini 3 (recommended by Google)
GEMINI_DEFAULT_TEMPERATURE = 1.0


def get_llm(
    provider: str,
    model_name: str,
    temperature: float = 1.0,
    max_tokens: int = 8192,
    streaming: bool = False,
    **kwargs: Any,
) -> BaseChatModel:
    """Factory for creating LLM instances.
    
    Args:
        provider: LLM provider ("openai", "anthropic", "gemini")
        model_name: Model name
        temperature: Sampling temperature (default 1.0 for Gemini 3)
        max_tokens: Maximum output tokens
        streaming: Enable streaming responses
        **kwargs: Additional provider-specific arguments
    
    Returns:
        Configured LLM instance
    
    Raises:
        ValueError: If provider is not supported or API key is missing
    """
    if settings.force_gemini_overall:
        # Force Gemini for all agents (cost-efficient mode)
        return _create_gemini_llm(model_name or "gemini-3-flash-preview", temperature, max_tokens, streaming)
    
    if provider == "openai":
        return _create_openai_llm(model_name, temperature, max_tokens, streaming)
    elif provider == "anthropic":
        return _create_anthropic_llm(model_name, temperature, max_tokens, streaming)
    elif provider == "gemini":
        return _create_gemini_llm(model_name, temperature, max_tokens, streaming)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def _create_openai_llm(
    model_name: str,
    temperature: float,
    max_tokens: int,
    streaming: bool,
) -> BaseChatModel:
    """Create OpenAI LLM instance."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError(
            "langchain-openai not installed. Run: pip install langchain-openai"
        )
    
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Add it to your .env file for GPT models."
        )
    
    logger.info(f"Creating OpenAI LLM: {model_name}")
    
    return ChatOpenAI(
        model=model_name,
        api_key=settings.openai_api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
    )


def _create_anthropic_llm(
    model_name: str,
    temperature: float,
    max_tokens: int,
    streaming: bool,
) -> BaseChatModel:
    """Create Anthropic LLM instance."""
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError(
            "langchain-anthropic not installed. Run: pip install langchain-anthropic"
        )
    
    if not settings.anthropic_api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file for Claude models."
        )
    
    logger.info(f"Creating Anthropic LLM: {model_name}")
    
    return ChatAnthropic(
        model=model_name,
        api_key=settings.anthropic_api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
    )


def _create_gemini_llm(
    model_name: str,
    temperature: float,
    max_tokens: int,
    streaming: bool,
) -> BaseChatModel:
    """Create Gemini LLM instance."""
    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Add it to your .env file."
        )
    
    logger.info(f"Creating Gemini LLM: {model_name}")
    
    return ChatGoogleGenerativeAI(
        model=model_name or settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=temperature,
        max_output_tokens=max_tokens,
        streaming=streaming,
        convert_system_message_to_human=False,
    )


def get_provider_for_model(model_name: str) -> str:
    """Determine provider from model name.
    
    Args:
        model_name: Model name
        
    Returns:
        Provider name
    """
    model_lower = model_name.lower()
    
    if "gpt" in model_lower:
        return "openai"
    elif "claude" in model_lower:
        return "anthropic"
    elif "gemini" in model_lower:
        return "gemini"
    
    # Default to gemini
    return "gemini"


# Agent model configuration - maps agent names to their preferred models
AGENT_MODEL_CONFIG = {
    # Orchestration
    "conductor": {"provider": "anthropic", "model": "claude-opus-4-5"},
    "strategist": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
    "analyst": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
    
    # Strategic
    "sage": {"provider": "openai", "model": "gpt-5.2"},
    "scholar": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
    
    # Fast/Exploration
    "scout": {"provider": "gemini", "model": "gemini-3-flash-preview"},
    "scribe": {"provider": "gemini", "model": "gemini-3-flash-preview"},
    "vision": {"provider": "gemini", "model": "gemini-3-flash-preview"},
    
    # Creative/Visual
    "artisan": {"provider": "gemini", "model": "gemini-3-pro-high"},
    
    # Platform Engineers (default to Gemini Pro)
    "flutter_engineer": {"provider": "gemini", "model": "gemini-3-pro-preview"},
    "react_engineer": {"provider": "gemini", "model": "gemini-3-pro-preview"},
    "nextjs_engineer": {"provider": "gemini", "model": "gemini-3-pro-preview"},
    "react_native_engineer": {"provider": "gemini", "model": "gemini-3-pro-preview"},
    
    # Operations
    "code_reviewer": {"provider": "gemini", "model": "gemini-3-pro-preview"},
    "git_operator": {"provider": "gemini", "model": "gemini-3-flash-preview"},
    "build_deploy": {"provider": "gemini", "model": "gemini-3-flash-preview"},
    "memory": {"provider": "gemini", "model": "gemini-3-flash-preview"},
    "planner": {"provider": "gemini", "model": "gemini-3-pro-preview"},
}


def get_llm_for_agent(agent_name: str, **kwargs: Any) -> BaseChatModel:
    """Get the configured LLM for a specific agent.
    
    Args:
        agent_name: Name of the agent
        **kwargs: Override default LLM settings
        
    Returns:
        Configured LLM for the agent
    """
    config = AGENT_MODEL_CONFIG.get(agent_name, {
        "provider": "gemini",
        "model": "gemini-3-flash-preview",
    })
    
    return get_llm(
        provider=config["provider"],
        model_name=config["model"],
        **kwargs,
    )
