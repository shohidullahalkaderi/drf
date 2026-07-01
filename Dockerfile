FROM python:3.11-slim

# 1. Install system dependencies only for MySQL client compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 2. Set the working directory before dealing with project files
WORKDIR /code

# 3. Alternative approach: Installs requirements.txt if found, otherwise falls back to a blank string safely
COPY requirements.txt* .
RUN pip install --no-cache-dir -r requirements.txt* 2>/dev/null || true

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]