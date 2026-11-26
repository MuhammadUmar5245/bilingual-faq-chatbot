# Flask API + NLP engine (build context: project root)
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/models \
    NLTK_DATA=/opt/nltk_data \
    NLP_CACHE_DIR=/opt/nlp_cache \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false
# One BLAS/OpenMP/tokenizer thread per worker: several gunicorn workers share the CPU, and the
# libraries' default "one thread per core" pools oversubscribe it under concurrent load (NF-01).

WORKDIR /app/backend

# CPU-only PyTorch keeps the image small (no CUDA libraries)
RUN pip install --no-cache-dir "torch==2.4.1+cpu" --extra-index-url https://download.pytorch.org/whl/cpu
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLP resources at build time so the container runs without internet access
RUN python -m nltk.downloader -d /opt/nltk_data stopwords \
 && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"
# From here on the model is loaded from the image only - no network access needed at runtime
ENV HF_HUB_OFFLINE=1

COPY backend/ /app/backend/
COPY data/ /app/data/
RUN useradd --create-home appuser && mkdir -p /opt/nlp_cache && chown -R appuser /opt/nlp_cache /app
USER appuser

EXPOSE 5000
HEALTHCHECK --interval=20s --timeout=5s --start-period=90s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:5000/api/health').status==200 else 1)"

# 1) create tables + seed data once, 2) start gunicorn workers (each loads the NLP engine)
# --worker-connections = threads: a busy worker stops accepting connections, so queued requests wait
# in the shared backlog for the next free worker instead of behind a busy one (NF-01, load-test run 5).
# --worker-connections = threads: a busy worker stops accepting connections, so waiting requests stay in
# the shared queue and go to the next free worker instead of queuing behind a busy one (NF-01, run 5).
CMD ["sh", "-c", "WARMUP_NLP=0 python -c 'from app import create_app; create_app()' && exec gunicorn --workers ${GUNICORN_WORKERS:-6} --threads ${GUNICORN_THREADS:-4} --worker-connections ${GUNICORN_THREADS:-4} --timeout 120 --bind 0.0.0.0:5000 wsgi:app"]
