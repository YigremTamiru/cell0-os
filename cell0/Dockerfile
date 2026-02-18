FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    cargo \
    rustc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Make sure scripts use the installed packages
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV CELL0_ENV=production

# Expose ports
EXPOSE 18800 18801 18802

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:18800/health || exit 1

# Run the daemon
CMD ["python", "cell0d.py"]
