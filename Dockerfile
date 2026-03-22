FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=5050 \
    APP_HOST=0.0.0.0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/workspace/uploads /app/workspace/jobs /app/workspace/outputs /app/workspace/preview_cache /app/workspace/preview_jobs

EXPOSE 5050

CMD ["sh", "-c", "python -m waitress --listen=0.0.0.0:${PORT} --max-request-body-size=4294967296 wsgi:app"]