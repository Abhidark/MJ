"""
memory_embeddings.py -- Vector Search for MJ Memory

Uses Ollama's nomic-embed-text for embeddings.
Falls back to keyword search if Ollama unavailable.

Provides semantic recall: "what does the user like" finds
preferences even if the word "like" isn't in the fact.
"""

import math
import httpx
import asyncio
from typing import Optional
from intelligence.memory_store import memory_store, Fact

# --- Config ---
OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"


def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def get_embedding(text):
    """Get embedding vector from Ollama nomic-embed-text."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.post(
                OLLAMA_EMBED_URL,
                json={"model": EMBED_MODEL, "prompt": text},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("embedding")
    except Exception:
        pass
    return None


async def embed_fact(fact):
    """Generate and store embedding for a single fact."""
    if fact.embedding:
        return fact.embedding
    emb = await get_embedding(fact.content)
    if emb:
        memory_store.update(fact.id, embedding=emb)
        fact.embedding = emb
    return emb


async def embed_all_facts():
    """Generate embeddings for all facts that don't have one yet."""
    facts = memory_store.get_all()
    count = 0
    for f in facts:
        if not f.embedding:
            emb = await get_embedding(f.content)
            if emb:
                memory_store.update(f.id, embedding=emb)
                count += 1
                await asyncio.sleep(0.1)  # rate limit
    return count


async def semantic_search(query, top_k=5):
    """
    Search memory using semantic similarity.
    Returns list of (fact, score) tuples.
    """
    query_emb = await get_embedding(query)
    if not query_emb:
        # Fallback to keyword search
        return memory_store.search(query, top_k=top_k)

    facts = memory_store.get_all()
    results = []

    for f in facts:
        if f.embedding:
            score = cosine_similarity(query_emb, f.embedding)
            if score > 0.3:  # threshold
                results.append((f, score))

    results.sort(key=lambda x: x[1], reverse=True)

    # Update access count
    for fact, _ in results[:top_k]:
        fact.access_count += 1

    return results[:top_k]


async def hybrid_search(query, top_k=5):
    """
    Combined keyword + semantic search.
    Merges results from both, deduplicates, re-ranks.
    """
    # Keyword results
    kw_results = memory_store.search(query, top_k=top_k)

    # Semantic results
    sem_results = await semantic_search(query, top_k=top_k)

    # Merge and deduplicate
    seen_ids = set()
    merged = []

    for fact, score in kw_results:
        if fact.id not in seen_ids:
            seen_ids.add(fact.id)
            merged.append((fact, score * 0.4))  # keyword weight

    for fact, score in sem_results:
        if fact.id not in seen_ids:
            seen_ids.add(fact.id)
            merged.append((fact, score * 0.6))  # semantic weight
        else:
            # Boost facts found by both methods
            for i, (f, s) in enumerate(merged):
                if f.id == fact.id:
                    merged[i] = (f, s + score * 0.6)
                    break

    merged.sort(key=lambda x: x[1], reverse=True)
    return merged[:top_k]


async def is_ollama_embed_available():
    """Check if Ollama embedding model is available."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return any(EMBED_MODEL in m.get("name", "") for m in models)
    except Exception:
        pass
    return False
