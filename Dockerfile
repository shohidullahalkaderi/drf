# Stage : Builder
FROM python:3.11-slim AS builder

WORKDIR /usr/src/app

# Install build dependencies & header libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

# Copy dependency manifests
COPY requirements.txt* requirements.lock* ./

# Compile wheel packages into isolated wheelhouse
RUN mkdir /wheels && \
    if [ -f requirements.lock ]; then \
        pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.lock; \
    elif [ -f requirements.txt ]; then \
        pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt; \
    fi

# Stage : Production Runtime
FROM python:3.11-slim AS runner

WORKDIR /usr/src/app

# Install runtime dependencies including netcat-openbsd for nc healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        default-libmysqlclient-dev \
        netcat-openbsd \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-compiled wheels from builder stage
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Create dedicated non-root user and group
RUN addgroup --system appgroup && adduser --system --group appuser

# Copy codebase with correct ownership
COPY --chown=appuser:appgroup . .

# Switch to non-root execution
USER appuser

EXPOSE 8000

# Universal container healthcheck using netcat
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD nc -z 0 8000 || exit 1

# Production server entrypoint
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app.wsgi:application"]