"""
OpenAI Cloud API Provider for MJ-Assistant.
Supports GPT-4o, GPT-4o-mini, GPT-4-turbo, o1, o3-mini.

Setup: Add OPENAI_API_KEY=sk-... to backend/.env
Get key: https://platform.openai.com/api-keys
"""

import os
import json
import httpx
from pathlib import Path
from typing import AsyncGenerator, Optional

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Model preferences (cost-effectiveness first)
OPENAI_MODELS = [
    "gpt-4o-mini",        # DEFAULT — cheapest, fast, good quality
    "gpt-4o",             # Best balance of speed + quality
    "gpt-4-turbo",        # Previous gen, still good
    "o3-mini",            # Reasoning model (cheaper)
    "o1",                 # Deep reasoning (expensive)
]

# Task-specific model recommendations
OPENAI_TASK_MODELS = {
    "chat": "gpt-4o-mini",
    "coding": "gpt-4o",
    "reasoning": "o3-mini",
    "creative": "gpt-4o",
    "analysis": "gpt-4o",
    "vision": "gpt-4o",       # GPT-4o supports vision
    "translation": "gpt-4o-mini",
}

_api_key: Optional[str] = None


def _load_api_key() -> Optional[str]:
    global _api_key
    if _api_key:
        return _api_key

    key = os.environ.get("OPENAI_API_KEY")
    if key:
        _api_key = key
        return key

    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    _api_key = key
                    os.environ["OPENAI_API_KEY"] = key
                    return key
    return None


def is_openai_available() -> bool:
    return bool(_load_api_key())


def get_openai_model(task_type: str = "chat") -> str:
    return OPENAI_TASK_MODELS.get(task_type, OPENAI_MODELS[0])


async def check_openai_connection() -> dict:
    key = _load_api_key()
    if not key:
        return {"available": False, "reason": "No OPENAI_API_KEY set"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            if resp.status_code == 200:
                models = [m["id"] for m in resp.json().get("data", [])
                          if any(m["id"].startswith(p) for p in ("gpt-4", "gpt-3.5", "o1", "o3"))]
                return {"available": True, "models": models[:20]}
            elif resp.status_code == 401:
                return {"available": False, "reason": "Invalid API key"}
            else:
                return {"available": False, "reason": f"API error: {resp.status_code}"}
    except Exception as e:
        return {"available": False, "reason": str(e)[:100]}


async def stream_openai_chat(
    messages: list,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> AsyncGenerator[str, None]:
    """Stream chat completion from OpenAI. Yields tokens."""
    key = _load_api_key()
    if not key:
        yield "[ERROR] OpenAI API key not set. Add OPENAI_API_KEY=sk-... to backend/.env"
        return

    if not model:
        model = OPENAI_MODELS[0]

    # Clean messages
    clean_messages = []
    for msg in messages:
        clean_messages.append({"role": msg["role"], "content": msg["content"]})

    payload = {
        "model": model,
        "messages": clean_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    # o1/o3 models don't support temperature or system messages
    if model.startswith("o1") or model.startswith("o3"):
        payload.pop("temperature", None)
        payload["max_completion_tokens"] = payload.pop("max_tokens", 1024)
        # Convert system messages to user messages for reasoning models
        for msg in clean_messages:
            if msg["role"] == "system":
                msg["role"] = "user"
                msg["content"] = "[System Instructions] " + msg["content"]

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    try:
        timeout = httpx.Timeout(connect=5.0, read=60.0, write=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", OPENAI_API_URL, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    error_body = ""
                    async for chunk in resp.aiter_text():
                        error_body += chunk
                    try:
                        err = json.loads(error_body)
                        error_msg = err.get("error", {}).get("message", error_body[:200])
                    except Exception:
                        error_msg = error_body[:200]
                    yield f"[ERROR] OpenAI API error ({resp.status_code}): {error_msg}"
                    return

                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        continue

    except httpx.ConnectError:
        yield "[ERROR] Cannot reach OpenAI API. Check internet connection."
    except httpx.ReadTimeout:
        yield "[ERROR] OpenAI API timeout. Try again."
    except Exception as e:
        yield f"[ERROR] OpenAI error: {str(e)[:200]}"
