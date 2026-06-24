"""
fact_extractor.py -- LLM-based Fact Extraction for MJ-Assistant

Uses Groq or Ollama to intelligently extract facts from conversations.
Falls back to regex if no LLM is available.

Replaces the old regex-only auto_memory.py approach.
"""

import json
import re
import httpx
import asyncio
import os
from pathlib import Path
from typing import Optional
from intelligence.memory_store import memory_store, CATEGORIES

# --- Config ---
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/chat"
EXTRACTION_MODEL_GROQ = "llama-3.1-8b-instant"
EXTRACTION_MODEL_OLLAMA = "qwen3:1.7b"  # Small model for fast extraction

EXTRACT_PROMPT = """You are a fact extractor. Analyze the user message and extract personal facts about the user.

RULES:
- Only extract FACTS about the user (not questions or requests)
- Each fact should be a short, clear statement
- Assign a category from: personal, preference, project, skill, location, relationship, work, device, instruction, general
- Assign confidence (0.0 to 1.0) based on how certain the fact is
- If no facts found, return empty array
- Do NOT extract facts about the AI assistant itself
- Extract facts in the same language the user used

Return ONLY valid JSON array, no other text:
[{"content": "fact text", "category": "category_name", "confidence": 0.9}]

If no facts to extract, return: []"""


def _get_groq_key():
    """Get Groq API key from env or .env file."""
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GROQ_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


async def _extract_via_groq(user_msg, assistant_msg=""):
    """Extract facts using Groq API."""
    key = _get_groq_key()
    if not key:
        return None

    messages = [
        {"role": "system", "content": EXTRACT_PROMPT},
        {"role": "user", "content": f"User message: {user_msg}"},
    ]
    if assistant_msg:
        messages.append({"role": "user", "content": f"Assistant response: {assistant_msg}"})

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": EXTRACTION_MODEL_GROQ,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            return _parse_llm_response(text)
    except Exception:
        return None


async def _extract_via_ollama(user_msg, assistant_msg=""):
    """Extract facts using local Ollama."""
    messages = [
        {"role": "system", "content": EXTRACT_PROMPT},
        {"role": "user", "content": f"User message: {user_msg}"},
    ]
    if assistant_msg:
        messages.append({"role": "user", "content": f"Assistant response: {assistant_msg}"})

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            resp = await client.post(
                OLLAMA_URL,
                json={
                    "model": EXTRACTION_MODEL_OLLAMA,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 500},
                },
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            text = data.get("message", {}).get("content", "").strip()
            return _parse_llm_response(text)
    except Exception:
        return None


def _parse_llm_response(text):
    """Parse LLM JSON response, handling common formatting issues."""
    # Remove think tags if present (qwen3/deepseek)
    text = re.sub(r'<think>[\s\S]*?</think>', '', text).strip()

    # Try to find JSON array in the response
    # Sometimes LLM wraps in markdown code blocks
    json_match = re.search(r'\[[\s\S]*?\]', text)
    if not json_match:
        return []

    try:
        facts = json.loads(json_match.group())
        if not isinstance(facts, list):
            return []

        # Validate and clean
        valid = []
        for f in facts:
            if not isinstance(f, dict):
                continue
            content = f.get("content", "").strip()
            if not content or len(content) < 3:
                continue
            category = f.get("category", "general")
            if category not in CATEGORIES:
                category = "general"
            confidence = f.get("confidence", 0.8)
            if not isinstance(confidence, (int, float)):
                confidence = 0.8
            confidence = min(1.0, max(0.1, confidence))
            valid.append({
                "content": content,
                "category": category,
                "confidence": confidence,
            })
        return valid
    except (json.JSONDecodeError, TypeError):
        return []


def _extract_via_regex(text):
    """Fallback: regex-based extraction (from old auto_memory.py)."""
    facts = []
    patterns = [
        (r"(?:my name is|i am|i'm|mera naam|naam hai)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)", "personal"),
        (r"(?:i live in|i'm from|i am from|main .* se|rehta)\s+(.+?)(?:\.|,|$)", "location"),
        (r"(?:i work (?:at|for|in)|working at|job at|kaam karta)\s+(.+?)(?:\.|,|$)", "work"),
        (r"(?:i (?:like|love|enjoy|prefer)|pasand|favourite|favorite)\s+(.+?)(?:\.|,|$)", "preference"),
        (r"(?:i am learning|i know|i use|main .* use karta)\s+(.+?)(?:\.|,|$)", "skill"),
        (r"(?:my project|working on|building)\s+(.+?)(?:\.|,|$)", "project"),
        (r"(?:i am (\d+) years? old|my age is (\d+)|meri age (\d+))", "personal"),
    ]

    for pattern, category in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            value = match if isinstance(match, str) else next((m for m in match if m), "")
            if value and len(value.strip()) > 2:
                facts.append({
                    "content": value.strip(),
                    "category": category,
                    "confidence": 0.6,
                })

    return facts


async def extract_and_store(user_msg, assistant_msg="", provider="auto"):
    """
    Main entry point: extract facts from a message and store them.
    Returns list of newly stored facts.

    provider: "groq" | "ollama" | "auto" | "regex"
    """
    if not user_msg or len(user_msg.strip()) < 5:
        return []

    # Skip if message is a command or question-only
    msg_lower = user_msg.lower().strip()
    skip_prefixes = ["/", "what ", "how ", "why ", "when ", "where ", "who ",
                     "kya ", "kaise ", "kab ", "kahan ", "kaun ", "?"]
    if any(msg_lower.startswith(p) for p in skip_prefixes) or msg_lower.endswith("?"):
        # Still try if message is long (might contain facts + question)
        if len(user_msg) < 30:
            return []

    facts_data = None

    if provider == "auto":
        # Try Groq first (fastest), then Ollama, then regex
        facts_data = await _extract_via_groq(user_msg, assistant_msg)
        if facts_data is None:
            facts_data = await _extract_via_ollama(user_msg, assistant_msg)
        if facts_data is None:
            facts_data = _extract_via_regex(user_msg)
    elif provider == "groq":
        facts_data = await _extract_via_groq(user_msg, assistant_msg)
    elif provider == "ollama":
        facts_data = await _extract_via_ollama(user_msg, assistant_msg)
    else:
        facts_data = _extract_via_regex(user_msg)

    if not facts_data:
        return []

    # Store via MemoryStore
    for fd in facts_data:
        fd["source"] = "llm" if provider != "regex" else "auto"

    added = memory_store.add_batch(facts_data)
    return added


def extract_sync(text):
    """Synchronous regex-only extraction (for backward compat)."""
    facts_data = _extract_via_regex(text)
    if not facts_data:
        return []
    for fd in facts_data:
        fd["source"] = "auto"
    return memory_store.add_batch(facts_data)
