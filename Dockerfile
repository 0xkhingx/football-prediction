# Matchday Fate API — Hugging Face Spaces (Docker SDK) + any container host.
# Processed data + prod model are committed, so the image needs no network
# pulls and serves deterministically. Expects port 7860 on Spaces.
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

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]
