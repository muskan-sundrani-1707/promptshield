"""
LLM provider adapters.
Every provider has the same method: chat(system_prompt, user_message) -> text.
Switching models = changing a config value, no other code changes.
API keys are read from the .env file only (never hardcoded, never sent to the frontend).
"""
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

# .env lives in the project root: promptshield/.env
load_dotenv(Path(__file__).resolve().parents[3] / ".env")


class LLMError(Exception):
    """Raised when an LLM call fails (network, bad key, bad model, etc.)."""


def _post(url: str, payload: dict, headers: dict, timeout: float = 120.0) -> dict:
    """POST JSON and return parsed JSON, converting every failure into LLMError."""
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise LLMError(f"Cannot connect to {url}. Is the server running / internet on?")
    except httpx.TimeoutException:
        raise LLMError("The model took too long to respond (timeout).")
    except httpx.HTTPStatusError as e:
        raise LLMError(f"API returned {e.response.status_code}: {e.response.text[:300]}")
    except ValueError:
        raise LLMError("API returned something that is not valid JSON.")


class LLMProvider:
    """Base class. Each provider fills in chat()."""
    name = "base"

    def __init__(self, model: str):
        self.model = model

    def chat(self, system_prompt: str, user_message: str,
             temperature: float = 0.0, max_tokens: int = 500) -> str:
        raise NotImplementedError


class OllamaProvider(LLMProvider):
    """Local models through Ollama (free, no API key)."""
    name = "ollama"

    def chat(self, system_prompt, user_message, temperature=0.0, max_tokens=500):
        base = os.getenv("OLLAMA_URL", "http://localhost:11434")
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        data = _post(f"{base}/api/chat", payload, headers={})
        try:
            return data["message"]["content"]
        except KeyError:
            raise LLMError(f"Unexpected Ollama response: {str(data)[:300]}")


class AnthropicProvider(LLMProvider):
    """Claude models through the Anthropic Messages API."""
    name = "anthropic"

    def chat(self, system_prompt, user_message, temperature=0.0, max_tokens=500):
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError("ANTHROPIC_API_KEY is not set in .env")
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
        data = _post("https://api.anthropic.com/v1/messages", payload, headers)
        try:
            return data["content"][0]["text"]
        except (KeyError, IndexError):
            raise LLMError(f"Unexpected Anthropic response: {str(data)[:300]}")


class OpenAIProvider(LLMProvider):
    """OpenAI chat models."""
    name = "openai"

    def chat(self, system_prompt, user_message, temperature=0.0, max_tokens=500):
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise LLMError("OPENAI_API_KEY is not set in .env")
        payload = {
            "model": self.model,
            "max_completion_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }
        headers = {"Authorization": f"Bearer {key}"}
        data = _post("https://api.openai.com/v1/chat/completions", payload, headers)
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise LLMError(f"Unexpected OpenAI response: {str(data)[:300]}")


PROVIDERS = {"ollama": OllamaProvider, "anthropic": AnthropicProvider, "openai": OpenAIProvider}


def get_provider(provider: str, model: str) -> LLMProvider:
    """Factory: turn ('ollama', 'llama3.2') into a ready-to-use provider object."""
    if provider not in PROVIDERS:
        raise LLMError(f"Unknown provider '{provider}'. Choose from {list(PROVIDERS)}")
    return PROVIDERS[provider](model)