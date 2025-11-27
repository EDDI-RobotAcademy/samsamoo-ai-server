import os
import logging
from typing import Optional
from .base_provider import BaseLLMProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .template_provider import TemplateProvider

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """
    Factory for creating LLM provider instances based on configuration.

    Supported providers:
    - openai: OpenAI GPT models (gpt-4o, gpt-4-turbo, gpt-3.5-turbo)
    - anthropic: Anthropic Claude models (claude-3-5-sonnet, claude-3-opus)
    - template: Template-based analysis (no API required)
    """

    @staticmethod
    def create_provider(
        provider_type: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ) -> BaseLLMProvider:
        """
        Create an LLM provider instance.

        Args:
            provider_type: Provider type ("openai", "anthropic", "template", "auto")
            api_key: API key for the provider (optional, can use env vars)
            model: Model name (optional, uses provider defaults)

        Returns:
            BaseLLMProvider instance

        Environment Variables:
            LLM_PROVIDER: Provider type (default: "auto")
            OPENAI_API_KEY: OpenAI API key
            OPENAI_MODEL: OpenAI model name (default: "gpt-4o")
            ANTHROPIC_API_KEY: Anthropic API key
            ANTHROPIC_MODEL: Anthropic model name (default: "claude-3-5-sonnet-20241022")
        """
        # Get configuration from environment if not provided
        if provider_type is None:
            provider_type = os.getenv("LLM_PROVIDER", "auto").lower()

        logger.info(f"Creating LLM provider: {provider_type}")

        # Auto-detect provider based on available API keys
        if provider_type == "auto":
            provider_type = LLMProviderFactory._auto_detect_provider()
            logger.info(f"Auto-detected provider: {provider_type}")

        # Create provider instance
        if provider_type == "openai":
            return LLMProviderFactory._create_openai_provider(api_key, model)
        elif provider_type == "anthropic":
            return LLMProviderFactory._create_anthropic_provider(api_key, model)
        elif provider_type == "template":
            return TemplateProvider()
        else:
            logger.warning(f"Unknown provider type: {provider_type}, falling back to template")
            return TemplateProvider()

    @staticmethod
    def _auto_detect_provider() -> str:
        """Auto-detect which provider to use based on available API keys"""
        # Check for OpenAI key first (most common)
        if os.getenv("OPENAI_API_KEY"):
            return "openai"

        # Check for Anthropic key
        if os.getenv("ANTHROPIC_API_KEY"):
            return "anthropic"

        # Fallback to template
        logger.info("No API keys found, using template provider")
        return "template"

    @staticmethod
    def _create_openai_provider(api_key: Optional[str], model: Optional[str]) -> OpenAIProvider:
        """Create OpenAI provider instance"""
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY", "")

        if model is None:
            model = os.getenv("OPENAI_MODEL", "gpt-4o")

        if not api_key:
            logger.warning("OpenAI API key not found, provider will be unavailable")

        return OpenAIProvider(api_key=api_key, model=model)

    @staticmethod
    def _create_anthropic_provider(api_key: Optional[str], model: Optional[str]) -> AnthropicProvider:
        """Create Anthropic provider instance"""
        if api_key is None:
            api_key = os.getenv("ANTHROPIC_API_KEY", "")

        if model is None:
            model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

        if not api_key:
            logger.warning("Anthropic API key not found, provider will be unavailable")

        return AnthropicProvider(api_key=api_key, model=model)

    @staticmethod
    def get_available_providers() -> dict:
        """Get information about all available providers"""
        return {
            "openai": {
                "name": "OpenAI",
                "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
                "configured": bool(os.getenv("OPENAI_API_KEY"))
            },
            "anthropic": {
                "name": "Anthropic Claude",
                "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
                "configured": bool(os.getenv("ANTHROPIC_API_KEY"))
            },
            "template": {
                "name": "Template (No AI)",
                "models": ["template"],
                "configured": True
            }
        }
