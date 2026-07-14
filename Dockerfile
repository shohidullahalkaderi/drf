FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /usr/src/app

# Upgrade pip first to ensure reliable dependency mapping
RUN pip install --no-cache-dir --upgrade pip

# Copy blueprint requirements and lock file (both completely optional)
COPY requirements.txt* requirements.lock* ./

# Single-line guard: Prioritizes lock file, falls back to text file, or skips if neither exists
RUN [ -f requirements.lock ] && pip install --no-cache-dir -r requirements.lock || \
    { [ -f requirements.txt ] && pip install --no-cache-dir -r requirements.txt; } || \
    echo "No python requirements files found, skipping installation."

# Explicitly copy remaining codebase into WORKDIR
COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]