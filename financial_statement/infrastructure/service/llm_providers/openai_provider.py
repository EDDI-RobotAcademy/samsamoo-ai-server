import json
import logging
from typing import Dict, Any
from openai import AsyncOpenAI
from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider implementation"""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self._available = bool(api_key)

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.3
    ) -> str:
        """Generate text completion using OpenAI API"""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"OpenAI text generation failed: {e}")
            if "insufficient_quota" in str(e) or "429" in str(e):
                self._available = False
                logger.warning("OpenAI quota exceeded - marking provider as unavailable")
            raise

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Generate structured JSON response using OpenAI API"""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content.strip()
            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            raise
        except Exception as e:
            logger.error(f"OpenAI JSON generation failed: {e}")
            if "insufficient_quota" in str(e) or "429" in str(e):
                self._available = False
                logger.warning("OpenAI quota exceeded - marking provider as unavailable")
            raise

    def is_available(self) -> bool:
        """Check if OpenAI provider is available"""
        return self._available and self.client is not None

    def get_provider_name(self) -> str:
        """Get provider name"""
        return f"OpenAI ({self.model})"
