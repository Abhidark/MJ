"""
Auto Memory: Detect important facts from user messages and save automatically.
No LLM needed -- uses keyword pattern matching (fast, sync).
Now routes through unified MemoryStore instead of direct file I/O.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from intelligence.memory_store import memory_store


def extract_facts(user_text):
    """Extract important facts from user message using regex."""
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
            if len(name) > 1 and name.lower() not in ["is", "a", "the", "hai", "hoon", "hu", "fine", "good", "ok"]:
                facts.append({"content": "User's name is " + name, "category": "personal"})
                break

    # Age
    m = re.search(r"(?:i am|i'm|meri age|meri umar|main)\s+(\d{1,2})\s*(?:years?|saal|sal|yr)", lower)
    if m:
        facts.append({"content": "User's age is " + m.group(1) + " years", "category": "personal"})

    # Location / city
    m = re.search(r"(?:i live in|i'm from|main .+ se hoon|main .+ me rehta|mera ghar|i stay in|i belong to)\s+(.+?)(?:\.|$|,)", user_text, re.IGNORECASE)
    if m:
        place = m.group(1).strip()
        if len(place) > 1 and len(place) < 30:
            facts.append({"content": "User lives in " + place, "category": "location"})

    # Job / profession
    m = re.search(r"(?:i am a|i'm a|i work as|main .+ hoon|my job is|i do|my profession)\s+(.+?)(?:\.|$|,)", user_text, re.IGNORECASE)
    if m:
        job = m.group(1).strip()
        if len(job) > 2 and len(job) < 40 and job.lower() not in ["fine", "good", "ok", "great", "happy", "sad"]:
            facts.append({"content": "User works as " + job, "category": "work"})

    # Project / working on
    m = re.search(r"(?:i'm working on|i am working on|my project|mera project|i'm building|i am building|main .+ bana raha)\s+(.+?)(?:\.|$|,)", user_text, re.IGNORECASE)
    if m:
        project = m.group(1).strip()
        if len(project) > 2 and len(project) < 50:
            facts.append({"content": "User is working on: " + project, "category": "project"})

    # Likes / favorites
    m = re.search(r"(?:my fav(?:ou?rite)? .+ is|i (?:really )?(?:like|love)|mujhe .+ pasand)\s+(.+?)(?:\.|$|,)", user_text, re.IGNORECASE)
    if m:
        fav = m.group(1).strip()
        if len(fav) > 1 and len(fav) < 30:
            facts.append({"content": "User likes " + fav, "category": "preference"})

    # Language preference
    if re.search(r"(?:speak|talk|baat|reply).+(?:hindi|english|hinglish)", lower):
        if "hindi" in lower:
            facts.append({"content": "User prefers Hindi", "category": "preference"})
        elif "hinglish" in lower:
            facts.append({"content": "User prefers Hinglish", "category": "preference"})
        elif "english" in lower:
            facts.append({"content": "User prefers English", "category": "preference"})

    # Email
    m = re.search(r"(?:my email|mera email|mail me at|email hai)\s+(\S+@\S+\.\S+)", user_text, re.IGNORECASE)
    if m:
        facts.append({"content": "User's email: " + m.group(1), "category": "personal"})

    # Phone
    m = re.search(r"(?:my (?:phone|number|mobile)|mera number)\s+(?:is\s+)?(\+?\d[\d\s-]{8,})", user_text, re.IGNORECASE)
    if m:
        facts.append({"content": "User's phone: " + m.group(1).strip(), "category": "personal"})

    return facts


def auto_remember(user_text):
    """
    Extract facts from user text and save via MemoryStore.
    Returns list of newly saved fact strings (backward compat).
    """
    extracted = extract_facts(user_text)
    if not extracted:
        return []

    # Add source info
    for fd in extracted:
        fd["source"] = "auto"
        fd["confidence"] = 0.7

    added = memory_store.add_batch(extracted)
    return [f.content for f in added]
