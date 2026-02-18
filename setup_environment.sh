#!/bin/bash
# KULLU Environment Setup Script
# Secure credential management for Vael Zaru'Tahl Xeth
# Location: Kyrenia, North Cyprus
# Date: 2026-02-05

echo "🔐 KULLU Security Environment Setup"
echo "===================================="
echo ""

# Check if 1Password CLI is installed
if command -v op &> /dev/null; then
    echo "✅ 1Password CLI is installed"
    op --version
else
    echo "⚠️  1Password CLI not found"
    echo "Install with: brew install 1password-cli"
    echo "Then enable desktop app integration"
    exit 1
fi

echo ""
echo "📋 Setup Checklist:"
echo ""

# Check for BRAVE_API_KEY
echo "1. Brave API Key"
if [ -n "$BRAVE_API_KEY" ]; then
    echo "   ✅ BRAVE_API_KEY is set in environment"
else
    echo "   ⚠️  BRAVE_API_KEY not set"
    echo "      Add to 1Password and export:"
    echo "      export BRAVE_API_KEY=\$(op read 'op://vault/item/field')"
fi

# Check OpenClaw config
echo ""
echo "2. OpenClaw Configuration"
if grep -q '"profile": "coding"' ~/.openclaw/openclaw.json; then
    echo "   ✅ Tool profile set to 'coding'"
else
    echo "   ⚠️  Tool profile not set correctly"
fi

if grep -q '"sandbox": true' ~/.openclaw/openclaw.json; then
    echo "   ✅ Sub-agent sandbox enabled"
else
    echo "   ⚠️  Sub-agent sandbox not enabled"
fi

if grep -q '"bind": "loopback"' ~/.openclaw/openclaw.json; then
    echo "   ✅ Gateway bound to loopback"
else
    echo "   ⚠️  Gateway not bound to loopback"
fi

echo ""
echo "3. Security Skills"
if [ -d "$HOME/.openclaw/workspace/skills/skill-scanner" ]; then
    echo "   ✅ skill-scanner installed"
else
    echo "   ⚠️  skill-scanner not installed"
fi

if [ -d "$HOME/.openclaw/workspace/skills/1password" ]; then
    echo "   ✅ 1password skill installed"
else
    echo "   ⚠️  1password skill not installed"
fi

echo ""
echo "🛡️  Security Status:"
ls -la ~/.openclaw/workspace/skills/ | grep -E "^d" | wc -l | xargs echo "   Installed skills:"

echo ""
echo "🔧 Recommended Actions:"
echo ""
echo "1. Add Brave API key to 1Password:"
echo "   op item create --category=password --title='Brave API Key' --password='$BRAVE_API_KEY'"
echo ""
echo "2. Set environment variable in ~/.zshrc:"
echo "   export BRAVE_API_KEY=\$(op read 'op://Private/Brave API Key/password')"
echo ""
echo "3. Test skill-scanner on all skills:"
echo "   for skill in ~/.openclay/workspace/skills/*; do"
echo "     python3 ~/.openclaw/workspace/skills/skill-scanner/skill_scanner.py \"\$skill\""
echo "   done"
echo ""
echo "4. Review AGENTS.md for security policy updates"
echo ""
echo "🌊 The fortress is being built."
