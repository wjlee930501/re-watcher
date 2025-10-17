FROM python:3.11-slim

# Install system dependencies - minimal set for Playwright and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libatk1.0-0 \
    libnss3 \
    libxkbcommon0 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libasound2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    fonts-liberation \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium only (no Firefox/WebKit to save space)
RUN python -m playwright install --with-deps chromium && \
    rm -rf /root/.cache/ms-playwright/webkit* /root/.cache/ms-playwright/firefox*

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /data/snapshots /data/hf_cache

# Set environment variables
ENV REV_SNAPSHOT_DIR=/data/snapshots \
    TRANSFORMERS_CACHE=/data/hf_cache \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Default command (will be overridden by render.yaml)
CMD ["celery", "-A", "apps.scheduler.main", "worker", "--loglevel=INFO", "--concurrency=2"]
