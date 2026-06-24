"""
MJ Intelligence: RAG Knowledge Base v2
- Upload documents (PDF, TXT, MD, CSV, JSON, DOCX, code files)
- PDF text extraction (PyPDF2 / pdfplumber)
- Chunk and index content with page-level citations
- TF-IDF based semantic search (no external dependencies)
- Answer questions from YOUR personal knowledge base
"""

import json
import re
import math
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from collections import Counter

logger = logging.getLogger("mj.knowledge_base")


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


def _extract_pdf_metadata(file_path: str) -> Dict:
    """Extract PDF metadata (title, author, pages, creation date)."""
    meta = {"title": "", "author": "", "pages": 0, "created": "", "producer": ""}
    try:
        import PyPDF2
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            meta["pages"] = len(reader.pages)
            info = reader.metadata
            if info:
                meta["title"] = str(info.get("/Title", "") or "")
                meta["author"] = str(info.get("/Author", "") or "")
                meta["producer"] = str(info.get("/Producer", "") or "")
                meta["created"] = str(info.get("/CreationDate", "") or "")
    except Exception:
        pass
    return meta


def _extract_text_from_pdf(file_path: str) -> List[Dict]:
    """Extract text from PDF with page numbers, tables, and metadata.
    Returns list of {page: int, text: str, tables: list} dicts.
    Tries pdfplumber first (best for tables), then PyPDF2, then basic."""
    pages = []

    # Try pdfplumber first (better for tables and complex layouts)
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                # Extract tables
                tables = []
                try:
                    raw_tables = page.extract_tables()
                    for t in (raw_tables or []):
                        if t and len(t) > 1:
                            # Convert table to readable text
                            table_text = "\n".join(
                                " | ".join(str(cell or "") for cell in row)
                                for row in t
                            )
                            tables.append(table_text)
                except Exception:
                    pass

                page_text = text.strip()
                if tables:
                    page_text += "\n\n[TABLE DATA]\n" + "\n---\n".join(tables)

                if page_text.strip():
                    pages.append({"page": i + 1, "text": page_text, "tables": len(tables)})

        if pages:
            total_tables = sum(p.get("tables", 0) for p in pages)
            logger.info(f"PDF extracted via pdfplumber: {len(pages)} pages, {total_tables} tables from {file_path}")
            return pages
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"pdfplumber failed for {file_path}: {e}")

    # Fallback: PyPDF2 (lightweight, pure Python, no table support)
    try:
        import PyPDF2
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append({"page": i + 1, "text": text.strip(), "tables": 0})
        if pages:
            logger.info(f"PDF extracted via PyPDF2: {len(pages)} pages from {file_path}")
            return pages
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"PyPDF2 failed for {file_path}: {e}")

    logger.error(f"No PDF library available. Install: pip install PyPDF2 pdfplumber")
    return []


def _extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX files."""
    try:
        import docx
        doc = docx.Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except ImportError:
        logger.warning("python-docx not installed. Install: pip install python-docx")
        return ""
    except Exception as e:
        logger.warning(f"DOCX extraction failed: {e}")
        return ""


def _extract_text_from_content(content: str, filename: str) -> str:
    """Extract clean text from various file formats."""
    ext = Path(filename).suffix.lower()

    # PDF files need binary reading — content param is the FILE PATH for PDFs
    if ext == ".pdf":
        pages = _extract_text_from_pdf(content)  # content = file path for PDF
        if pages:
            return "\n\n".join([f"[Page {p['page']}]\n{p['text']}" for p in pages])
        return ""

    if ext == ".docx":
        return _extract_text_from_docx(content)  # content = file path for DOCX

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
        text = re.sub(r'!\[.*?\]\(.*?\)', '', content)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        return text

    if ext in (".html", ".htm"):
        text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()

    # Code files — keep as is
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

    # Save chunks with citation info
    doc_id = f"doc_{doc_hash}"
    chunk_data = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"{doc_id}_c{i}"
        tokens = _tokenize(chunk)
        # Extract page number from [Page N] markers if present (PDF sources)
        page_match = re.search(r'\[Page\s+(\d+)\]', chunk)
        page_num = int(page_match.group(1)) if page_match else None
        chunk_info = {
            "id": chunk_id,
            "doc_id": doc_id,
            "text": chunk,
            "tokens": tokens,
            "index": i,
            "page": page_num,
        }
        chunk_data.append(chunk_info)

    # Save all chunks to disk
    chunk_file = CHUNKS_DIR / f"{doc_id}.json"
    chunk_file.write_text(json.dumps(chunk_data, ensure_ascii=False), encoding="utf-8")

    # Extract PDF metadata if applicable
    ext = Path(filename).suffix.lower()
    pdf_meta = {}
    if ext == ".pdf":
        try:
            pdf_meta = _extract_pdf_metadata(content)  # content = file path for PDF
        except Exception:
            pass

    # Update index
    doc_entry = {
        "id": doc_id,
        "filename": filename,
        "hash": doc_hash,
        "chunk_count": len(chunks),
        "char_count": len(clean_text),
        "ingested_at": datetime.now().isoformat(),
        "metadata": {**(metadata or {}), **pdf_meta},
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
                    "source": doc["filename"],
                    "page": c.get("page"),
                    "chunk_index": c.get("index", 0),
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
            result = {
                "text": chunk["text"],
                "source": chunk["source"],
                "score": round(score, 4),
                "chunk_index": chunk.get("chunk_index", 0),
            }
            if chunk.get("page"):
                result["page"] = chunk["page"]
            scored.append(result)

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    return scored[:top_k]


def format_kb_context(results: list) -> str:
    """Format knowledge base results for LLM context with citations."""
    if not results:
        return ""

    parts = ["KNOWLEDGE BASE CONTEXT (from user's uploaded documents):"]
    for i, r in enumerate(results, 1):
        citation = f"Source: {r['source']}"
        if r.get("page"):
            citation += f", Page {r['page']}"
        citation += f" | Relevance: {r['score']}"
        parts.append(f"\n[{citation}]")
        parts.append(r["text"])

    parts.append("\nIMPORTANT: When using information from the knowledge base, cite the source filename and page number if available.")
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


def ingest_file(file_path: str, metadata: dict = None) -> dict:
    """Ingest a file by path. Handles binary files (PDF, DOCX) automatically.
    For text files, reads content. For binary files, passes path to extractors."""
    path = Path(file_path)
    if not path.exists():
        return {"status": "error", "message": f"File not found: {file_path}"}

    ext = path.suffix.lower()
    filename = path.name

    # Binary files — pass file path (not content) to extractor
    if ext in (".pdf", ".docx"):
        content = str(path)  # Pass path as string for binary extractors
    else:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return {"status": "error", "message": f"Failed to read file: {e}"}

    return ingest_document(filename, content, metadata)
