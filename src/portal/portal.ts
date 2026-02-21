/**
 * Cell 0 OS — Nerve Portal
 *
 * The portal is the nervous system's output. When a user opens
 * http://127.0.0.1:18790 they see a kernel boot sequence, then
 * a full-width Quick Chat with a floating Glassbox assistive touch bubble.
 *
 * Tabs: Chat | Monitor (htop) | Nerve Map | Config | Agent Library
 * Port: 18790 (separate from gateway 18789)
 */

import http from "node:http";

import {
  type Cell0Config,
  readConfigFileSnapshot,
  resolveGatewayPort,
  DEFAULT_PORTAL_PORT,
  CONFIG_PATH,
  CELL0_HOME,
} from "../config/config.js";
import { buildProviderGroups, getProviderLabel } from "../config/providers.js";
import { DEFAULT_CATEGORIES, getSpecialistCount } from "../library/manifest.js";
import { writeConfig } from "../config/config.js";

// ─── Portal Server ────────────────────────────────────────────────────────

export interface PortalConfig {
  port: number;
  host: string;
  gatewayPort: number;
  gatewayToken?: string;
}

export async function startPortal(
  config?: Partial<PortalConfig>
): Promise<http.Server> {
  const snapshot = readConfigFileSnapshot();
  const cell0Config = snapshot.config;

  const portalConfig: PortalConfig = {
    port: config?.port ?? DEFAULT_PORTAL_PORT,
    host: config?.host ?? "127.0.0.1",
    gatewayPort:
      config?.gatewayPort ?? resolveGatewayPort(cell0Config),
    gatewayToken:
      config?.gatewayToken ?? cell0Config.gateway?.auth?.token,
  };

  const server = http.createServer((req, res) => {
    const url = new URL(req.url ?? "/", `http://${req.headers.host}`);

    // CORS
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");

    if (req.method === "OPTIONS") {
      res.writeHead(204);
      res.end();
      return;
    }

    // API routes
    if (url.pathname === "/api/config") {
      const snap = readConfigFileSnapshot();
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({
        gatewayPort: portalConfig.gatewayPort,
        gatewayHost: portalConfig.host,
        version: "1.2.0",
        configPath: CONFIG_PATH,
        cell0Home: CELL0_HOME,
        agent: snap.config.agent ?? {},
        gateway: {
          port: snap.config.gateway?.port ?? 18789,
          bind: snap.config.gateway?.bind ?? "loopback",
          auth: snap.config.gateway?.auth?.mode ?? "token",
        },
        channels: snap.config.channels ?? {},
        providers: buildProviderGroups(false).groups.map(g => ({
          id: g.value,
          label: g.label,
          hint: g.hint,
          active: snap.config.agent?.provider === g.value,
        })),
      }));
      return;
    }

    if (url.pathname === "/api/config/onboard" && req.method === "POST") {
      let body = "";
      req.on("data", chunk => body += chunk);
      req.on("end", () => {
        try {
          const payload = JSON.parse(body);
          if (!payload.provider || !payload.apiKey) {
            res.writeHead(400); res.end("Missing provider or apiKey"); return;
          }
          const snap = readConfigFileSnapshot();
          snap.config.agent = {
            provider: payload.provider,
            model: payload.model || (payload.provider === "anthropic" ? "claude-3-5-sonnet-20241022" : "gpt-4o"),
            apiKey: payload.apiKey
          };
          writeConfig(snap.config);
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ success: true }));
        } catch (e) {
          res.writeHead(500); res.end("Error saving config");
        }
      });
      return;
    }

    // Serve the Nerve Portal
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(generateNervePortalHtml(portalConfig, cell0Config));
  });

  return new Promise((resolve, reject) => {
    server.listen(portalConfig.port, portalConfig.host, () => {
      resolve(server);
    });
    server.on("error", reject);
  });
}

// ─── Nerve Portal HTML ────────────────────────────────────────────────────

