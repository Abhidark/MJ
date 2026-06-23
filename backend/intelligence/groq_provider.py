"""
Groq Cloud API Provider for MJ.
Fast inference via Groq's free tier — ideal for laptop testing.

Setup: Set GROQ_API_KEY environment variable, or create backend/.env with GROQ_API_KEY=gsk_...
Get free key: https://console.groq.com/keys
"""

import os
import json
import httpx
from pathlib import Path
from typing import AsyncGenerator, Optional

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Groq model preferences (speed first for laptop testing)
GROQ_MODELS = [
    "llama-3.1-8b-instant",          # DEFAULT — fastest, 20K tokens/min free tier
    "llama-3.3-70b-versatile",       # Better quality but slower, 6K tokens/min free
    "gemma2-9b-it",                  # Good multilingual (Hindi)
    "mixtral-8x7b-32768",            # Good reasoning
]

# Load API key from env or .env file
_api_key: Optional[str] = None


def _load_api_key() -> Optional[str]:
    global _api_key
    if _api_key:
        return _api_key

    # Try environment variable first
    key = os.environ.get("GROQ_API_KEY")
    if key:
        _api_key = key
        return key

    # Try .env file in backend directory
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GROQ_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    _api_key = key
                    os.environ["GROQ_API_KEY"] = key
                    return key

    # Try groq_config.json
    config_file = Path(__file__).parent.parent / "groq_config.json"
    if config_file.exists():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            key = data.get("api_key", "")
            if key:
                _api_key = key
                return key
        except Exception:
            pass

    return None


def is_groq_available() -> bool:
    """Check if Groq API key is configured."""
    return bool(_load_api_key())


def get_groq_model() -> str:
    """Return the preferred Groq model."""
    return GROQ_MODELS[0]


async def check_groq_connection() -> dict:
    """Test Groq API connection."""
    key = _load_api_key()
    if not key:
        return {"available": False, "reason": "No GROQ_API_KEY set"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            if resp.status_code == 200:
                models = [m["id"] for m in resp.json().get("data", [])]
                return {"available": True, "models": models}
            elif resp.status_code == 401:
                return {"available": False, "reason": "Invalid API key"}
            else:
                return {"available": False, "reason": f"API error: {resp.status_code}"}
    except Exception as e:
        return {"available": False, "reason": str(e)[:100]}


async def stream_groq_chat(
    messages: list,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> AsyncGenerator[str, None]:
    """
    Stream chat completion from Groq API.
    Yields individual tokens as they arrive.
    Compatible format with Ollama streaming for easy swap.
    """
    key = _load_api_key()
    if not key:
        yield "[ERROR] Groq API key not set. Create backend/.env with GROQ_API_KEY=gsk_..."
        return

    if not model:
        model = GROQ_MODELS[0]

    # Clean messages — Groq uses OpenAI format
    clean_messages = []
    for msg in messages:
        clean_msg = {"role": msg["role"], "content": msg["content"]}
        # Skip images — Groq text models don't support vision
        clean_messages.append(clean_msg)

    payload = {
        "model": model,
        "messages": clean_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", GROQ_API_URL, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    error_body = ""
                    async for chunk in resp.aiter_text():
                        error_body += chunk
                    try:
                        err = json.loads(error_body)
                        error_msg = err.get("error", {}).get("message", error_body[:200])
                    except Exception:
                        error_msg = error_body[:200]
                    yield f"[ERROR] Groq API error ({resp.status_code}): {error_msg}"
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
        yield "[ERROR] Cannot reach Groq API. Check internet connection."
    except httpx.ReadTimeout:
        yield "[ERROR] Groq API timeout. Try again."
    except Exception as e:
        yield f"[ERROR] Groq error: {str(e)[:200]}"
