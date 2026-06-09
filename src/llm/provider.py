"""LLM provider abstraction with real API implementations and fallback chain."""
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum
import logging
import anthropic
import openai
import requests

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Available LLM providers."""
    CLAUDE = "claude"
    OPENAI = "openai"
    OLLAMA = "local"


@dataclass
class LLMMessage:
    """Message for LLM chat completion."""
    role: str
    content: str


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    provider: LLMProvider
    model: str
    tokens_used: Optional[int] = None
    cache_hit: bool = False
    error: Optional[str] = None

    def is_successful(self) -> bool:
        return self.error is None


class LLMClient:
    """Unified LLM client with provider fallback chain."""

    DEFAULT_MODELS = {
        LLMProvider.CLAUDE: "claude-sonnet-4-6",
        LLMProvider.OPENAI: "gpt-4o",
        LLMProvider.OLLAMA: "qwen2.5:7b"
    }

    def __init__(
        self,
        provider: Union[str, LLMProvider] = LLMProvider.CLAUDE,
        anthropic_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        ollama_base_url: str = "http://localhost:11434"
    ):
        if isinstance(provider, str):
            provider = LLMProvider(provider)

        self.primary_provider = provider
        self.anthropic_api_key = anthropic_api_key
        self.openai_api_key = openai_api_key
        self.ollama_base_url = ollama_base_url

        self.fallback_chain = self._build_fallback_chain()

    def _build_fallback_chain(self) -> List[LLMProvider]:
        """Build fallback chain based on available API keys."""
        chain = []
        if self.anthropic_api_key:
            chain.append(LLMProvider.CLAUDE)
        if self.openai_api_key:
            chain.append(LLMProvider.OPENAI)
        chain.append(LLMProvider.OLLAMA)  # Always available locally
        return chain

    def chat_completion(
        self,
        messages: List[LLMMessage],
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        use_cache: bool = True
    ) -> LLMResponse:
        """Generate chat completion with provider fallback."""
        providers_to_try = [provider] if provider else self.fallback_chain

        for prov in providers_to_try:
            if prov not in self.fallback_chain:
                continue

            try:
                response = self._call_provider(
                    prov,
                    messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    use_cache=use_cache
                )
                if response.is_successful():
                    return response
            except Exception as e:
                logger.warning(f"Provider {prov} failed: {e}")

        return LLMResponse(
            content="",
            provider=LLMProvider.OLLAMA,
            model=self.DEFAULT_MODELS[LLMProvider.OLLAMA],
            error="All providers failed"
        )

    def _call_provider(
        self,
        provider: LLMProvider,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        use_cache: bool = True
    ) -> LLMResponse:
        """Call specific provider implementation."""
        model = model or self.DEFAULT_MODELS.get(provider)

        if provider == LLMProvider.CLAUDE:
            return self._call_claude(messages, model, temperature, max_tokens, use_cache)
        elif provider == LLMProvider.OPENAI:
            return self._call_openai(messages, model, temperature, max_tokens)
        elif provider == LLMProvider.OLLAMA:
            return self._call_ollama(messages, model, temperature, max_tokens)

        return LLMResponse(
            content="",
            provider=provider,
            model=model or "",
            error=f"Unknown provider: {provider}"
        )

    def _call_claude(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int,
        use_cache: bool
    ) -> LLMResponse:
        """Call Claude API via Anthropic SDK."""
        if not self.anthropic_api_key:
            return LLMResponse(
                content="",
                provider=LLMProvider.CLAUDE,
                model=model,
                error="No API key provided"
            )

        try:
            client = anthropic.Anthropic(api_key=self.anthropic_api_key)

            system_message = None
            api_messages = []

            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    api_messages.append({"role": msg.role, "content": msg.content})

            kwargs = {
                "model": model,
                "messages": api_messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            if system_message:
                kwargs["system"] = system_message

            response = client.messages.create(**kwargs)

            return LLMResponse(
                content=response.content[0].text,
                provider=LLMProvider.CLAUDE,
                model=model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                cache_hit=getattr(response, 'cache_hit', False)
            )

        except anthropic.APIError as e:
            return LLMResponse(
                content="",
                provider=LLMProvider.CLAUDE,
                model=model,
                error=str(e)
            )

    def _call_openai(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call OpenAI API for GPT-4o."""
        if not self.openai_api_key:
            return LLMResponse(
                content="",
                provider=LLMProvider.OPENAI,
                model=model,
                error="No API key provided"
            )

        try:
            client = openai.OpenAI(api_key=self.openai_api_key)

            api_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            response = client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                provider=LLMProvider.OPENAI,
                model=model,
                tokens_used=response.usage.total_tokens
            )

        except openai.APIError as e:
            return LLMResponse(
                content="",
                provider=LLMProvider.OPENAI,
                model=model,
                error=str(e)
            )

    def _call_ollama(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call local Ollama model."""
        try:
            prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])

            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                },
                timeout=120
            )

            if response.status_code == 200:
                data = response.json()
                return LLMResponse(
                    content=data.get("response", ""),
                    provider=LLMProvider.OLLAMA,
                    model=model
                )

            return LLMResponse(
                content="",
                provider=LLMProvider.OLLAMA,
                model=model,
                error=f"Ollama request failed: {response.status_code}"
            )

        except Exception as e:
            return LLMResponse(
                content="",
                provider=LLMProvider.OLLAMA,
                model=model,
                error=str(e)
            )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
