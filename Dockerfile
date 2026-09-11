# Matchday Fate API — any container host (Pxxl, HF Spaces, Cloud Run, Render).
# Processed data + prod model are committed, so the image needs no network
# pulls and serves deterministically. Honors $PORT (PaaS-injected) with a
# local/dev fallback.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api.py .
COPY src/ ./src/
COPY models/ ./models/
COPY data/processed/ ./data/processed/
COPY data/fixtures_2627.csv data/season_record.csv data/simulation_2627.json ./data/

EXPOSE 7860

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-7860}"]
