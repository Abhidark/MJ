"""
Auto Memory: Detect important facts from user messages and save automatically.
No LLM needed — uses keyword pattern matching.
"""

import re
from pathlib import Path
import json

CORE_MEMORY_FILE = Path(__file__).parent.parent / "core_memory.json"


def load_core_memory():
    if CORE_MEMORY_FILE.exists():
        return json.loads(CORE_MEMORY_FILE.read_text(encoding="utf-8"))
    return []


def save_core_memory(facts):
    CORE_MEMORY_FILE.write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8")


def is_duplicate(new_fact: str, existing_facts: list) -> bool:
    """Check if fact already exists (fuzzy)."""
    new_lower = new_fact.lower()
    for fact in existing_facts:
        if new_lower in fact.lower() or fact.lower() in new_lower:
            return True
        # Check key words overlap
        new_words = set(new_lower.split())
        fact_words = set(fact.lower().split())
        overlap = len(new_words & fact_words) / max(len(new_words), 1)
        if overlap > 0.7:
            return True
    return False


def extract_facts(user_text: str) -> list:
    """Extract important facts from user message."""
    facts = []
    lower = user_text.lower().strip()

    # Name patterns
    name_patterns = [
        r"(?:my name is|mera naam|i am|i'm|main hoon|call me|mujhe .+ bulao)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
        r"(?:my name is|mera naam|mera naam hai|i am|main)\s+(\w+)",
    ]
    for pat in name_patterns:
        m = re.search(pat, user_text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            if len(name) > 1 and name.lower() not in ["is", "a", "the", "hai", "hoon", "hu"]:
                facts.append(f"User's name is {name}")
                break

    # Age
    m = re.search(r"(?:i am|i'm|meri age|meri umar|main)\s+(\d{1,2})\s*(?:years?|saal|sal|yr)", lower)
    if m:
        facts.append(f"User's age is {m.group(1)} years")

    # Location / city
    m = re.search(r"(?:i live in|i'm from|main .+ se hoon|main .+ me rehta|mera ghar|i stay in|i belong to)\s+(.+?)(?:\.|$|,)", user_text, re.IGNORECASE)
    if m:
        place = m.group(1).strip()
        if len(place) > 1 and len(place) < 30:
            facts.append(f"User lives in {place}")

    # Job / profession
    m = re.search(r"(?:i am a|i'm a|i work as|main .+ hoon|my job is|i do|my profession)\s+(.+?)(?:\.|$|,)", user_text, re.IGNORECASE)
    if m:
        job = m.group(1).strip()
        if len(job) > 2 and len(job) < 40 and job.lower() not in ["fine", "good", "ok", "great", "happy", "sad"]:
            facts.append(f"User works as {job}")

    # Project / working on
    m = re.search(r"(?:i'm working on|i am working on|my project|mera project|i'm building|i am building|main .+ bana raha)\s+(.+?)(?:\.|$|,)", user_text, re.IGNORECASE)
    if m:
        project = m.group(1).strip()
        if len(project) > 2 and len(project) < 50:
            facts.append(f"User is working on: {project}")

    # Likes / favorites
    m = re.search(r"(?:my fav(?:ou?rite)? .+ is|i (?:really )?(?:like|love)|mujhe .+ pasand)\s+(.+?)(?:\.|$|,)", user_text, re.IGNORECASE)
    if m:
        fav = m.group(1).strip()
        if len(fav) > 1 and len(fav) < 30:
            facts.append(f"User likes {fav}")

    # Language preference
    if re.search(r"(?:speak|talk|baat|reply).+(?:hindi|english|hinglish)", lower):
        if "hindi" in lower:
            facts.append("User prefers Hindi")
        elif "hinglish" in lower:
            facts.append("User prefers Hinglish")
        elif "english" in lower:
            facts.append("User prefers English")

    # Email
    m = re.search(r"(?:my email|mera email|mail me at|email hai)\s+(\S+@\S+\.\S+)", user_text, re.IGNORECASE)
    if m:
        facts.append(f"User's email: {m.group(1)}")

    # Phone
    m = re.search(r"(?:my (?:phone|number|mobile)|mera number)\s+(?:is\s+)?(\+?\d[\d\s-]{8,})", user_text, re.IGNORECASE)
    if m:
        facts.append(f"User's phone: {m.group(1).strip()}")

    return facts


def auto_remember(user_text: str) -> list:
    """
    Extract facts from user text and save new ones.
    Returns list of newly saved facts.
    """
    extracted = extract_facts(user_text)
    if not extracted:
        return []

    existing = load_core_memory()
    new_facts = []

    for fact in extracted:
        if not is_duplicate(fact, existing):
            existing.append(fact)
            new_facts.append(fact)

    if new_facts:
        save_core_memory(existing)

    return new_facts
