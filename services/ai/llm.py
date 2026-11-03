"""Replaceable LLM provider layer.

To add another provider, write a class with `is_configured()` and `chat()` returning the same
normalized dict, then register it in PROVIDERS. The rest of the app does not change.
"""
import json

import requests


class LLMError(Exception):
    """Safe message for display. Never contains API keys or response bodies."""


class OpenAICompatibleClient:
    """Works with OpenAI and any server exposing /chat/completions with tool calling
    (e.g. OpenRouter, Groq, Together, local Ollama/LM Studio)."""

    def __init__(self, api_key, base_url, model, timeout=30):
        self.api_key = api_key or ""
        self.base_url = (base_url or "").rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_configured(self):
        return bool(self.api_key.strip() and self.base_url and self.model)

    def chat(self, messages, tools=None):
        if not self.is_configured():
            raise LLMError("AI is not configured.")
        payload = {"model": self.model, "messages": messages, "temperature": 0.2}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            resp = requests.post(
                self.base_url + "/chat/completions",
                headers={"Authorization": "Bearer " + self.api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout,
            )
        except requests.Timeout:
            raise LLMError("The AI service took too long to respond. Please try again.")
        except requests.RequestException:
            raise LLMError("Could not reach the AI service. Check your internet connection and AI_BASE_URL.")

        if resp.status_code in (401, 403):
            raise LLMError("The AI service rejected the API key. Check AI_API_KEY.")
        if resp.status_code == 429:
            raise LLMError("The AI service rate limit was reached. Please wait a moment and try again.")
        if resp.status_code >= 500:
            raise LLMError("The AI service had an internal error. Please try again later.")
        if resp.status_code >= 400:
            raise LLMError("The AI service rejected the request (HTTP %d). Check AI_MODEL and AI_BASE_URL."
                           % resp.status_code)

        try:
            message = resp.json()["choices"][0]["message"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise LLMError("The AI service returned an unexpected response.")
        return self._normalize(message)

    @staticmethod
    def _normalize(message):
        calls = []
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function") or {}
            raw = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw) if isinstance(raw, str) else raw
                if not isinstance(args, dict):
                    args = None
            except ValueError:
                args = None
            calls.append({"id": tc.get("id") or "call_%d" % len(calls),
                          "name": fn.get("name") or "", "arguments": args})
        return {"content": message.get("content") or "", "tool_calls": calls}


PROVIDERS = {"openai_compatible": OpenAICompatibleClient}


def get_client(config):
    cls = PROVIDERS.get(config.get("AI_PROVIDER", "openai_compatible"), OpenAICompatibleClient)
    return cls(
        api_key=config.get("AI_API_KEY", ""),
        base_url=config.get("AI_BASE_URL", ""),
        model=config.get("AI_MODEL", ""),
        timeout=config.get("AI_TIMEOUT_SECONDS", 30),
    )
