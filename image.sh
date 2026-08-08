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

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# requirements.txt
Django==5.2.16
mysqlclient==2.2.4
djangorestframework==3.15.2
redis==8.0.1

# requirements.lock
# Core Framework & System dependencies
asgiref==3.8.1
sqlparse==0.5.3
Django==5.2.16

# Database & Engine drivers
mysqlclient==2.2.4

# API Engine & Helpers
djangorestframework==3.15.2

# Cache & Redis protocols
redis==8.0.1

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

# NEW: create UID/GID 10001 — switched to the addgroup/adduser pattern.
RUN addgroup --gid 10001 appgroup \
    && adduser --uid 10001 --ingroup appgroup --disabled-password --no-create-home appuser

COPY --chown=10001:10001 . .

USER 10001

EXPOSE 8000

# NOTE: kubelet does NOT read this HEALTHCHECK instruction — your
# Deployment's startupProbe/readinessProbe/livenessProbe (tcpSocket on
# 8000) are what actually govern pod health in the cluster. Kept only
# for standalone `docker run` debugging; harmless, not a production risk.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD nc -z 0 8000 || exit 1

CMD ["uvicorn", "app.asgi:application", "--host", "0.0.0.0", "--port", "8000"]

# requirements.txt
Django==5.2.16
mysqlclient==2.2.4
djangorestframework==3.15.2
redis==8.0.1
uvicorn[standard]==0.34.0

# requirements.lock
# Core Framework & Transitive Dependencies
asgiref==3.8.1
sqlparse==0.5.3
typing-extensions==4.12.2
Django==5.2.16

# Database & Engine Drivers
mysqlclient==2.2.4

# API Engine & Helpers
djangorestframework==3.15.2

# Cache, Redis & Async Protocols
redis==8.0.1

# Production ASGI Server & Async Extensions
h11==0.14.0
httptools==0.6.4
uvloop==0.21.0
watchfiles==1.0.4
websockets==14.1
uvicorn==0.34.0