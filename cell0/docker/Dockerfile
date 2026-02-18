# Cell 0 OS Production Docker Image
# Multi-stage build for optimized production image

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi uvicorn[standard] websockets aiohttp pyyaml pydantic \
    prometheus-client python-json-logger psutil pyjwt cryptography \
    slowapi redis diskcache tenacity rich typer httpx requests

# ============================================================================
# Stage 2: Production
# ============================================================================
FROM python:3.11-slim as production

LABEL maintainer="Vael Zaru'Tahl Xeth (Yige) <yige@cell0.io>"
LABEL org.opencontainers.image.title="Cell 0 OS"
LABEL org.opencontainers.image.description="Sovereign Edge Model Operating System"
LABEL org.opencontainers.image.version="1.2.0"
LABEL org.opencontainers.image.source="https://github.com/cell0-os/cell0"

# Create non-root user
RUN groupadd --gid 1000 cell0 && \
    useradd --uid 1000 --gid cell0 --shell /bin/bash --create-home cell0

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY cell0/ ./cell0/
COPY pyproject.toml ./

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R cell0:cell0 /app

# Set environment variables
ENV CELL0_HOME=/app \
    CELL0_STATE_DIR=/app/data \
    CELL0_ENV=production \
    CELL0_LOG_LEVEL=INFO \
    CELL0_PORT=18800 \
    CELL0_WS_PORT=18801 \
    CELL0_METRICS_PORT=18802 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${CELL0_PORT}/health || exit 1

# Switch to non-root user
USER cell0

# Expose ports
EXPOSE 18800 18801 18802

# Run the daemon
CMD ["python", "-m", "cell0.cell0d"]
