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

# Verzeichnisse vorbereiten und Rechte setzen
RUN mkdir -p /app/app/data/{instance,uploads,logos} \
    && chown -R appuser:appuser /app/app/data \
    && chown -R appuser:appuser /app/frontend

# Sicherstellen, dass /app/frontend/static/images ein Verzeichnis ist
RUN rm -f /app/frontend/static/images && mkdir -p /app/frontend/static/images \
    && chown -R appuser:appuser /app/frontend/static/images


# entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
