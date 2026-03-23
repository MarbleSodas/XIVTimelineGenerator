"""MiniMax OpenAI-compatible client helpers."""

from __future__ import annotations

import json
import os
from typing import Any

import requests


class MiniMaxError(RuntimeError):
    """Raised when MiniMax cannot fulfill a request."""


class MiniMaxClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "MiniMax-M2.7",
        timeout_seconds: int = 60,
        session: requests.Session | None = None,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.minimax.io/v1").rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.1,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise MiniMaxError("OPENAI_API_KEY is required for MiniMax requests")

        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            raw_content = self._request_content(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                use_json_response_format=(attempt == 0),
            )
            try:
                payload = self._extract_json(raw_content)
            except (json.JSONDecodeError, MiniMaxError) as error:
                last_error = error
                continue
            if not isinstance(payload, dict):
                last_error = MiniMaxError("MiniMax returned a non-object JSON payload")
                continue
            return payload

        raise MiniMaxError(f"Failed to parse MiniMax JSON response: {last_error}")

    def _request_content(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        use_json_response_format: bool,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        if use_json_response_format:
            payload["response_format"] = {"type": "json_object"}

        response = self.session.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout_seconds,
        )
        if not response.ok and use_json_response_format:
            payload.pop("response_format", None)
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise MiniMaxError("MiniMax returned no completion choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_chunks: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                    text_chunks.append(str(item.get("text") or ""))
            return "\n".join(chunk for chunk in text_chunks if chunk)
        raise MiniMaxError("MiniMax returned an unsupported message content shape")

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        candidate = text.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            candidate = "\n".join(lines).strip()

        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise MiniMaxError("MiniMax response did not contain a JSON object")
        return json.loads(candidate[start : end + 1])
