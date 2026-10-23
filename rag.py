import fitz, chromadb, difflib

_client = chromadb.PersistentClient(path="data/chroma")
_col = _client.get_or_create_collection("campus")

def extract_pdf(data: bytes):
    """Returns list of (page_no, text). Scanned pages with no text are skipped
    (add pytesseract OCR here if you need scanned-PDF support)."""
    doc = fitz.open(stream=data, filetype="pdf")
    return [(i + 1, p.get_text()) for i, p in enumerate(doc) if p.get_text().strip()]

def chunk(text, size=800, overlap=120):
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i + size]); i += size - overlap
    return out

def ingest(name, pages):
    _col.delete(where={"source": name})
    ids, docs, metas = [], [], []
    for pno, txt in pages:
        for j, ch in enumerate(chunk(txt)):
            ids.append(f"{name}-{pno}-{j}"); docs.append(ch)
            metas.append({"source": name, "page": pno})
    if docs:
        _col.add(ids=ids, documents=docs, metadatas=metas)
    return len(docs)

def search(query, k=5):
    if _col.count() == 0:
        return []
    r = _col.query(query_texts=[query], n_results=min(k, _col.count()))
    return [{"text": d, "source": m["source"], "page": m["page"]}
            for d, m in zip(r["documents"][0], r["metadatas"][0])]

def diff_text(old, new):
    d = difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=0)
    return [l for l in d if l[:1] in "+-" and not l.startswith(("+++", "---"))]

def count():
    return _col.count()
