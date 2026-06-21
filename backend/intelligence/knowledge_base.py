"""
MJ Intelligence: RAG Knowledge Base
- Upload documents (PDF, TXT, MD, CSV, JSON, code files)
- Chunk and index content
- TF-IDF based semantic search (no external dependencies)
- Answer questions from YOUR personal knowledge base
"""

import json
import re
import math
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional
from collections import Counter


KB_DIR = Path(__file__).parent.parent / "knowledge_base"
KB_DIR.mkdir(exist_ok=True)
INDEX_FILE = KB_DIR / "index.json"
CHUNKS_DIR = KB_DIR / "chunks"
CHUNKS_DIR.mkdir(exist_ok=True)


def _load_index() -> dict:
    """Load the knowledge base index."""
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    return {"documents": [], "total_chunks": 0, "last_updated": None}


def _save_index(index: dict):
    """Save the knowledge base index."""
    index["last_updated"] = datetime.now().isoformat()
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list:
    """Split text into overlapping chunks for better retrieval."""
    words = text.split()
    chunks = []
    i = 0

    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunk = " ".join(chunk_words)
        if chunk.strip():
            chunks.append(chunk.strip())
        i += chunk_size - overlap

    return chunks


def _extract_text_from_content(content: str, filename: str) -> str:
    """Extract clean text from various file formats."""
    ext = Path(filename).suffix.lower()

    if ext == ".json":
        try:
            data = json.loads(content)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception:
            return content

    if ext == ".csv":
        lines = content.strip().split("\n")
        return "\n".join(lines)

    if ext in (".md", ".txt"):
        # Remove markdown images but keep text
        text = re.sub(r'!\[.*?\]\(.*?\)', '', content)
        # Remove markdown links but keep text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        return text

    if ext in (".html", ".htm"):
        text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()

    # Code files — keep as is, useful for code Q&A
    return content


