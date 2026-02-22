#!/usr/bin/env bash

# Cell 0 OS — Interactive Installation Wizard
# Triggers the OpenClaw-style visual CLI setup and compiles the interface.

echo "🧬 Initiating Cell 0 OS Neural Setup..."

# 1. Install Dependencies
echo "📦 Verifying package dependencies..."
npm install >/dev/null 2>&1

# 2. Build the Neural Glassbox UI
echo "🌐 Compiling Neural Glassbox Interface..."
npm run build --prefix glassbox >/dev/null 2>&1

# 3. Compile backend TS dynamically for CLI
echo "🧠 Launching Sovereign Configuration Wizard..."
npx tsx src/cli/index.ts onboard

echo ""
echo "✅ Setup Complete."
echo "▶️  Run ./start.sh to boot the Civilization."