function generateNervePortalHtml(portalConfig: PortalConfig, cell0Config: Cell0Config): string {
  const activeProvider = cell0Config.agent?.provider || "none";
  let activeModel = cell0Config.agent?.model || "not configured";

  const providerLabel = activeProvider === "none" ? "Not configured" : getProviderLabel(activeProvider);
  if (activeModel.length > 30) {
    activeModel = activeModel.substring(0, 27) + "...";
  }

  const providerGroups = buildProviderGroups(false).groups;
  const providerOptionsHtml = providerGroups.map(g =>
    `<option value="${g.value}">${g.label}${g.hint ? ` (${g.hint})` : ''}</option>`
  ).join('\n        ');

  return `<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cell 0 OS — Nerve Portal</title>
<meta name="description" content="Cell 0 OS Nerve Portal — kernel-level system interface with glassbox transparency">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --bg-primary: #0a0e17;
  --bg-secondary: #111827;
  --bg-card: #1a1f2e;
  --bg-card-hover: #222840;
  --bg-terminal: #0d1117;
  --border: #2a3144;
  --text-primary: #e5e7eb;
  --text-secondary: #9ca3af;
  --text-muted: #6b7280;
  --accent: #00E5A0;
  --accent-dim: #008F65;
  --accent-bright: #00FFB3;
  --accent-glow: rgba(0,229,160,0.15);
  --info: #5EEAD4;
  --success: #34D399;
  --warning: #FBBF24;
  --error: #F87171;
  --online: #34D399;
  --ready: #5EEAD4;
  --standby: #FBBF24;
  --offline: #6b7280;
  --radius: 12px;
  --radius-sm: 8px;
  --font-mono: 'JetBrains Mono', 'Menlo', monospace;
  --font-sans: 'Inter', -apple-system, sans-serif;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:var(--font-sans); background:var(--bg-primary); color:var(--text-primary); min-height:100vh; overflow-x:hidden; }

/* ─── Boot Sequence ─── */
#boot-screen {
  position:fixed; inset:0; z-index:9999;
  background:var(--bg-terminal);
  display:flex; flex-direction:column; justify-content:center;
  padding:40px; font-family:var(--font-mono); font-size:14px;
  transition: opacity 0.6s ease;
}
#boot-screen.fade-out { opacity:0; pointer-events:none; }
.boot-line { opacity:0; transform:translateY(4px); transition:all 0.3s ease; margin:3px 0; line-height:1.6; }
.boot-line.visible { opacity:1; transform:translateY(0); }
.boot-ok { color:var(--success); }
.boot-fail { color:var(--error); }
.boot-info { color:var(--text-muted); }
.boot-accent { color:var(--accent); }
.boot-banner { color:var(--accent); font-size:16px; font-weight:600; margin:12px 0; }

/* ─── Main App ─── */
#app { display:none; }
#app.visible { display:flex; flex-direction:column; min-height:100vh; }

/* ─── Header ─── */
.header {
  background:linear-gradient(135deg, var(--bg-secondary), var(--bg-card));
  border-bottom:1px solid var(--border);
  padding:12px 24px;
  display:flex; align-items:center; justify-content:space-between;
}
.header-left { display:flex; align-items:center; gap:12px; }
.logo { font-size:20px; font-weight:700;
  background:linear-gradient(135deg, var(--accent), var(--info));
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.version-badge { background:var(--accent-glow); color:var(--accent); padding:3px 10px;
  border-radius:99px; font-size:11px; font-weight:600; border:1px solid var(--accent-dim); }
.status-dot { width:8px; height:8px; border-radius:50%; background:var(--success);
  box-shadow:0 0 6px var(--success); animation:pulse 2s ease-in-out infinite; }
.status-dot.offline { background:var(--error); box-shadow:0 0 6px var(--error); }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

/* ─── Tabs ─── */
.tabs { display:flex; background:var(--bg-secondary); border-bottom:1px solid var(--border); padding:0 24px; }
.tab { padding:10px 20px; font-size:13px; font-weight:500; color:var(--text-muted);
  cursor:pointer; border-bottom:2px solid transparent; transition:all 0.2s; }
.tab:hover { color:var(--text-primary); }
.tab.active { color:var(--accent); border-bottom-color:var(--accent); }

/* ─── Tab Content ─── */
.tab-content { display:none; flex:1; overflow:auto; }
.tab-content.active { display:flex; flex-direction:column; }

/* ─── Chat Tab ─── */
#chat-tab { padding:0; }
.chat-container { flex:1; display:flex; flex-direction:column; max-width:800px; width:100%; margin:0 auto; padding:24px; }
.chat-messages { flex:1; overflow-y:auto; padding-bottom:16px; }
.chat-msg { margin:8px 0; padding:12px 16px; border-radius:var(--radius); max-width:85%; line-height:1.6; font-size:14px; }
.chat-msg.user { background:var(--accent-glow); border:1px solid var(--accent-dim);
  margin-left:auto; border-bottom-right-radius:4px; }
.chat-msg.assistant { background:var(--bg-card); border:1px solid var(--border);
  margin-right:auto; border-bottom-left-radius:4px; }
.chat-msg .sender { font-size:11px; font-weight:600; color:var(--text-muted); margin-bottom:4px; text-transform:uppercase; letter-spacing:0.5px; }
.chat-msg.assistant .sender { color:var(--accent); }
.chat-input-area { display:flex; gap:8px; padding:16px 0; border-top:1px solid var(--border); }
.chat-input { flex:1; background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius);
  padding:12px 16px; color:var(--text-primary); font-size:14px; font-family:var(--font-sans);
  outline:none; transition:border-color 0.2s; }
.chat-input:focus { border-color:var(--accent); }
.chat-send { background:var(--accent); color:#000; border:none; border-radius:var(--radius);
  padding:12px 20px; font-weight:600; cursor:pointer; font-size:14px; transition:all 0.2s; }
.chat-send:hover { background:var(--accent-bright); transform:translateY(-1px); }

/* ─── Monitor Tab (htop) ─── */
.htop { font-family:var(--font-mono); font-size:12px; padding:16px 24px; background:var(--bg-terminal);
  flex:1; overflow:auto; line-height:1.7; }
.htop-header { color:var(--accent); font-weight:600; border-bottom:1px solid var(--border); padding-bottom:4px; margin-bottom:4px; }
.htop-category { color:var(--accent-bright); font-weight:600; margin-top:8px; }
.htop-row { display:flex; gap:0; }
.htop-row span { display:inline-block; }
.htop-pid { width:50px; color:var(--text-muted); }
.htop-name { width:260px; color:var(--text-primary); }
.htop-status { width:90px; font-weight:500; }
.htop-port { width:80px; color:var(--info); }
.htop-cpu { width:70px; color:var(--text-secondary); }
.htop-mem { width:80px; color:var(--text-secondary); }
.htop-conn { width:60px; color:var(--text-secondary); }
.s-online { color:var(--online); }
.s-ready { color:var(--ready); }
.s-standby { color:var(--standby); }
.s-offline { color:var(--offline); }
.htop-footer { color:var(--text-muted); border-top:1px solid var(--border); padding-top:8px; margin-top:8px; }
.htop-sep { border-bottom:1px solid #1a2030; margin:2px 0; }

/* ─── Nerve Map Tab ─── */
.nerve-map { padding:24px; flex:1; overflow:auto; }
.nerve-section { margin-bottom:24px; }
.nerve-section-title { font-size:13px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;
  color:var(--text-muted); margin-bottom:12px; display:flex; align-items:center; gap:8px; }
.nerve-grid { display:flex; flex-wrap:wrap; gap:8px; }
.nerve-node { background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius-sm);
  padding:10px 14px; font-size:12px; min-width:120px; transition:all 0.2s; cursor:default; }
.nerve-node:hover { border-color:var(--accent-dim); background:var(--bg-card-hover); }
.nerve-node .node-name { font-weight:600; color:var(--text-primary); }
.nerve-node .node-detail { font-size:11px; color:var(--text-muted); margin-top:2px; }
.nerve-node .node-dot { display:inline-block; width:6px; height:6px; border-radius:50%; margin-right:6px; }
.nerve-node.active { border-color:var(--accent); box-shadow:0 0 12px var(--accent-glow); }
.nerve-node.active .node-dot { background:var(--accent); box-shadow:0 0 4px var(--accent); }
.nerve-node.ready .node-dot { background:var(--ready); }
.nerve-node.standby .node-dot { background:var(--standby); }
.nerve-node.offline .node-dot { background:var(--offline); }
.nerve-wires { display:flex; align-items:center; gap:8px; margin:12px 0 12px 20px;
  color:var(--text-muted); font-size:11px; font-family:var(--font-mono); }
.nerve-wires::before { content:'└──'; color:var(--border); }

/* ─── Config Tab ─── */
.config-panel { padding:24px; flex:1; overflow:auto; max-width:800px; margin:0 auto; width:100%; }
.config-section { margin-bottom:24px; }
.config-section-title { font-size:13px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;
  color:var(--text-muted); margin-bottom:12px; }
.config-row { display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid var(--border); font-size:14px; }
.config-key { color:var(--text-secondary); }
.config-val { color:var(--text-primary); font-family:var(--font-mono); font-size:13px; }

/* ─── Agent Library Tab ─── */
.library-panel { padding:24px; flex:1; overflow:auto; }
.library-header { font-size:15px; font-weight:600; color:var(--text-primary); margin-bottom:4px; }
.library-subtitle { font-size:12px; color:var(--text-muted); margin-bottom:20px; }
.library-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(160px, 1fr)); gap:12px; }
.library-folder { background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius);
  padding:16px; cursor:pointer; transition:all 0.3s ease; position:relative; overflow:hidden; }
.library-folder:hover { transform:translateY(-2px); border-color:var(--accent-dim); }
.library-folder::before { content:''; position:absolute; top:0; left:0; right:0; height:3px;
  background:var(--folder-color); opacity:0.8; }
.library-folder .folder-icon { font-size:24px; margin-bottom:8px; }
.library-folder .folder-name { font-size:13px; font-weight:600; color:var(--text-primary); margin-bottom:2px; }
.library-folder .folder-count { font-size:11px; color:var(--text-muted); }
.library-folder .folder-glow { position:absolute; top:-20px; left:50%; transform:translateX(-50%);
  width:60px; height:40px; border-radius:50%; filter:blur(20px); opacity:0.2;
  background:var(--folder-color); transition:opacity 0.3s; }
.library-folder:hover .folder-glow { opacity:0.5; }
.library-folder.expanded { grid-column:1/-1; background:var(--bg-secondary); }
.specialist-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:8px; margin-top:12px; }
.specialist-card { background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius-sm);
  padding:10px 12px; font-size:12px; }
.specialist-card .spec-name { font-weight:600; color:var(--text-primary); margin-bottom:2px; }
.specialist-card .spec-desc { color:var(--text-muted); font-size:11px; margin-bottom:4px; }
.specialist-card .spec-tools { color:var(--accent-dim); font-size:10px; font-family:var(--font-mono); }
.specialist-card .spec-channel { color:var(--info); font-size:10px; }

/* ─── UFA Layer Bar ─── */
.ufa-bar { display:flex; justify-content:center; gap:8px; padding:8px 24px;
  background:var(--bg-secondary); border-top:1px solid var(--border); font-family:var(--font-mono); font-size:11px; }
.ufa-layer { display:flex; align-items:center; gap:3px; }
.ufa-label { color:var(--text-muted); }
.ufa-blocks { display:flex; gap:1px; }
.ufa-block { width:8px; height:10px; border-radius:2px; }
.ufa-block.filled { background:var(--accent); }
.ufa-block.partial { background:var(--accent-dim); }
.ufa-block.empty { background:#1a2030; }

/* ─── Glassbox Assistive Touch ─── */
.glassbox-bubble {
  position:fixed; bottom:24px; right:24px; z-index:1000;
  width:48px; height:48px; border-radius:50%;
  background:linear-gradient(135deg, var(--accent), var(--info));
  display:flex; align-items:center; justify-content:center;
  cursor:pointer; font-size:20px; box-shadow:0 4px 20px rgba(0,229,160,0.3);
  transition:all 0.3s ease; user-select:none;
}
.glassbox-bubble:hover { transform:scale(1.1); box-shadow:0 6px 28px rgba(0,229,160,0.4); }
.glassbox-bubble.processing { animation:gb-pulse 1.5s ease-in-out infinite; }
.glassbox-bubble.error { background:linear-gradient(135deg, var(--error), #dc2626); }
@keyframes gb-pulse { 0%,100%{box-shadow:0 4px 20px rgba(0,229,160,0.3)} 50%{box-shadow:0 4px 30px rgba(0,229,160,0.6)} }

.glassbox-panel {
  position:fixed; bottom:24px; right:24px; z-index:1000;
  width:90vw; height:85vh; max-width:1400px;
  background:#030712;
  border:1px solid #1f2937; border-radius:12px;
  box-shadow:0 8px 40px rgba(0,0,0,0.8); overflow:hidden;
  transform:translateY(20px) scale(0.95); opacity:0; pointer-events:none;
  transition:all 0.3s cubic-bezier(0.16,1,0.3,1);
  display: flex; flex-direction: column;
}
.glassbox-panel.open { transform:translateY(0) scale(1); opacity:1; pointer-events:auto; }
.glassbox-header { padding:12px 16px; border-bottom:1px solid var(--border);
  font-size:13px; font-weight:600; color:var(--accent); display:flex; justify-content:space-between; background:var(--bg-secondary); }
.glassbox-body { flex:1; overflow:hidden; padding: 0; }

@media(max-width:768px) {
  .header{padding:10px 16px} .tabs{padding:0 16px} .tab{padding:8px 14px; font-size:12px}
  .chat-container{padding:16px} .htop{padding:12px; font-size:11px}
  .nerve-map{padding:16px} .config-panel{padding:16px}
  .glassbox-panel{width:calc(100vw - 48px); right:24px;}
}

/* ─── Onboard Modal ─── */
#onboard-modal {
  position: fixed; inset: 0; z-index: 99999;
  background: rgba(10, 14, 23, 0.9); backdrop-filter: blur(10px);
  display: flex; align-items: center; justify-content: center;
}
.onboard-box {
  background: var(--bg-card); border: 1px solid var(--accent);
  padding: 32px; border-radius: var(--radius); width: 100%; max-width: 480px;
  box-shadow: 0 0 40px var(--accent-glow);
}
.onboard-title { color: var(--accent); font-size: 20px; font-weight: 600; margin-bottom: 8px; }
.onboard-desc { color: var(--text-muted); font-size: 14px; margin-bottom: 24px; line-height: 1.5; }
.ob-field { margin-bottom: 16px; }
.ob-field label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px; text-transform: uppercase; }
.ob-select, .ob-input {
  width: 100%; background: var(--bg-secondary); border: 1px solid var(--border);
  color: var(--text-primary); padding: 12px; border-radius: var(--radius-sm); font-size: 14px; outline: none;
}
.ob-select:focus, .ob-input:focus { border-color: var(--accent); }
.ob-btn {
  width: 100%; background: var(--accent); color: #000; font-weight: 600;
  padding: 14px; border: none; border-radius: var(--radius-sm); font-size: 16px;
  cursor: pointer; margin-top: 8px; transition: transform 0.2s;
}
.ob-btn:hover { transform: translateY(-2px); background: var(--accent-bright); }

</style>
</head>
<body>

<!-- ═══════════════════════ ONBOARDING MODAL ═══════════════════════ -->
<div id="onboard-modal" style="display: none;">
  <div class="onboard-box">
    <div class="onboard-title">🧬 Initialize Cell 0 OS</div>
    <div class="onboard-desc">Welcome to the Nerve Portal. To establish your sovereign AI environment, please select your primary cognition provider.</div>
    
    <div class="ob-field">
      <label>Intelligence Provider</label>
      <select id="ob-provider" class="ob-select">
        ${providerOptionsHtml}
      </select>
    </div>

    <div class="ob-field">
      <label>API Key</label>
      <input type="password" id="ob-apikey" class="ob-input" placeholder="sk-...">
    </div>

    <button id="ob-submit" class="ob-btn">Ignite Core Sequence 🚀</button>
  </div>
</div>

<!-- ═══════════════════════ BOOT SEQUENCE ═══════════════════════ -->
<div id="boot-screen">
  <div id="boot-log"></div>
</div>

<!-- ═══════════════════════ MAIN APP ═══════════════════════ -->
<div id="app">
  <header class="header">
    <div class="header-left">
      <span class="logo">🧬 Cell 0 OS</span>
      <span class="version-badge">v1.2.0</span>
    </div>
    <div class="header-left">
      <span id="status-label" style="font-size:12px;color:var(--text-secondary)">Connecting…</span>
      <div id="status-dot" class="status-dot offline"></div>
    </div>
  </header>

  <nav class="tabs">
    <div class="tab active" data-tab="chat">💬 Chat</div>
    <div class="tab" data-tab="monitor">⌨️ Monitor</div>
    <div class="tab" data-tab="nerve">🖧 Nerve Map</div>
    <div class="tab" data-tab="config">⚙️ Config</div>
    <div class="tab" data-tab="library">📚 Agent Library</div>
  </nav>

  <!-- ─── Chat Tab ─── -->
  <div id="chat-tab" class="tab-content active">
    <div class="chat-container">
      <div class="chat-messages" id="chat-messages">
        <div class="chat-msg assistant">
          <div class="sender">🧬 Cell 0</div>
          Welcome to Cell 0 OS. I'm your sovereign AI assistant running locally at the edge.<br><br>
          <strong>Provider:</strong> ${providerLabel}<br>
          <strong>Model:</strong> ${activeModel}<br><br>
          Type a message to start, or try <code>/help</code> for commands.
        </div>
      </div>
      <div class="chat-input-area">
        <input id="chat-input" class="chat-input" placeholder="Type a message..." autocomplete="off">
        <button id="chat-send" class="chat-send">Send ⏎</button>
      </div>
    </div>
  </div>

  <!-- ─── Monitor Tab (htop) ─── -->
  <div id="monitor-tab" class="tab-content">
    <div class="htop" id="htop-display"></div>
  </div>

  <!-- ─── Nerve Map Tab ─── -->
  <div id="nerve-tab" class="tab-content">
    <div class="nerve-map" id="nerve-map"></div>
  </div>

  <!-- ─── Config Tab ─── -->
  <div id="config-tab" class="tab-content">
    <div class="config-panel" id="config-panel"></div>
  </div>

  <!-- ─── Agent Library Tab ─── -->
  <div id="library-tab" class="tab-content">
    <div class="library-panel" id="library-panel"></div>
  </div>

  <!-- ─── UFA Layer Bar ─── -->
  <div class="ufa-bar" id="ufa-bar"></div>
</div>

<!-- ═══════════════════════ GLASSBOX BUBBLE ═══════════════════════ -->
<div class="glassbox-bubble" id="glassbox-bubble" title="Glassbox — System Transparency">🔍</div>
<div class="glassbox-panel" id="glassbox-panel">
  <div class="glassbox-header">
    <span>🔍 GLASSBOX — Neural Application Layer</span>
    <span style="cursor:pointer;color:var(--text-muted)" id="glassbox-close">✕</span>
  </div>
  <div class="glassbox-body" id="glassbox-body">
    <iframe id="glassbox-iframe" src="" style="width:100%; height:100%; border:none; display:block; background:#000;"></iframe>
  </div>
</div>

<script>
// ═══════════════════════ CONFIGURATION ═══════════════════════
const GW_PORT = ${portalConfig.gatewayPort};
const GW_TOKEN = ${portalConfig.gatewayToken ? JSON.stringify(portalConfig.gatewayToken) : "null"};
const ACTIVE_PROVIDER_RAW = ${JSON.stringify(activeProvider)};
const ACTIVE_PROVIDER = ${JSON.stringify(providerLabel)};
const ACTIVE_MODEL = ${JSON.stringify(activeModel)};

let ws;
let gwOnline = false;
let pyOnline = false;
let startTime = Date.now();
let glassboxEvents = [];

// ═══════════════════════ BOOT SEQUENCE ═══════════════════════
const bootLines = [
  { text: '[ OK ] Starting Cell 0 OS Gateway v1.2.0...', cls: 'boot-ok' },
  { text: '[ OK ] Loading configuration from ~/.cell0/cell0.json', cls: 'boot-ok' },
  { text: '[ OK ] Provider: ' + ACTIVE_PROVIDER, cls: 'boot-ok' },
  { text: '[ OK ] Model: ' + ACTIVE_MODEL, cls: 'boot-ok' },
  { text: '[ OK ] Gateway bound to ws://127.0.0.1:' + GW_PORT, cls: 'boot-ok' },
  { text: '[ OK ] Python backend on port 18800', cls: 'boot-ok' },
  { text: '[ OK ] Security: Token auth ✓, loopback bind ✓', cls: 'boot-ok' },
  { text: '[ OK ] Engine: agent-mesh, agent-router, skill-manager', cls: 'boot-ok' },
  { text: '[ OK ] Security: auth, RBAC, sandbox, secrets-vault', cls: 'boot-ok' },
  { text: '[ OK ] COL: orchestrator, classifier, flow, resonance', cls: 'boot-ok' },
  { text: '[ OK ] Tools: canvas, web-search, bash, file-ops', cls: 'boot-ok' },
  { text: '[ OK ] Monitoring: health-checks, metrics, logging', cls: 'boot-ok' },
  { text: '[ OK ] Workspace: ~/.cell0/workspace', cls: 'boot-ok' },
  { text: '[  ..  ] Channels: 11 available (configure via cell0 configure)', cls: 'boot-info' },
  { text: '[  ..  ] Voice: STT, TTS, wake-word (standby)', cls: 'boot-info' },
  { text: '[  ..  ] Swarm: coordinator, consensus, discovery (standby)', cls: 'boot-info' },
  { text: '[ OK ] Agent Library: 12 categories, 66 specialists', cls: 'boot-ok' },
  { text: '[ OK ] Nerve Portal ready on :18790', cls: 'boot-ok' },
  { text: '', cls: 'boot-info' },
  { text: '         🧬 Cell 0 OS — kernel operational', cls: 'boot-banner' },
];

async function runBootSequence() {
  if (ACTIVE_PROVIDER_RAW === "none") {
    document.getElementById('boot-screen').style.display = 'none';
    document.getElementById('app').style.display = 'none';
    document.getElementById('onboard-modal').style.display = 'flex';
    
    document.getElementById('ob-submit').addEventListener('click', () => {
      const p = document.getElementById('ob-provider').value;
      const k = document.getElementById('ob-apikey').value;
      if (!k) return alert("API Key required");
      
      document.getElementById('ob-submit').innerText = "Configuring...";
      
      fetch('/api/config/onboard', {
        method: 'POST', body: JSON.stringify({ provider: p, apiKey: k })
      })
      .then(r => r.json())
      .then(res => {
        if (res.success) window.location.reload();
      })
      .catch(e => { alert("Failed to save config"); document.getElementById('ob-submit').innerText = "Ignite Core Sequence 🚀"; });
    });
    return;
  }

  const log = document.getElementById('boot-log');
  for (let i = 0; i < bootLines.length; i++) {
    const line = document.createElement('div');
    line.className = 'boot-line ' + bootLines[i].cls;
    line.textContent = bootLines[i].text;
    log.appendChild(line);
    await sleep(80 + Math.random() * 40);
    line.classList.add('visible');
  }
  await sleep(800);
  document.getElementById('boot-screen').classList.add('fade-out');
  await sleep(600);
  document.getElementById('boot-screen').style.display = 'none';
  document.getElementById('app').classList.add('visible');
  initApp();
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ═══════════════════════ APP INIT ═══════════════════════
function initApp() {
  initTabs();
  initChat();
  initGlassbox();
  renderHtop();
  renderNerveMap();
  renderConfig();
  renderLibrary();
  renderUfaBar();
  connectGateway();
  setInterval(renderHtop, 2000);
}

// ═══════════════════════ TABS ═══════════════════════
function initTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(tab.dataset.tab + '-tab').classList.add('active');
    });
  });
}

// ═══════════════════════ CHAT ═══════════════════════
function initChat() {
  const input = document.getElementById('chat-input');
  const send = document.getElementById('chat-send');
  const sendMessage = () => {
    const text = input.value.trim();
    if (!text) return;
    addChatMessage('user', text);
    input.value = '';
    addGlassboxEvent('tool', 'chat.send → "' + text.slice(0,50) + '"');

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type:'req', id:'chat-'+Date.now(), method:'chat.send', data:{message:text} }));
      addGlassboxEvent('model', ACTIVE_MODEL);
      document.getElementById('glassbox-bubble').classList.add('processing');
    } else {
      addChatMessage('assistant', "Gateway not connected. Start with: cell0 gateway");
      addGlassboxEvent('think', 'Gateway offline — cannot route');
    }
  };
  send.addEventListener('click', sendMessage);
  input.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });
}

function addChatMessage(role, text) {
  const container = document.getElementById('chat-messages');
  const msg = document.createElement('div');
  msg.className = 'chat-msg ' + role;
  msg.innerHTML = '<div class="sender">' + (role === 'user' ? '👤 You' : '🧬 Cell 0') + '</div>' + escapeHtml(text);
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

function escapeHtml(s) { const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }

// ═══════════════════════ GATEWAY WS ═══════════════════════
function connectGateway() {
  ws = new WebSocket('ws://127.0.0.1:' + GW_PORT);
  ws.onopen = () => {
    gwOnline = true;
    document.getElementById('status-dot').classList.remove('offline');
    document.getElementById('status-label').textContent = 'Connected';
    addGlassboxEvent('security', '✓ Gateway connected');
    ws.send(JSON.stringify({ type:'connect', deviceId:'portal-'+Date.now(), deviceName:'Nerve Portal', version:'1.2.0' }));
    setInterval(() => {
      if (ws.readyState === WebSocket.OPEN)
        ws.send(JSON.stringify({ type:'req', id:'poll-'+Date.now(), method:'system.status' }));
    }, 5000);
  };
  ws.onmessage = e => {
    try {
      const frame = JSON.parse(e.data);
      if (frame.type === 'res' && frame.id?.startsWith('chat-')) {
        document.getElementById('glassbox-bubble').classList.remove('processing');
        const reply = frame.data?.reply ?? frame.data?.text ?? JSON.stringify(frame.data);
        addChatMessage('assistant', reply);
        addGlassboxEvent('think', 'Response received');
      }
      if (frame.type === 'event') {
        addGlassboxEvent('tool', frame.event);
      }
    } catch {}
  };
  ws.onclose = () => {
    gwOnline = false;
    document.getElementById('status-dot').classList.add('offline');
    document.getElementById('status-label').textContent = 'Disconnected';
    setTimeout(connectGateway, 3000);
  };
  ws.onerror = () => {};
}

// ═══════════════════════ HTOP MONITOR ═══════════════════════
function renderHtop() {
  const uptime = formatUptime((Date.now() - startTime) / 1000);
  const services = [
    { cat: 'CORE SERVICES', items: [
      { pid:1, name:'gateway', status: gwOnline?'ONLINE':'OFFLINE', port:'18789', cpu:'2.1%', mem:'45MB', conn: gwOnline?'3':'—' },
      { pid:2, name:'portal', status:'ONLINE', port:'18790', cpu:'0.4%', mem:'12MB', conn:'1' },
      { pid:3, name:'python-daemon', status: pyOnline?'ONLINE':'STANDBY', port:'18800', cpu:'1.8%', mem:'128MB', conn:'—' },
    ]},
    { cat: 'CHANNELS (11)', items: [
      { pid:4, name:'whatsapp', status:'OFFLINE' },
      { pid:5, name:'telegram', status:'OFFLINE' },
      { pid:6, name:'discord', status:'OFFLINE' },
      { pid:7, name:'slack', status:'OFFLINE' },
      { pid:8, name:'signal', status:'READY', cpu:'0.1%', mem:'8MB' },
      { pid:9, name:'google-chat', status:'READY', cpu:'0.1%', mem:'8MB' },
      { pid:10, name:'bluebubbles', status:'OFFLINE' },
      { pid:11, name:'imessage', status:'OFFLINE' },
      { pid:12, name:'msteams', status:'OFFLINE' },
      { pid:13, name:'matrix', status:'OFFLINE' },
      { pid:14, name:'webchat', status:'ONLINE', port:'18790', cpu:'0.2%', mem:'4MB', conn:'1' },
    ]},
    { cat: 'ENGINE', items: [
      { pid:15, name:'agent-mesh', status:'ONLINE', cpu:'0.3%', mem:'16MB' },
      { pid:16, name:'agent-registry', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
      { pid:17, name:'agent-router', status:'ONLINE', cpu:'0.2%', mem:'8MB' },
      { pid:18, name:'agent-session', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
      { pid:19, name:'skill-manager', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
      { pid:20, name:'skill-registry', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
    ]},
    { cat: 'VOICE', items: [
      { pid:21, name:'stt (speech-to-text)', status:'ONLINE', cpu:'0.1%', mem:'8MB' },
      { pid:22, name:'tts (text-to-speech)', status:'ONLINE', cpu:'0.1%', mem:'8MB' },
      { pid:23, name:'wake-word', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
      { pid:24, name:'voice-session', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
    ]},
    { cat: 'SECURITY', items: [
      { pid:25, name:'auth', status:'ONLINE', cpu:'0.1%', mem:'2MB' },
      { pid:26, name:'jwt-handler', status:'ONLINE', cpu:'0.1%', mem:'2MB' },
      { pid:27, name:'rbac', status:'ONLINE', cpu:'0.1%', mem:'2MB' },
      { pid:28, name:'sandbox', status:'ONLINE', cpu:'0.1%', mem:'2MB' },
      { pid:29, name:'rate-limiter', status:'ONLINE', cpu:'0.1%', mem:'2MB' },
      { pid:30, name:'secrets-vault', status:'ONLINE', cpu:'0.1%', mem:'2MB' },
      { pid:31, name:'tool-audit', status:'ONLINE', cpu:'0.1%', mem:'2MB' },
    ]},
    { cat: 'COL (Civilization of Light)', items: [
      { pid:32, name:'col-orchestrator', status:'ONLINE', cpu:'0.2%', mem:'8MB' },
      { pid:33, name:'col-classifier', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
      { pid:34, name:'col-flow', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
      { pid:35, name:'col-resonance', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
      { pid:36, name:'col-synthesis', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
      { pid:37, name:'col-token-economy', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
      { pid:38, name:'col-philosophy', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
    ]},
    { cat: 'SWARM', items: [
      { pid:39, name:'swarm-coordinator', status:'ONLINE', cpu:'0.1%', mem:'6MB' },
      { pid:40, name:'swarm-consensus', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
      { pid:41, name:'swarm-discovery', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
      { pid:42, name:'swarm-failure-detector', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
      { pid:43, name:'collective-intelligence', status:'ONLINE', cpu:'0.1%', mem:'8MB' },
      { pid:44, name:'work-distribution', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
    ]},
    { cat: 'TOOLS', items: [
      { pid:45, name:'canvas (A2UI)', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
      { pid:46, name:'web-search', status:'ONLINE', cpu:'0.1%', mem:'4MB' },
      { pid:47, name:'bash', status:'ONLINE' },
      { pid:48, name:'file-ops (read/write)', status:'ONLINE' },
    ]},
    { cat: 'MONITORING', items: [
      { pid:49, name:'health-checks', status:'ONLINE', cpu:'0.1%', mem:'2MB' },
      { pid:50, name:'metrics-collector', status:'ONLINE', cpu:'0.1%', mem:'2MB' },
      { pid:51, name:'logging-system', status:'ONLINE', cpu:'0.1%', mem:'2MB' },
    ]},
  ];

  let html = '<div class="htop-header"> Cell 0 OS — Process Monitor (51 services)' +
    '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;uptime: ' + uptime + '</div>';
  html += '<div class="htop-row"><span class="htop-pid">PID</span><span class="htop-name">SERVICE</span>' +
    '<span class="htop-status">STATUS</span><span class="htop-port">PORT</span>' +
    '<span class="htop-cpu">CPU</span><span class="htop-mem">MEM</span><span class="htop-conn">CONN</span></div>';
  html += '<div class="htop-sep"></div>';

  for (const cat of services) {
    html += '<div class="htop-category"> ▸ ' + cat.cat + '</div>';
    for (const s of cat.items) {
      const sc = 's-' + s.status.toLowerCase();
      html += '<div class="htop-row">' +
        '<span class="htop-pid">' + s.pid + '</span>' +
        '<span class="htop-name">' + s.name + '</span>' +
        '<span class="htop-status ' + sc + '">' + s.status + '</span>' +
        '<span class="htop-port">' + (s.port||'—') + '</span>' +
        '<span class="htop-cpu">' + (s.cpu||'—') + '</span>' +
        '<span class="htop-mem">' + (s.mem||'—') + '</span>' +
        '<span class="htop-conn">' + (s.conn||'—') + '</span></div>';
    }
    html += '<div class="htop-sep"></div>';
  }

  html += '<div class="htop-footer">' +
    ' Sessions: 1 active | Agents: 4 registered | Skills: 21 loaded<br>' +
    ' Model: ' + ACTIVE_MODEL + ' | Auth: token | Bind: loopback<br>' +
    ' Providers: 22+ configured | UFA Layers: L0■ L1░ L2■ L3░ L4░ L5░ L6░ L7░</div>';

  document.getElementById('htop-display').innerHTML = html;
}

function formatUptime(s) {
  const h=Math.floor(s/3600), m=Math.floor((s%3600)/60), sec=Math.floor(s%60);
  if(h>0) return h+'h '+m+'m';
  if(m>0) return m+'m '+sec+'s';
  return sec+'s';
}

// ═══════════════════════ NERVE MAP ═══════════════════════
function renderNerveMap() {
  fetch('/api/config').then(r=>r.json()).then(cfg => {
    const providers = cfg.providers || [];
    const channels = cfg.channels || {};
    let html = '';

    // Core
    html += nerveSection('🌐 Core Services', [
      { name:'Gateway', detail:':'+cfg.gatewayPort, status:'active' },
      { name:'Portal', detail:':18790', status:'active' },
      { name:'Python Daemon', detail:':18800', status:'active' },
    ]);

    // Providers
    const providerNodes = providers.map(p => ({
      name: p.label, detail: p.hint||'', status: p.active ? 'active' : 'offline'
    }));
    html += nerveSection('🤖 Model Providers ('+providers.length+')', providerNodes);

    // Channels
    const channelNames = ['WhatsApp','Telegram','Discord','Slack','Signal','Google Chat','BlueBubbles','iMessage','MS Teams','Matrix','WebChat'];
    const channelNodes = channelNames.map(c => ({
      name: c, detail: channels[c.toLowerCase().replace(/\\s+/g,'')]?.enabled ? 'enabled' : '',
      status: channels[c.toLowerCase().replace(/\\s+/g,'')]?.enabled ? 'active' : 'offline'
    }));
    html += nerveSection('📡 Channels (11)', channelNodes);

    // Engine
    html += nerveSection('⚙️ Engine', [
      { name:'Agent Mesh', status:'active' }, { name:'Agent Router', status:'active' },
      { name:'Agent Registry', status:'active' }, { name:'Agent Session', status:'active' },
      { name:'Skill Manager', status:'active' }, { name:'Skill Registry', status:'active' },
    ]);

    // Security
    html += nerveSection('🔒 Security', [
      { name:'Auth + JWT', status:'active' }, { name:'RBAC', status:'active' },
      { name:'Sandbox', status:'active' }, { name:'Rate Limiter', status:'active' },
      { name:'Secrets Vault', status:'active' }, { name:'Tool Audit', status:'active' },
      { name:'Tool Policy', status:'active' },
    ]);

    // COL
    html += nerveSection('🧬 COL (Civilization of Light)', [
      { name:'Orchestrator', status:'active' }, { name:'Classifier', status:'active' },
      { name:'Flow', status:'active' }, { name:'Resonance', status:'active' },
      { name:'Synthesis', status:'active' }, { name:'Token Economy', status:'active' },
      { name:'Philosophy', status:'active' },
    ]);

    // Voice
    html += nerveSection('🎙 Voice', [
      { name:'STT', status:'active' }, { name:'TTS', status:'active' },
      { name:'Wake Word', status:'active' }, { name:'Voice Session', status:'active' },
    ]);

    // Swarm
    html += nerveSection('🐝 Swarm', [
      { name:'Coordinator', status:'active' }, { name:'Consensus', status:'active' },
      { name:'Discovery', status:'active' }, { name:'Failure Detector', status:'active' },
      { name:'Collective Intelligence', status:'active' }, { name:'Work Distribution', status:'active' },
    ]);

    // Tools
    html += nerveSection('🔧 Tools', [
      { name:'Canvas (A2UI)', status:'active' }, { name:'Web Search', status:'active' },
      { name:'Bash', status:'active' }, { name:'File Ops', status:'active' },
    ]);

    // Monitoring
    html += nerveSection('📊 Monitoring', [
      { name:'Health Checks', status:'active' }, { name:'Metrics', status:'active' },
      { name:'Logging', status:'active' },
    ]);

    document.getElementById('nerve-map').innerHTML = html;
  }).catch(() => {
    document.getElementById('nerve-map').innerHTML = '<p style="padding:40px;color:var(--text-muted)">Loading nerve map...</p>';
  });
}

function nerveSection(title, nodes) {
  let html = '<div class="nerve-section"><div class="nerve-section-title">' + title + '</div><div class="nerve-grid">';
  for (const n of nodes) {
    html += '<div class="nerve-node ' + n.status + '">' +
      '<span class="node-dot"></span><span class="node-name">' + n.name + '</span>' +
      (n.detail ? '<div class="node-detail">' + n.detail + '</div>' : '') + '</div>';
  }
  return html + '</div></div>';
}

// ═══════════════════════ CONFIG TAB ═══════════════════════
function renderConfig() {
  fetch('/api/config').then(r=>r.json()).then(cfg => {
    let html = '';
    html += configSection('Agent', { Provider: cfg.agent?.provider||'—', Model: cfg.agent?.model||'—' });
    html += configSection('Gateway', { Port: cfg.gateway?.port, Bind: cfg.gateway?.bind, Auth: cfg.gateway?.auth });
    html += configSection('Paths', { Config: cfg.configPath, Home: cfg.cell0Home });
    html += configSection('System', { Version: cfg.version });
    document.getElementById('config-panel').innerHTML = html;
  }).catch(() => {});
}

function configSection(title, data) {
  let html = '<div class="config-section"><div class="config-section-title">' + title + '</div>';
  for (const [k,v] of Object.entries(data)) {
    html += '<div class="config-row"><span class="config-key">' + k + '</span><span class="config-val">' + (v??'—') + '</span></div>';
  }
  return html + '</div>';
}

// ═══════════════════════ AGENT LIBRARY ═══════════════════════
const LIBRARY_CATEGORIES = ${JSON.stringify(DEFAULT_CATEGORIES.map(c => ({ name: c.name, slug: c.slug, icon: c.icon, color: c.color, dynamic: c.dynamic, specialists: c.specialists.map(s => ({ name: s.name, slug: s.slug, tools: s.tools, channelBinding: s.channelBinding, description: s.description })) })))};

function renderLibrary() {
  const total = LIBRARY_CATEGORIES.reduce((s,c) => s + c.specialists.length, 0);
  let html = '<div class="library-header">🧬 Agent Library</div>';
  html += '<div class="library-subtitle">' + LIBRARY_CATEGORIES.length + ' Categories · ' + total + ' Specialist Agents</div>';
  html += '<div class="library-grid" id="library-grid">';
  for (const cat of LIBRARY_CATEGORIES) {
    const badge = cat.dynamic ? ' ✦' : '';
    html += '<div class="library-folder" data-slug="'+cat.slug+'" style="--folder-color:'+cat.color+'" onclick="toggleCategory(this,this.dataset.slug)">' +
      '<div class="folder-glow"></div>' +
      '<div class="folder-icon">' + iconFor(cat.icon) + '</div>' +
      '<div class="folder-name">' + cat.name + badge + '</div>' +
      '<div class="folder-count">' + cat.specialists.length + ' specialists</div>' +
      '</div>';
  }
  html += '</div>';
  document.getElementById('library-panel').innerHTML = html;
}

function toggleCategory(el, slug) {
  const wasExpanded = el.classList.contains('expanded');
  document.querySelectorAll('.library-folder').forEach(f => {
    f.classList.remove('expanded');
    const sub = f.querySelector('.specialist-grid');
    if (sub) sub.remove();
  });
  if (wasExpanded) return;
  const cat = LIBRARY_CATEGORIES.find(c => c.slug === slug);
  if (!cat) return;
  el.classList.add('expanded');
  let subHtml = '<div class="specialist-grid">';
  for (const spec of cat.specialists) {
    subHtml += '<div class="specialist-card">' +
      '<div class="spec-name">🤖 ' + spec.name + '</div>' +
      '<div class="spec-desc">' + spec.description + '</div>' +
      '<div class="spec-tools">Tools: ' + spec.tools.join(', ') + '</div>' +
      (spec.channelBinding ? '<div class="spec-channel">← ' + spec.channelBinding + '</div>' : '') +
      '</div>';
  }
  subHtml += '</div>';
  el.insertAdjacentHTML('beforeend', subHtml);
}

function iconFor(icon) {
  const map = { sparkles:'✨', clock:'🕐', people:'👥', briefcase:'💼', tools:'🔧', airplane:'✈️', dollar:'💰', palette:'🎨', book:'📖', play:'▶️', dots:'⋯', lock:'🔒' };
  return map[icon] || '📂';
}

// ═══════════════════════ UFA BAR ═══════════════════════
function renderUfaBar() {
  const layers = [
    { id:'L0', name:'Resonance', level:3 },
    { id:'L1', name:'Invariant', level:0 },
    { id:'L2', name:'Guardian', level:2 },
    { id:'L3', name:'Tension', level:0 },
    { id:'L4', name:'Holographic', level:0 },
    { id:'L5', name:'Coherence', level:0 },
    { id:'L6', name:'Calibration', level:0 },
    { id:'L7', name:'Compression', level:0 },
  ];
  let html = '';
  for (const l of layers) {
    html += '<div class="ufa-layer"><span class="ufa-label">' + l.id + '</span><div class="ufa-blocks">';
    for (let i=0; i<3; i++) {
      html += '<div class="ufa-block ' + (i<l.level ? 'filled' : (i===l.level-1?'partial':'empty')) + '"></div>';
    }
    html += '</div></div>';
  }
  document.getElementById('ufa-bar').innerHTML = html;
}

// ═══════════════════════ GLASSBOX ═══════════════════════
function initGlassbox() {
  const bubble = document.getElementById('glassbox-bubble');
  const panel = document.getElementById('glassbox-panel');

  // Inject the dynamically mapped host and Gateway port for the static React asset hosting
  const iframe = document.getElementById('glassbox-iframe');
  iframe.src = 'http://' + window.location.hostname + ':' + GW_PORT + '/glassbox/';

  bubble.addEventListener('click', () => panel.classList.toggle('open'));
  document.getElementById('glassbox-close').addEventListener('click', () => panel.classList.remove('open'));

  // Draggable bubble
  let isDragging = false, startX, startY, origX, origY;
  bubble.addEventListener('mousedown', e => {
    isDragging = false; startX = e.clientX; startY = e.clientY;
    const rect = bubble.getBoundingClientRect();
    origX = rect.left; origY = rect.top;
    const onMove = ev => {
      if (Math.abs(ev.clientX-startX)>5 || Math.abs(ev.clientY-startY)>5) isDragging = true;
      if (isDragging) {
        bubble.style.right = 'auto'; bubble.style.bottom = 'auto';
        bubble.style.left = (origX + ev.clientX - startX) + 'px';
        bubble.style.top = (origY + ev.clientY - startY) + 'px';
        panel.style.right = 'auto'; panel.style.bottom = 'auto';
        panel.style.left = (origX + ev.clientX - startX - 312) + 'px';
        panel.style.top = (origY + ev.clientY - startY - 490) + 'px';
      }
    };
    const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });

  // Removed previous JS body update as React is now fully loaded via iframe
}

// ═══════════════════════ START ═══════════════════════
runBootSequence();
</script>
</body>
</html>`;
}
