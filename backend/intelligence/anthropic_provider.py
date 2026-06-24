"""
Anthropic (Claude) Cloud API Provider for MJ-Assistant.
Supports Claude 4 Sonnet, Claude 4 Opus, Claude 3.5 Haiku.

Setup: Add ANTHROPIC_API_KEY=sk-ant-... to backend/.env
Get key: https://console.anthropic.com/settings/keys
"""

import os
import json
import httpx
from pathlib import Path
from typing import AsyncGenerator, Optional

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"

# Model preferences
ANTHROPIC_MODELS = [
    "claude-sonnet-4-20250514",       # DEFAULT — best balance
    "claude-haiku-4-20250414",        # Fast + cheap
    "claude-opus-4-20250514",         # Most capable (expensive)
]

ANTHROPIC_TASK_MODELS = {
    "chat": "claude-sonnet-4-20250514",
    "coding": "claude-sonnet-4-20250514",
    "reasoning": "claude-opus-4-20250514",
    "creative": "claude-sonnet-4-20250514",
    "analysis": "claude-sonnet-4-20250514",
    "vision": "claude-sonnet-4-20250514",
    "translation": "claude-haiku-4-20250414",
}

_api_key: Optional[str] = None


def _load_api_key() -> Optional[str]:
    global _api_key
    if _api_key:
        return _api_key

    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        _api_key = key
        return key

    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    _api_key = key
                    os.environ["ANTHROPIC_API_KEY"] = key
                    return key
    return None


def is_anthropic_available() -> bool:
    return bool(_load_api_key())


def get_anthropic_model(task_type: str = "chat") -> str:
    return ANTHROPIC_TASK_MODELS.get(task_type, ANTHROPIC_MODELS[0])


async def check_anthropic_connection() -> dict:
    key = _load_api_key()
    if not key:
        return {"available": False, "reason": "No ANTHROPIC_API_KEY set"}
    try:
        # Anthropic doesn't have a /models endpoint — test with a tiny request
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": key,
                    "anthropic-version": ANTHROPIC_API_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODELS[0],
                    "max_tokens": 5,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            if resp.status_code == 200:
                return {"available": True, "models": ANTHROPIC_MODELS}
            elif resp.status_code == 401:
                return {"available": False, "reason": "Invalid API key"}
            elif resp.status_code == 529:
                return {"available": True, "models": ANTHROPIC_MODELS, "note": "API overloaded but key valid"}
            else:
                return {"available": False, "reason": f"API error: {resp.status_code}"}
    except Exception as e:
        return {"available": False, "reason": str(e)[:100]}


async def stream_anthropic_chat(
    messages: list,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> AsyncGenerator[str, None]:
    """Stream chat from Anthropic Claude API. Yields tokens."""
    key = _load_api_key()
    if not key:
        yield "[ERROR] Anthropic API key not set. Add ANTHROPIC_API_KEY=sk-ant-... to backend/.env"
        return

    if not model:
        model = ANTHROPIC_MODELS[0]

    # Anthropic uses a different message format:
    # - system message goes in a separate "system" field
    # - only "user" and "assistant" roles in messages array
    system_prompt = ""
    clean_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_prompt += msg["content"] + "\n"
        else:
            clean_messages.append({"role": msg["role"], "content": msg["content"]})

    # Anthropic requires messages to start with "user" role
    if clean_messages and clean_messages[0]["role"] != "user":
        clean_messages.insert(0, {"role": "user", "content": "Hello"})

    # Merge consecutive same-role messages (Anthropic requires alternating roles)
    merged = []
    for msg in clean_messages:
        if merged and merged[-1]["role"] == msg["role"]:
            merged[-1]["content"] += "\n" + msg["content"]
        else:
            merged.append(msg)

    payload = {
        "model": model,
        "messages": merged,
        "max_tokens": max_tokens,
        "stream": True,
    }

    if system_prompt.strip():
        payload["system"] = system_prompt.strip()

    # temperature not supported for some models, but generally fine
    if temperature != 1.0:
        payload["temperature"] = temperature

    headers = {
        "x-api-key": key,
        "anthropic-version": ANTHROPIC_API_VERSION,
        "content-type": "application/json",
    }

    try:
        timeout = httpx.Timeout(connect=5.0, read=60.0, write=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", ANTHROPIC_API_URL, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    error_body = ""
                    async for chunk in resp.aiter_text():
                        error_body += chunk
                    try:
                        err = json.loads(error_body)
                        error_msg = err.get("error", {}).get("message", error_body[:200])
                    except Exception:
                        error_msg = error_body[:200]
                    yield f"[ERROR] Anthropic API error ({resp.status_code}): {error_msg}"
                    return

                # Anthropic SSE format:
                # event: content_block_delta
                # data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"token"}}
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        event_type = data.get("type", "")
                        if event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                token = delta.get("text", "")
                                if token:
                                    yield token
                        elif event_type == "message_stop":
                            break
                        elif event_type == "error":
                            error = data.get("error", {})
                            yield f"[ERROR] {error.get('message', 'Unknown error')}"
                            break
                    except json.JSONDecodeError:
                        continue

    except httpx.ConnectError:
        yield "[ERROR] Cannot reach Anthropic API. Check internet connection."
    except httpx.ReadTimeout:
        yield "[ERROR] Anthropic API timeout. Try again."
    except Exception as e:
        yield f"[ERROR] Anthropic error: {str(e)[:200]}"
