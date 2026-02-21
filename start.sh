#!/usr/bin/env bash

# Cell 0 OS — Unified Boot Sequence
# This script terminates dangling orchestrator processes and natively cold-boots the 3-Tier Architecture.

echo "🌊 Terminating dangling Cell 0 instances..."
killall node python3 cell0d.py >/dev/null 2>&1 || true
sleep 2

echo "🧠 Booting Python Intelligence Engine (:18800)..."
nohup python3 cell0/cell0d.py > python_daemon.log 2>&1 &
sleep 2

echo "⚡ Booting Node WebSocket Gateway (:18789)..."
nohup npm run gateway > node_gateway.log 2>&1 &
sleep 2

echo "🌐 Booting Nerve Portal UI (:18790)..."
nohup node dist/cli/index.js portal > portal_ui.log 2>&1 &
sleep 5

echo "✅ Cell 0 OS Sovereign Architecture is ONLINE."
echo "▶️  Access the Neural Glassbox at: http://127.0.0.1:18790"
echo "▶️  To verify integrity, run: node scripts/audit.mjs"
