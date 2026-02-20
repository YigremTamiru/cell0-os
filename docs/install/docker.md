# Docker Installation Guide

Containerizing the **Cell 0 OS** ensures that the deep Python Intelligence Engine, the Rust security kernel, and the Node.js gateway perfectly bind without polluting the host environment's dependency tree. 

*Note: While native installation is recommended for active architectural development, Docker is optimal for secure, headless deployment on cloud VPS hardware.*

## Prerequisites
- Docker Engine (v24.0+)
- Docker Compose (v2.20+)

## Containerized Deployment

**1. Clone the Repository**
```bash
git clone https://github.com/YigremTamiru/cell0-os.git
cd cell0-os
```

**2. Build the Docker Image**
Our multistage `Dockerfile` handles compiling the TypeScript, installing the Python dependencies (`requirements.txt`), and preparing the Rust execution environment natively inside the container.
```bash
docker build -t cell0-os:latest .
```

**3. Run the Container**
The container requires mounting a persistent volume bound to `~/.cell0/` to ensure your Agent Library, Memory Vectors, and Cryptographic Identity survive restarts.
```bash
docker run -d \
  --name cell0 \
  -p 18789:18789 \
  -p 18790:18790 \
  -v ~/.cell0:/root/.cell0 \
  cell0-os:latest
```

## Initial Configuration
Because the Node.js API Gateway (`port 18789`) and the Nerve Portal (`port 18790`) are exposed to your local machine, the onboarding flow remains identical to the native setup.

Open your browser to:
**http://127.0.0.1:18790**

The configuration wizard will store your API keys and provider selections natively within the mounted `~/.cell0/cell0.json` volume.

## Checking Container Health
You can drop into the Nerve Portal UI at any time to view the 51 microservices live telemetry. Alternatively, you can view the raw Docker logs to monitor the `cell0d.py` daemon synchronization:

```bash
docker logs -f cell0
```
