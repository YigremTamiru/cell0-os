# Operations Runbook

This runbook details how to securely host, monitor, and scale your Cell 0 OS instance.

## Managing the Lifecycle (PM2 / SystemD)

While native `npm start` is fine for development, a Sovereign OS must run relentlessly in the background.

We recommend using **PM2** to daemonize the Node.js Gateway.
*(Note: Because the Python engine is natively bridged, PM2 handles the lifecycle of the `cell0d.py` processes automatically by watching the Node parent).*

```bash
# Install PM2 globally
npm install -g pm2

# Start the Gateway and daemonize it
pm2 start dist/gateway/index.js --name "cell0-gateway"

# Ensure Cell 0 boots on server restart
pm2 startup
pm2 save
```

## The Nerve Portal (/api/health)

The Node API Gateway exposes a critical, zero-auth health endpoint at `http://127.0.0.1:18789/api/health`.

This endpoint returns a JSON map of all 51 microservices. If any service (from the Rust Kernel loader to the Swarm Coordinator) crashes, the gateway will return a `503 Degraded` status and auto-attempt a reboot of the specific faulty module.

The **Nerve Portal UI** (`http://127.0.0.1:18790`) visually polls this endpoint to render the green/yellow/red status grid.

## System Backup & Restoration

Because all truth exists in `~/.cell0/`, backing up the OS requires zero database dumps. 

Using the native tools (`src/infra/backup.ts` wrapping `cell0/scripts/backup.py`), you can trigger an automated tarball snapshot of your entire identity, vector memories, and agent workspaces.

## Exposing the Gateway (Tailscale VPN)

**Never expose Port 18789 or 18790 to the public internet without a reverse proxy or VPN.**

We natively integrate with **Tailscale** for secure mesh deployment.
If `GatewayTailscaleConfig` is enabled in your `config.ts`, the OS will bind its web hooks to your Tailnet IP instead of `localhost`. This allows you to securely access the Nerve Portal from your phone while away from home, without opening firewall ports.
