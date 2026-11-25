FROM python:3.11-slim

# System dependencies for PyMuPDF + Tesseract (optional OCR) + curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 tesseract-ocr curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directories (will be replaced by Render's persistent disk at /data)
RUN mkdir -p /data/chroma /data/uploads

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:${PORT:-10000}/_stcore/health || exit 1

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_PATH=/data/campus.db \
    CHROMA_PERSIST_DIRECTORY=/data/chroma \
    DOCUMENT_STORAGE_PATH=/data/uploads

# Render sets $PORT dynamically — Streamlit must bind to it
CMD streamlit run app.py \
    --server.port=${PORT:-10000} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
