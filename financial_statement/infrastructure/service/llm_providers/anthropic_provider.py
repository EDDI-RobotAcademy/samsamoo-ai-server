import json
import logging
from typing import Dict, Any
from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider implementation"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model
        self.client = None
        self._available = False

        if api_key:
            try:
                from anthropic import AsyncAnthropic
                self.client = AsyncAnthropic(api_key=api_key)
                self._available = True
                logger.info(f"Anthropic provider initialized with model: {model}")
            except ImportError:
                logger.warning("anthropic package not installed. Install with: pip install anthropic")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.3
    ) -> str:
        """Generate text completion using Anthropic API"""
        if not self.client:
            raise RuntimeError("Anthropic client not initialized")

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.content[0].text.strip()

        except Exception as e:
            logger.error(f"Anthropic text generation failed: {e}")
            if "insufficient_quota" in str(e) or "429" in str(e):
                self._available = False
                logger.warning("Anthropic quota exceeded - marking provider as unavailable")
            raise

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Generate structured JSON response using Anthropic API"""
        if not self.client:
            raise RuntimeError("Anthropic client not initialized")

        # Add JSON instruction to prompts
        enhanced_system = f"{system_prompt}\n\nRespond only with valid JSON."
        enhanced_user = f"{user_prompt}\n\nProvide your response as valid JSON only, with no additional text."

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=enhanced_system,
                messages=[
                    {"role": "user", "content": enhanced_user}
                ]
            )

            content = response.content[0].text.strip()
            # Extract JSON if wrapped in markdown code blocks
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Anthropic JSON response: {e}")
            raise
        except Exception as e:
            logger.error(f"Anthropic JSON generation failed: {e}")
            if "insufficient_quota" in str(e) or "429" in str(e):
                self._available = False
                logger.warning("Anthropic quota exceeded - marking provider as unavailable")
            raise

    def is_available(self) -> bool:
        """Check if Anthropic provider is available"""
        return self._available and self.client is not None

    def get_provider_name(self) -> str:
        """Get provider name"""
        return f"Anthropic Claude ({self.model})"
