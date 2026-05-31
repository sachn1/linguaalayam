FROM python:3.11-slim

WORKDIR /app

# System deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files first for layer caching
COPY pyproject.toml poetry.lock ./

# Force CPU-only PyTorch — VPS has no GPU, CUDA build is ~2 GB wasted
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install production deps only (no dev, no huggingface extras)
RUN poetry config virtualenvs.create false \
    && poetry install --without dev,huggingface --no-root --no-interaction

# Pre-bake embedding and reranker models into the image
RUN python - <<'EOF'
from sentence_transformers import SentenceTransformer, CrossEncoder
SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
CrossEncoder("cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
EOF

# Copy application source
COPY linguaalayam/ ./linguaalayam/
COPY README.md ./

# Install the package itself
RUN poetry install --without dev,huggingface --no-interaction

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.cache/huggingface

EXPOSE 8000

CMD ["python", "-c", "from linguaalayam.api.app import main; main()"]
