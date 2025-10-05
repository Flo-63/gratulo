FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Non-root User
RUN useradd -m appuser

# Requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Code
COPY app ./app
COPY frontend ./frontend

# Verzeichnisse vorbereiten
RUN mkdir -p /app/app/data/instance \
    && mkdir -p /app/app/data/uploads \
    && chown -R appuser:appuser /app/app/data


USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
