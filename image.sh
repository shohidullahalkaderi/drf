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


#-# #-# #-#

# production-image
# Stage : Builder
FROM python:3.11-slim AS builder

WORKDIR /usr/src/app

# Install build dependencies & header libraries for compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip

# Copy dependency manifests first for layer caching
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

# Install runtime database shared libraries (not -dev headers) + netcat
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb3 \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-compiled wheels from builder stage and install offline
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl \
    && rm -rf /wheels

# Create UID/GID 10001 non-root user pattern
RUN addgroup --gid 10001 appgroup \
    && adduser --uid 10001 --ingroup appgroup --disabled-password --no-create-home appuser

# Copy application code with proper ownership assigned to appuser
COPY --chown=10001:10001 . .

# Ensure the non-root user owns the working directory
RUN chown -R 10001:10001 /usr/src/app

# Switch to non-root security context
USER 10001

EXPOSE 8000

# NOTE: kubelet does NOT read this HEALTHCHECK instruction — your
# Deployment's startupProbe/readinessProbe/livenessProbe (tcpSocket on
# 8000) are what actually govern pod health in the cluster. Kept only
# for standalone `docker run` debugging; harmless, not a production risk.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD nc -z 0 8000 || exit 1

CMD ["uvicorn", "app.asgi:application", "--host", "0.0.0.0", "--port", "8000"]