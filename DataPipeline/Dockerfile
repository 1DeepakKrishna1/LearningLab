FROM python:3.11-slim

LABEL maintainer="DataPipeline Team"
LABEL description="Production PDF data pipeline with AI enrichment"

# System deps for OCR, PDF, and CV libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ghostscript \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p input output/{raw,extracted,processed,embeddings,knowledge_graph,faq,questions} logs

# Non-root user for security
RUN useradd -m -u 1001 pipeline && chown -R pipeline:pipeline /app
USER pipeline

# Expose Prometheus metrics port
EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

ENTRYPOINT ["python", "scripts/run_pipeline.py"]
CMD ["--help"]
