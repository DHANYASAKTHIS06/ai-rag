"""
CampusCopilot — RAG pipeline
PDF extraction → chunking → ChromaDB indexing → hybrid search → security scan
"""
import os, pymupdf as fitz, chromadb, difflib, re, json
from pathlib import Path

CHROMA_PATH  = os.getenv("CHROMA_PERSIST_DIRECTORY", "data/chroma")
UPLOAD_PATH  = os.getenv("DOCUMENT_STORAGE_PATH",    "data/uploads")
os.makedirs(CHROMA_PATH, exist_ok=True)
os.makedirs(UPLOAD_PATH, exist_ok=True)

_client = None
_col    = None

def _get_collection():
    global _client, _col
    if _col is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
        _col    = _client.get_or_create_collection(
            "campus", metadata={"hnsw:space": "cosine"}
        )
    return _col

# ─── PDF extraction ──────────────────────────────────────────────────────────────
def extract_pdf(data: bytes) -> list[tuple[int, str]]:
    """Return [(page_no, text), …]. Skips blank pages."""
    doc = fitz.open(stream=data, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        txt = page.get_text().strip()
        if txt:
            pages.append((i + 1, txt))
    return pages

def extract_pdf_full(data: bytes, filename: str = "") -> dict:
    """Rich extraction: pages, page_count, has_tables, metadata."""
    doc   = fitz.open(stream=data, filetype="pdf")
    pages = []
    has_tables = False
    for i, page in enumerate(doc):
        txt = page.get_text().strip()
        # basic table heuristic: multiple tab-separated columns
        if "\t" in txt or "  |  " in txt:
            has_tables = True
        if txt:
            pages.append({"page": i + 1, "text": txt})
    return {
        "filename":   filename,
        "page_count": len(doc),
        "has_tables": has_tables,
        "pages":      pages,
        "metadata":   doc.metadata or {},
    }

def save_pdf(data: bytes, filename: str) -> str:
    """Save uploaded PDF bytes to UPLOAD_PATH. Returns absolute file path."""
    safe = re.sub(r"[^\w\-. ]", "_", filename)
    path = os.path.join(UPLOAD_PATH, safe)
    with open(path, "wb") as f:
        f.write(data)
    return path

# ─── chunking ───────────────────────────────────────────────────────────────────
def chunk(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    out, i = [], 0
    while i < len(text):
        out.append(text[i : i + size])
        i += size - overlap
    return out

# ─── indexing ───────────────────────────────────────────────────────────────────
def ingest(name: str, pages: list[tuple[int, str]]) -> int:
    """Index pages from (page_no, text) list. Returns chunk count."""
    col = _get_collection()
    # remove old chunks for this document
    try:
        col.delete(where={"source": name})
    except Exception:
        pass
    ids, docs, metas = [], [], []
    for pno, txt in pages:
        for j, ch in enumerate(chunk(txt)):
            ids.append(f"{name}||{pno}||{j}")
            docs.append(ch)
            metas.append({"source": name, "page": pno})
    if docs:
        col.add(ids=ids, documents=docs, metadatas=metas)
    return len(docs)

# ─── search ─────────────────────────────────────────────────────────────────────
def search(query: str, k: int = 6) -> list[dict]:
    """Return up to k relevant chunks with source, page, text."""
    col = _get_collection()
    if col.count() == 0:
        return []
    n = min(k, col.count())
    r = col.query(query_texts=[query], n_results=n)
    results = []
    for d, m, dist in zip(r["documents"][0], r["metadatas"][0],
                          r.get("distances", [[0]*n])[0]):
        results.append({
            "text":   d,
            "source": m["source"],
            "page":   m["page"],
            "score":  round(1 - dist, 3),   # cosine → similarity
        })
    return results

def search_by_source(source: str, query: str, k: int = 4) -> list[dict]:
    """Search within a specific document only."""
    col = _get_collection()
    if col.count() == 0:
        return []
    n   = min(k, col.count())
    r   = col.query(
        query_texts=[query], n_results=n,
        where={"source": source}
    )
    return [
        {"text": d, "source": m["source"], "page": m["page"]}
        for d, m in zip(r["documents"][0], r["metadatas"][0])
    ]

# ─── document management ─────────────────────────────────────────────────────────
def delete_document(name: str):
    """Remove all indexed chunks for a document."""
    col = _get_collection()
    try:
        col.delete(where={"source": name})
    except Exception:
        pass

def count() -> int:
    return _get_collection().count()

def get_sources() -> list[str]:
    col = _get_collection()
    if col.count() == 0:
        return []
    r = col.get(include=["metadatas"])
    seen = set()
    for m in r["metadatas"]:
        seen.add(m.get("source", ""))
    return sorted(seen - {""})

# ─── diff ────────────────────────────────────────────────────────────────────────
def diff_text(old: str, new: str) -> list[str]:
    d = difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=0)
    return [line for line in d if line[:1] in "+-" and not line.startswith(("+++", "---"))]

# ─── security scan ───────────────────────────────────────────────────────────────
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"you\s+are\s+now\s+a",
    r"disregard\s+(all\s+)?",
    r"forget\s+(all\s+)?(your|previous)",
    r"new\s+instructions?:",
    r"act\s+as\s+(an?\s+)?(ai|assistant|bot|system)",
    r"system\s+prompt",
    r"reveal\s+(your\s+)?(instructions?|prompt|api\s+key)",
    r"print\s+(your\s+)?(instructions?|system|prompt)",
    r"<\s*script\b",
    r"<!--.*?-->",    # hidden HTML comments
    r"\[INST\]",      # Llama instruction injection
    r"<<SYS>>",
]

def security_scan(text: str) -> dict:
    """Scan document text for prompt-injection patterns."""
    issues = []
    lower  = text.lower()
    for pat in _INJECTION_PATTERNS:
        m = re.search(pat, lower)
        if m:
            issues.append(f"Suspicious pattern: '{m.group()}' at position {m.start()}")
    return {"safe": len(issues) == 0, "issues": issues}
