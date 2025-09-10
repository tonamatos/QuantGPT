# src/quantgpt/llm/client.py
from __future__ import annotations

import os
from typing import Iterable, Optional
from openai import OpenAI, AsyncOpenAI

class LLMClient:
    """
    Thin wrapper around OpenAI Chat Completions that:
      - Reads model & knobs from loaded config
      - Falls back to environment variables where needed
    """

    def __init__(self, cfg: dict):
        self.cfg = cfg or {}
        self.section = (self.cfg.get("openai") or {})
        # Prefer explicit key; otherwise rely on env-only usage
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Create a .env from .env.example and fill it in."
            )

        # Optional base_url for proxy/self-hosted gateways (leave None if not used)
        base_url = self.section.get("base_url") or None

        # Create the SDK client. If api_key is set in env, OpenAI() can omit the parameter.
        self.client = OpenAI(api_key=api_key, base_url=base_url)

        # Async client
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        # Core generation settings (with sensible fallbacks)
        self.model = self.section.get("model") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        self.temperature = float(self.section.get("temperature", 0.2))
        # Chat Completions uses `max_tokens`; map from config's `max_output_tokens` if provided
        self.max_tokens = int(self.section.get("max_output_tokens", 2048)) or None

    def chat(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        context_messages: Optional[Iterable[dict]] = None,
        json_mode: Optional[bool] = None,
    ) -> str:
        """
        Perform a single-turn chat completion and return the assistant's text.
        Set `json_mode=True` to request JSON-formatted output (best-effort).
        """
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        if context_messages:
            msgs.extend(context_messages)
        msgs.append({"role": "user", "content": prompt})

        # Decide whether to ask for JSON
        force_json = (
            self.section.get("json_mode", False) if json_mode is None else json_mode
        )

        # --- The actual API call happens on the next line. ---
        resp = self.client.chat.completions.create(  # <-- ChatGPT API CALL
            model=self.model,
            messages=msgs,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"} if force_json else None,
        )
        # -----------------------------------------------------

        # Extract the text safely
        choice = resp.choices[0]
        content = choice.message.content or ""
        return content
    
    async def achat(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        context_messages: Optional[Iterable[dict]] = None,
        json_mode: Optional[bool] = None,
    ) -> str:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        if context_messages:
            msgs.extend(context_messages)
        msgs.append({"role": "user", "content": prompt})

        force_json = (
            self.section.get("json_mode", False) if json_mode is None else json_mode
        )

        resp = await self.async_client.chat.completions.create(
            model=self.model,
            messages=msgs,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"} if force_json else None,
        )

        choice = resp.choices[0]
        content = choice.message.content or ""
        return content

