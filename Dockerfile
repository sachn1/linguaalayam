FROM ghcr.io/sachn1/linguaalayam-base:latest

WORKDIR /app

RUN pip install --no-cache-dir poetry

# Copy dependency files first for layer caching
COPY pyproject.toml poetry.lock README.md ./

# Install production deps (torch already in base image from pytorch-cpu source)
RUN poetry config virtualenvs.create false \
    && poetry install --without dev,huggingface --no-root --no-interaction

# Copy application source and Alembic migrations
COPY linguaalayam/ ./linguaalayam/
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Install the package itself
RUN poetry install --without dev,huggingface --no-interaction

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.cache/huggingface

EXPOSE 8000

CMD ["python", "-c", "from linguaalayam.api.app import main; main()"]
