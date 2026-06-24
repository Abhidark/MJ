"""
Google Gemini Cloud API Provider for MJ-Assistant.
Supports Gemini 2.5 Flash, Gemini 2.5 Pro, Gemini 2.0 Flash.

Setup: Add GEMINI_API_KEY=AI... to backend/.env
Get key: https://aistudio.google.com/apikey
"""

import os
import json
import httpx
from pathlib import Path
from typing import AsyncGenerator, Optional

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Model preferences
GEMINI_MODELS = [
    "gemini-2.0-flash",          # DEFAULT — fast, free tier generous
    "gemini-2.5-flash",          # Newer flash with thinking
    "gemini-2.5-pro",            # Most capable
]

GEMINI_TASK_MODELS = {
    "chat": "gemini-2.0-flash",
    "coding": "gemini-2.5-flash",
    "reasoning": "gemini-2.5-pro",
    "creative": "gemini-2.5-flash",
    "analysis": "gemini-2.5-pro",
    "vision": "gemini-2.0-flash",
    "translation": "gemini-2.0-flash",
}

_api_key: Optional[str] = None


def _load_api_key() -> Optional[str]:
    global _api_key
    if _api_key:
        return _api_key

    key = os.environ.get("GEMINI_API_KEY")
    if key:
        _api_key = key
        return key

    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    _api_key = key
                    os.environ["GEMINI_API_KEY"] = key
                    return key
    return None


def is_gemini_available() -> bool:
    return bool(_load_api_key())


def get_gemini_model(task_type: str = "chat") -> str:
    return GEMINI_TASK_MODELS.get(task_type, GEMINI_MODELS[0])


async def check_gemini_connection() -> dict:
    key = _load_api_key()
    if not key:
        return {"available": False, "reason": "No GEMINI_API_KEY set"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{GEMINI_API_BASE}/models?key={key}",
            )
            if resp.status_code == 200:
                models = [m["name"].replace("models/", "")
                          for m in resp.json().get("models", [])
                          if "gemini" in m.get("name", "").lower()]
                return {"available": True, "models": models[:20]}
            elif resp.status_code == 400 or resp.status_code == 403:
                return {"available": False, "reason": "Invalid API key"}
            else:
                return {"available": False, "reason": f"API error: {resp.status_code}"}
    except Exception as e:
        return {"available": False, "reason": str(e)[:100]}


async def stream_gemini_chat(
    messages: list,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> AsyncGenerator[str, None]:
    """Stream chat from Gemini API. Yields tokens."""
    key = _load_api_key()
    if not key:
        yield "[ERROR] Gemini API key not set. Add GEMINI_API_KEY=AI... to backend/.env"
        return

    if not model:
        model = GEMINI_MODELS[0]

    # Convert OpenAI-style messages to Gemini format
    # Gemini uses "contents" with "parts" and roles "user"/"model"
    system_instruction = ""
    contents = []

    for msg in messages:
        if msg["role"] == "system":
            system_instruction += msg["content"] + "\n"
        elif msg["role"] == "assistant":
            contents.append({
                "role": "model",
                "parts": [{"text": msg["content"]}],
            })
        else:  # user
            contents.append({
                "role": "user",
                "parts": [{"text": msg["content"]}],
            })

    # Gemini requires contents to start with "user"
    if contents and contents[0]["role"] != "user":
        contents.insert(0, {"role": "user", "parts": [{"text": "Hello"}]})

    # Merge consecutive same-role messages
    merged = []
    for c in contents:
        if merged and merged[-1]["role"] == c["role"]:
            merged[-1]["parts"].extend(c["parts"])
        else:
            merged.append(c)

    payload = {
        "contents": merged,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }

    if system_instruction.strip():
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction.strip()}]
        }

    url = f"{GEMINI_API_BASE}/models/{model}:streamGenerateContent?key={key}&alt=sse"

    try:
        timeout = httpx.Timeout(connect=5.0, read=60.0, write=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", url, json=payload) as resp:
                if resp.status_code != 200:
                    error_body = ""
                    async for chunk in resp.aiter_text():
                        error_body += chunk
                    try:
                        err = json.loads(error_body)
                        error_msg = err.get("error", {}).get("message", error_body[:200])
                    except Exception:
                        error_msg = error_body[:200]
                    yield f"[ERROR] Gemini API error ({resp.status_code}): {error_msg}"
                    return

                # Gemini SSE format:
                # data: {"candidates":[{"content":{"parts":[{"text":"token"}]}}]}
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                token = part.get("text", "")
                                if token:
                                    yield token
                    except json.JSONDecodeError:
                        continue

    except httpx.ConnectError:
        yield "[ERROR] Cannot reach Gemini API. Check internet connection."
    except httpx.ReadTimeout:
        yield "[ERROR] Gemini API timeout. Try again."
    except Exception as e:
        yield f"[ERROR] Gemini error: {str(e)[:200]}"
