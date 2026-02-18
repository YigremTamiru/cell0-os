# Dockerfile for signal-cli-rest-api
# Based on the official signal-cli-rest-api image with Cell 0 OS customizations

FROM bbernhard/signal-cli-rest-api:latest

LABEL maintainer="Cell 0 OS"
LABEL description="Signal CLI REST API for Cell 0 OS"

# Install additional dependencies for Cell 0 integration
USER root
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Create Cell 0 data directory
RUN mkdir -p /data/cell0-signal && chmod 755 /data/cell0-signal

# Copy custom entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy health check script
COPY healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /healthcheck.sh

# Expose the API port
EXPOSE 8080

# Switch back to signal-api user
USER signal-api

# Use custom entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]
