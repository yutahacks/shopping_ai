FROM python:3.12-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./
COPY uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Install Playwright browsers
RUN uv run playwright install chromium
RUN uv run playwright install-deps chromium

# Copy source code
COPY app/ ./app/

ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data
ENV DATABASE_PATH=/data/shopping.db
ENV RULES_PATH=/data/rules.yaml
ENV COOKIES_PATH=/data/cookies.json

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