def _tokenize(text: str) -> list:
    """Simple tokenization: lowercase, split, remove punctuation."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.split()
    # Remove very short/common stopwords
    stops = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
             'has', 'have', 'had', 'do', 'does', 'did', 'will', 'would',
             'could', 'should', 'may', 'might', 'shall', 'can', 'to', 'of',
             'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
             'through', 'during', 'before', 'after', 'above', 'below',
             'and', 'but', 'or', 'nor', 'not', 'so', 'yet', 'both',
             'each', 'few', 'more', 'most', 'other', 'some', 'such',
             'no', 'only', 'own', 'same', 'than', 'too', 'very',
             'it', 'its', 'this', 'that', 'these', 'those', 'i', 'me',
             'my', 'we', 'our', 'you', 'your', 'he', 'him', 'his',
             'she', 'her', 'they', 'them', 'their', 'what', 'which',
             'who', 'whom', 'when', 'where', 'why', 'how'}
    return [w for w in words if w not in stops and len(w) > 1]


def _compute_tf(tokens: list) -> dict:
    """Compute term frequency."""
    counts = Counter(tokens)
    total = len(tokens)
    if total == 0:
        return {}
    return {word: count / total for word, count in counts.items()}


def _compute_idf(all_docs_tokens: list) -> dict:
    """Compute inverse document frequency across all chunks."""
    n_docs = len(all_docs_tokens)
    if n_docs == 0:
        return {}
    word_doc_count = Counter()
    for tokens in all_docs_tokens:
        unique_words = set(tokens)
        for word in unique_words:
            word_doc_count[word] += 1
    return {word: math.log(n_docs / (1 + count)) for word, count in word_doc_count.items()}


def _tfidf_similarity(query_tokens: list, chunk_tokens: list, idf: dict) -> float:
    """Compute TF-IDF based similarity between query and a chunk."""
    if not query_tokens or not chunk_tokens:
        return 0.0

    query_tf = _compute_tf(query_tokens)
    chunk_tf = _compute_tf(chunk_tokens)

    score = 0.0
    for word in query_tokens:
        if word in chunk_tf:
            word_idf = idf.get(word, 1.0)
            score += query_tf[word] * chunk_tf[word] * word_idf * word_idf

    return score


def ingest_document(filename: str, content: str, metadata: dict = None) -> dict:
    """
    Ingest a document into the knowledge base.
    Returns status dict.
    """
    index = _load_index()

    # Create document hash for dedup
    doc_hash = hashlib.md5(content.encode()).hexdigest()[:12]

    # Check if already ingested
    for doc in index["documents"]:
        if doc.get("hash") == doc_hash:
            return {"status": "exists", "message": f"'{filename}' already in knowledge base"}

    # Extract text
    clean_text = _extract_text_from_content(content, filename)
    if not clean_text or len(clean_text.strip()) < 20:
        return {"status": "error", "message": "File has too little content to index"}

    # Chunk the text
    chunks = _chunk_text(clean_text)

    # Save chunks
    doc_id = f"doc_{doc_hash}"
    chunk_data = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"{doc_id}_c{i}"
        tokens = _tokenize(chunk)
        chunk_info = {
            "id": chunk_id,
            "doc_id": doc_id,
            "text": chunk,
            "tokens": tokens,
            "index": i,
        }
        chunk_data.append(chunk_info)

    # Save all chunks to disk
    chunk_file = CHUNKS_DIR / f"{doc_id}.json"
    chunk_file.write_text(json.dumps(chunk_data, ensure_ascii=False), encoding="utf-8")

    # Update index
    doc_entry = {
        "id": doc_id,
        "filename": filename,
        "hash": doc_hash,
        "chunk_count": len(chunks),
        "char_count": len(clean_text),
        "ingested_at": datetime.now().isoformat(),
        "metadata": metadata or {}
    }
    index["documents"].append(doc_entry)
    index["total_chunks"] = sum(d["chunk_count"] for d in index["documents"])
    _save_index(index)

    return {
        "status": "ok",
        "message": f"Indexed '{filename}': {len(chunks)} chunks, {len(clean_text)} characters",
        "doc_id": doc_id,
        "chunks": len(chunks)
    }


def search_knowledge(query: str, top_k: int = 3) -> list:
    """
    Search the knowledge base using TF-IDF similarity.
    Returns top_k most relevant chunks.
    """
    index = _load_index()
    if not index["documents"]:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    # Load all chunks
    all_chunks = []
    all_tokens_list = []

    for doc in index["documents"]:
        chunk_file = CHUNKS_DIR / f"{doc['id']}.json"
        if chunk_file.exists():
            chunks = json.loads(chunk_file.read_text(encoding="utf-8"))
            for c in chunks:
                all_chunks.append({
                    "text": c["text"],
                    "tokens": c["tokens"],
                    "doc_id": c["doc_id"],
                    "source": doc["filename"]
                })
                all_tokens_list.append(c["tokens"])

    if not all_chunks:
        return []

    # Compute IDF across all chunks
    idf = _compute_idf(all_tokens_list)

    # Score each chunk
    scored = []
    for chunk in all_chunks:
        score = _tfidf_similarity(query_tokens, chunk["tokens"], idf)
        if score > 0:
            scored.append({
                "text": chunk["text"],
                "source": chunk["source"],
                "score": round(score, 4)
            })

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    return scored[:top_k]


def format_kb_context(results: list) -> str:
    """Format knowledge base results for LLM context."""
    if not results:
        return ""

    parts = ["KNOWLEDGE BASE CONTEXT (from user's uploaded documents):"]
    for i, r in enumerate(results, 1):
        parts.append(f"\n[Source: {r['source']} | Relevance: {r['score']}]")
        parts.append(r["text"])

    return "\n".join(parts)


def get_kb_stats() -> dict:
    """Get knowledge base statistics."""
    index = _load_index()
    return {
        "document_count": len(index["documents"]),
        "total_chunks": index["total_chunks"],
        "documents": [
            {
                "filename": d["filename"],
                "chunks": d["chunk_count"],
                "chars": d["char_count"],
                "ingested": d["ingested_at"][:10]
            }
            for d in index["documents"]
        ],
        "last_updated": index.get("last_updated")
    }


def delete_document(doc_id: str) -> dict:
    """Remove a document from the knowledge base."""
    index = _load_index()

    found = None
    for doc in index["documents"]:
        if doc["id"] == doc_id:
            found = doc
            break

    if not found:
        return {"status": "error", "message": "Document not found"}

    index["documents"].remove(found)
    index["total_chunks"] = sum(d["chunk_count"] for d in index["documents"])

    # Remove chunk file
    chunk_file = CHUNKS_DIR / f"{doc_id}.json"
    if chunk_file.exists():
        chunk_file.unlink()

    _save_index(index)
    return {"status": "ok", "message": f"Removed '{found['filename']}' from knowledge base"}


def needs_kb_search(text: str) -> bool:
    """Detect if query should search knowledge base."""
    lower = text.lower().strip()

    kb_triggers = [
        r"(?:from|in|according to)\s+(?:my|the)\s+(?:docs?|documents?|files?|notes?|knowledge|uploads?|kb)",
        r"(?:my|the)\s+(?:docs?|documents?|files?|notes?|knowledge|uploads?)\s+(?:say|mention|contain|have)",
        r"(?:check|search|look|find|dhundho|dekho)\s+(?:in\s+)?(?:my|the)\s+(?:docs?|documents?|files?|notes?|knowledge|kb)",
        r"(?:what|kya).*(?:my|the)\s+(?:docs?|documents?|files?|notes?|knowledge)",
    ]

    for pat in kb_triggers:
        if re.search(pat, lower):
            return True

    return False
