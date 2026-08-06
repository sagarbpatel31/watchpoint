FROM python:3.11-slim

WORKDIR /app

# System deps for asyncpg + bcrypt build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

# Render injects PORT env var; default to 8000 for local
ENV PORT=8000
EXPOSE 8000

# Migrations run before the app binds — Alembic owns the schema, not metadata
# create_all. Production: no --reload, bind to $PORT, single worker for free
# tier memory.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
