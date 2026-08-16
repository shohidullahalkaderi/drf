# local-image
FROM python:3.11-slim

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        default-libmysqlclient-dev \
        pkg-config \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt* requirements.lock* ./

RUN [ -f requirements.lock ] && pip install --no-cache-dir -r requirements.lock || \
    { [ -f requirements.txt ] && pip install --no-cache-dir -r requirements.txt; } || \
    echo "No python requirements files found, skipping installation."

COPY . .

EXPOSE 8000

# Standalone container healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD nc -z 0 8000 || exit 1

CMD ["uvicorn", "app.asgi:application", "--host", "0.0.0.0", "--port", "8000"]