#!/usr/bin/env node
/**
 * Cell 0 OS — CLI
 *
 * OpenClaw-equivalent CLI providing:
 *   cell0 gateway     — Start the WebSocket gateway
 *   cell0 status      — Show system status
 *   cell0 doctor      — Run diagnostic checks
 *   cell0 message     — Send a quick message
 *   cell0 onboard     — Interactive onboarding wizard
 *   cell0 configure   — Change settings
 *   cell0 portal      — Open web dashboard
 *   cell0 security    — Security audit
 *   cell0 update      — Update Cell 0 OS
 *
 * Matches OpenClaw's `openclaw` CLI structure and UX.
 */
import { Command } from "commander";
import { emitBanner } from "./banner.js";
import { theme, formatCheck, formatBullet } from "./theme.js";
const VERSION = "1.2.0";
const program = new Command();
// Emit banner on every CLI invocation (like OpenClaw)
emitBanner(VERSION);
program
    .name("cell0")
    .description("Cell 0 OS — Sovereign Edge AI Operating System")
    .version(VERSION);
// ─── cell0 gateway ──────────────────────────────────────────────────────────
program
    .command("gateway")
    .description("Start the Cell 0 WebSocket gateway")
    .option("-p, --port <port>", "Gateway port", "18789")
    .option("-H, --host <host>", "Bind host", "127.0.0.1")
    .option("--python-port <port>", "Python backend port", "18800")
    .option("--no-python", "Don't auto-start Python daemon")
    .option("-v, --verbose", "Verbose logging")
    .action(async (opts) => {
    const { CELL0_PROJECT_ROOT } = await import("../config/config.js");
    const { Gateway } = await import("../gateway/index.js");
    const gateway = new Gateway({
        port: parseInt(opts.port, 10),
        host: opts.host,
        pythonPort: parseInt(opts.pythonPort, 10),
        autoStartPython: opts.python !== false,
        projectRoot: CELL0_PROJECT_ROOT,
        verbose: opts.verbose ?? false,
    });
    const shutdown = async () => {
        await gateway.stop();
        process.exit(0);
    };
    process.on("SIGTERM", shutdown);
    process.on("SIGINT", shutdown);
    await gateway.start();
});
// ─── cell0 status ───────────────────────────────────────────────────────────
program
    .command("status")
    .description("Show system status")
    .option("-p, --port <port>", "Gateway port", "18789")
    .action(async (opts) => {
    try {
        const res = await fetch(`http://127.0.0.1:${opts.port}/api/status`);
        const data = (await res.json());
        console.log("\n🧬 Cell 0 OS Status\n");
        if (data.gateway) {
            console.log(formatCheck(true, `Gateway v${data.gateway.version}`));
            console.log(formatBullet(`Uptime: ${Math.floor(data.gateway.uptime)}s`));
            console.log(formatBullet(`Clients: ${data.gateway.clients}`));
            console.log(formatBullet(`Sessions: ${data.gateway.sessions}`));
        }
        if (data.python && !data.python.error) {
            console.log(formatCheck(true, "Python backend running"));
        }
        else {
            console.log(formatCheck(false, "Python backend not running"));
        }
        console.log("");
    }
    catch {
        console.error("\n❌ Cannot connect to gateway. Is it running?\n");
        console.error("   Start with: cell0 gateway\n");
        process.exit(1);
    }
});
// ─── cell0 doctor ───────────────────────────────────────────────────────────
program
    .command("doctor")
    .description("Run diagnostic checks")
    .option("--repair", "Auto-fix detected issues")
    .action(async (opts) => {
    console.log("\n🩺 Cell 0 Doctor\n");
    let allGood = true;
    // Check Node.js version
    const nodeVersion = process.versions.node;
    const nodeMajor = parseInt(nodeVersion.split(".")[0], 10);
    if (nodeMajor >= 20) {
        console.log(formatCheck(true, `Node.js ${nodeVersion} (≥20 required)`));
    }
    else {
        console.log(formatCheck(false, `Node.js ${nodeVersion} — upgrade to 20+`));
        allGood = false;
    }
    // Check Python venv
    const { existsSync } = await import("node:fs");
    const { join } = await import("node:path");
    const os = await import("node:os");
    const pythonPaths = [
        join(os.homedir(), ".cell0", "venv", "bin", "python3"),
        join(os.homedir(), ".cell0", ".venv", "bin", "python3"),
        "python3",
    ];
    let pythonPath = "";
    for (const p of pythonPaths) {
        if (p === "python3" || existsSync(p)) {
            pythonPath = p;
            break;
        }
    }
    if (pythonPath) {
        try {
            const { execSync } = await import("node:child_process");
            const ver = execSync(`${pythonPath} --version`, {
                encoding: "utf-8",
            }).trim();
            console.log(formatCheck(true, `${ver} (at ${pythonPath})`));
        }
        catch {
            console.log(formatCheck(false, "Python not found"));
            allGood = false;
        }
    }
    else {
        console.log(formatCheck(false, "Python not found"));
        allGood = false;
    }
    // Check daemon script
    const { CELL0_PROJECT_ROOT } = await import("../config/config.js");
    const daemonPaths = [
        join(CELL0_PROJECT_ROOT, "cell0", "cell0d.py"),
        join(CELL0_PROJECT_ROOT, "service", "cell0d.py"),
    ];
    let daemonPath = "";
    for (const dp of daemonPaths) {
        if (existsSync(dp)) {
            daemonPath = dp;
            break;
        }
    }
    if (daemonPath) {
        console.log(formatCheck(true, `Daemon found: ${daemonPath}`));
    }
    else {
        console.log(formatCheck(false, "Daemon script not found"));
        allGood = false;
    }
    // Check Python deps
    if (pythonPath) {
        try {
            const { execSync } = await import("node:child_process");
            execSync(`${pythonPath} -c "import fastapi; import uvicorn"`, { encoding: "utf-8" });
            console.log(formatCheck(true, "Python deps: fastapi, uvicorn"));
        }
        catch {
            console.log(formatCheck(false, "Python deps missing: pip install fastapi uvicorn"));
            allGood = false;
        }
    }
    // Check ports
    const net = await import("node:net");
    const portCheck = async (port, label) => {
        return new Promise((resolve) => {
            const socket = new net.Socket();
            socket.setTimeout(2000);
            socket.on("connect", () => {
                socket.destroy();
                console.log(formatCheck(true, `Port ${port} (${label}): responding`));
                resolve();
            });
            socket.on("timeout", () => {
                socket.destroy();
                console.log(`  ⚪ Port ${port} (${label}): not active`);
                resolve();
            });
            socket.on("error", () => {
                console.log(`  ⚪ Port ${port} (${label}): not active`);
                resolve();
            });
            socket.connect(port, "127.0.0.1");
        });
    };
    await portCheck(18789, "Gateway WS");
    await portCheck(18790, "Control Portal");
    await portCheck(18800, "Python HTTP");
    // Check filesystem structure
    const { CELL0_PATHS } = await import("../config/config.js");
    const fs = await import("node:fs");
    const requiredDirs = [
        { path: CELL0_PATHS.home, label: "Home" },
        { path: CELL0_PATHS.identity.root, label: "Identity" },
        { path: CELL0_PATHS.workspace.root, label: "Workspace" },
        { path: CELL0_PATHS.runtime.root, label: "Runtime" },
        { path: CELL0_PATHS.runtime.logs, label: "Logs" },
        { path: CELL0_PATHS.library.root, label: "Agent Library" },
        { path: CELL0_PATHS.workspaces, label: "Workspaces" },
        { path: CELL0_PATHS.credentials, label: "Credentials" },
        { path: CELL0_PATHS.kernel.root, label: "Kernel" },
    ];
    let fsGood = true;
    for (const dir of requiredDirs) {
        if (fs.existsSync(dir.path)) {
            try {
                fs.accessSync(dir.path, fs.constants.R_OK | fs.constants.W_OK);
                console.log(formatCheck(true, `${dir.label}: ${dir.path}`));
            }
            catch {
                console.log(formatCheck(false, `${dir.label}: Permission denied`));
                fsGood = false;
            }
        }
        else {
            console.log(formatCheck(false, `${dir.label}: Missing — run cell0 onboard`));
            fsGood = false;
        }
    }
    if (!fsGood)
        allGood = false;
    // Check workspace files (AGENTS.md etc)
    const workspaceDirs = [
        CELL0_PROJECT_ROOT,
        CELL0_PATHS.workspace.root,
    ];
    // Check config file
    const { CONFIG_PATH } = await import("../config/config.js");
    if (existsSync(CONFIG_PATH)) {
        console.log(formatCheck(true, `Config: ${CONFIG_PATH}`));
    }
    else {
        console.log(formatCheck(false, "Config not found — run cell0 onboard"));
    }
    // Check daemon service
    if (process.platform === "darwin") {
        const plistPath = join(os.homedir(), "Library", "LaunchAgents", "io.cell0.gateway.plist");
        const legacyPlistPath = join(os.homedir(), "Library", "LaunchAgents", "com.cell0.gateway.plist");
        if (existsSync(plistPath)) {
            console.log(formatCheck(true, "Gateway service (launchd io.cell0.gateway)"));
        }
        else if (existsSync(legacyPlistPath)) {
            console.log(`  ⚠️  Gateway service: legacy plist found (run cell0 doctor --repair to upgrade)`);
            allGood = false;
        }
        else {
            console.log(`  ⚪ Gateway service: not installed (run cell0 onboard --install-daemon)`);
        }
    }
    // Summary
    console.log("");
    if (allGood) {
        console.log("  🎉 All checks passed!\n");
    }
    else {
        console.log("  ⚠️  Some checks failed. Run cell0 onboard to fix.\n");
    }
    // Repair mode
    if (opts.repair) {
        console.log("\n🔧 Running auto-repair…\n");
        const repairedItems = [];
        // 1. Ensure all required directories exist
        const { CELL0_PATHS, CELL0_HOME } = await import("../config/config.js");
        const requiredDirs = [
            CELL0_HOME,
            CELL0_PATHS.identity.root,
            CELL0_PATHS.identity.keys,
            CELL0_PATHS.identity.certs,
            CELL0_PATHS.workspace.root,
            CELL0_PATHS.workspace.agents,
            CELL0_PATHS.workspace.skills,
            CELL0_PATHS.workspace.data,
            CELL0_PATHS.runtime.root,
            CELL0_PATHS.runtime.sessions,
            CELL0_PATHS.runtime.logs,
            CELL0_PATHS.runtime.pids,
            CELL0_PATHS.runtime.memory,
            join(CELL0_HOME, "logs"),
            CELL0_PATHS.library.root,
            CELL0_PATHS.library.categories,
            CELL0_PATHS.credentials,
            CELL0_PATHS.kernel.root,
            CELL0_PATHS.kernel.policies,
            CELL0_PATHS.snapshots,
        ];
        for (const dir of requiredDirs) {
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
                repairedItems.push(`Created directory: ${dir}`);
            }
        }
        // 2. Remove stale plists on macOS
        if (process.platform === "darwin") {
            const plistDir = join(os.homedir(), "Library", "LaunchAgents");
            const stalePlists = [
                "com.cell0.gateway.plist",
                "com.cell0.daemon.plist",
                "io.cell0.daemon.plist",
                "com.kulluai.cell0.plist",
            ];
            const { execSync } = await import("node:child_process");
            for (const stale of stalePlists) {
                const stalePath = join(plistDir, stale);
                if (fs.existsSync(stalePath)) {
                    try {
                        execSync(`launchctl unload "${stalePath}" 2>/dev/null`, { stdio: "ignore" });
                    }
                    catch { }
                    fs.unlinkSync(stalePath);
                    repairedItems.push(`Removed stale plist: ${stale}`);
                }
            }
        }
        // 3. Re-bootstrap system (creates missing identity/config files)
        try {
            const { bootstrapSystem } = await import("../init/bootstrap.js");
            await bootstrapSystem();
            repairedItems.push("Re-ran bootstrap (identity/soul/agent files ensured)");
        }
        catch (e) {
            console.log(`  ⚠️  Bootstrap re-run failed: ${e instanceof Error ? e.message : String(e)}`);
        }
        if (repairedItems.length === 0) {
            console.log("  ✅ Nothing needed repair.");
        }
        else {
            for (const item of repairedItems) {
                console.log(`  ✅ ${item}`);
            }
            console.log(`\n  ${repairedItems.length} item(s) repaired. Run cell0 doctor to verify.`);
        }
    }
});
// ─── cell0 message ──────────────────────────────────────────────────────────
program
    .command("message <text>")
    .description("Send a quick message to the active session")
    .option("-p, --port <port>", "Gateway port", "18789")
    .action(async (text, opts) => {
    const WebSocket = (await import("ws")).default;
    const ws = new WebSocket(`ws://127.0.0.1:${opts.port}`);
    ws.on("open", () => {
        ws.send(JSON.stringify({
            type: "connect",
            deviceId: `cli-${Date.now()}`,
            deviceName: "cell0-cli",
            version: VERSION,
        }));
        ws.send(JSON.stringify({
            type: "req",
            id: `msg-${Date.now()}`,
            method: "chat.send",
            data: { message: text },
        }));
    });
    ws.on("message", (raw) => {
        try {
            const frame = JSON.parse(raw.toString());
            if (frame.type === "res" && frame.id?.startsWith("msg-")) {
                if (frame.ok) {
                    console.log(`\n${theme.accent("🧬")} ${frame.data?.reply ?? "Message sent"}\n`);
                }
                else {
                    console.error(`\n❌ ${frame.error ?? "Failed"}\n`);
                }
                ws.close();
            }
            if (frame.type === "event" && frame.event === "chat.reply") {
                console.log(`\n${theme.accent("🧬")} ${frame.payload?.text ?? ""}\n`);
                ws.close();
            }
        }
        catch {
            // ignore
        }
    });
    ws.on("error", () => {
        console.error("\n❌ Cannot connect to gateway. Is it running?\n");
        console.error("   Start with: cell0 gateway\n");
        process.exit(1);
    });
});
// ─── cell0 onboard ──────────────────────────────────────────────────────────
program
    .command("onboard")
    .description("Interactive onboarding wizard")
    .option("--install-daemon", "Auto-install daemon service")
    .option("--flow <mode>", "Wizard mode: quickstart, manual")
    .option("--accept-risk", "Accept security warning")
    .option("--skip-channels", "Skip channel setup")
    .option("--skip-health", "Skip health check")
    .action(async (opts) => {
    const { bootstrapSystem } = await import("../init/bootstrap.js");
    await bootstrapSystem();
    const { runOnboardingWizard } = await import("../wizard/wizard.js");
    await runOnboardingWizard({
        installDaemon: opts.installDaemon,
        flow: opts.flow,
        skipChannels: opts.skipChannels,
        skipHealth: opts.skipHealth,
        acceptRisk: opts.acceptRisk,
    });
});
// ─── cell0 configure ────────────────────────────────────────────────────────
program
    .command("configure")
    .description("Change Cell 0 OS settings")
    .action(async () => {
    const { runOnboardingWizard } = await import("../wizard/wizard.js");
    // Re-run wizard in modify mode
    await runOnboardingWizard({
        skipHealth: true,
    });
});
// ─── cell0 portal ───────────────────────────────────────────────────────────
program
    .command("portal")
    .description("Open the Cell 0 web dashboard")
    .option("-p, --port <port>", "Portal port", "18790")
    .option("--gateway-port <port>", "Gateway port", "18789")
    .option("--no-open", "Do not open browser automatically")
    .action(async (opts) => {
    const { startPortal } = await import("../portal/portal.js");
    const portalPort = parseInt(opts.port, 10);
    const gatewayPort = parseInt(opts.gatewayPort, 10);
    const url = `http://127.0.0.1:${portalPort}`;
    console.log(`\n${theme.heading("🧬 Cell 0 OS Control Panel")}`);
    console.log(`   ${theme.muted("Portal:")}\t${theme.url(url)}`);
    console.log(`   ${theme.muted("Gateway:")}\t${theme.url(`ws://127.0.0.1:${gatewayPort}`)}`);
    console.log("");
    const server = await startPortal({
        port: portalPort,
        gatewayPort,
    });
    console.log(`${theme.success("✅")} Portal ready at ${theme.url(url)}\n`);
    // Open browser by default unless --no-open is passed
    if (opts.open !== false) {
        const opener = process.platform === "darwin" ? "open"
            : process.platform === "win32" ? "start"
                : "xdg-open";
        try {
            const { execSync } = await import("node:child_process");
            execSync(`${opener} "${url}"`, { stdio: "ignore" });
        }
        catch {
            console.log(`Could not auto-open browser. Visit: ${url}`);
        }
    }
    // Keep running
    process.on("SIGINT", () => {
        server.close();
        console.log("\n🛑 Portal stopped\n");
        process.exit(0);
    });
});
// ─── cell0 security ─────────────────────────────────────────────────────────
program
    .command("security")
    .description("Security audit and management")
    .argument("[action]", "Action: audit, fix", "audit")
    .option("--deep", "Run deep security audit")
    .action(async (action, opts) => {
    console.log("\n🔒 Cell 0 Security Audit\n");
    const { readConfigFileSnapshot } = await import("../config/config.js");
    const snapshot = readConfigFileSnapshot();
    const config = snapshot.config;
    // Check gateway auth
    if (config.gateway?.auth?.mode === "none") {
        console.log(formatCheck(false, "Gateway auth is disabled — enable token or password auth"));
    }
    else if (config.gateway?.auth?.mode === "token") {
        console.log(formatCheck(true, "Gateway auth: token mode"));
    }
    else if (config.gateway?.auth?.mode === "password") {
        console.log(formatCheck(true, "Gateway auth: password mode"));
    }
    else {
        console.log(`  ⚪ Gateway auth: not configured`);
    }
    // Check bind
    if (config.gateway?.bind &&
        config.gateway.bind !== "loopback") {
        console.log(formatCheck(false, `Gateway bind: ${config.gateway.bind} — consider loopback for security`));
    }
    else {
        console.log(formatCheck(true, "Gateway bind: loopback (secure)"));
    }
    // Check DM policies
    if (config.channels) {
        for (const [name, ch] of Object.entries(config.channels)) {
            if (ch?.enabled && ch?.dmPolicy === "open") {
                console.log(formatCheck(false, `${name}: DM policy is OPEN — consider "pairing" mode`));
            }
            else if (ch?.enabled) {
                console.log(formatCheck(true, `${name}: DM policy ${ch?.dmPolicy ?? "pairing"}`));
            }
        }
    }
    // Check workspace permissions
    if (config.agents?.defaults?.sandbox?.mode === "non-main") {
        console.log(formatCheck(true, "Sandbox: non-main sessions sandboxed"));
    }
    else {
        console.log(`  ⚪ Sandbox: not configured (tools run on host)`);
    }
    console.log("");
});
// ─── cell0 update ───────────────────────────────────────────────────────────
program
    .command("update")
    .description("Update Cell 0 OS")
    .option("--channel <channel>", "Update channel: stable, beta, dev", "stable")
    .action(async (opts) => {
    console.log(`\n${theme.heading("🧬 Cell 0 OS Update")}\n`);
    console.log(formatBullet(`Channel: ${opts.channel}`));
    console.log(formatBullet("Checking for updates…"));
    try {
        const { execSync } = await import("node:child_process");
        const tag = opts.channel === "stable"
            ? "latest"
            : opts.channel;
        execSync(`npm install -g cell0-os@${tag}`, {
            stdio: "inherit",
        });
        console.log(`\n${theme.success("✅")} Cell 0 OS updated successfully!\n`);
        console.log(formatBullet("Run cell0 doctor to verify.\n"));
    }
    catch (err) {
        console.error(`\n❌ Update failed: ${err instanceof Error ? err.message : err}\n`);
        process.exit(1);
    }
});
// ─── cell0 completions ──────────────────────────────────────────────────────
program
    .command("completions")
    .description("Manage shell completions")
    .argument("[action]", "install | uninstall | show", "install")
    .action(async (action) => {
    const { installCompletions, uninstallCompletions, generateZshCompletion } = await import("./completions.js");
    switch (action) {
        case "install":
            await installCompletions();
            break;
        case "uninstall":
            await uninstallCompletions();
            break;
        case "show":
            console.log(generateZshCompletion());
            break;
        default:
            console.error(`Unknown action: ${action}. Use install, uninstall, or show.`);
            process.exit(1);
    }
});
// ─── cell0 daemon ───────────────────────────────────────────────────────────
program
    .command("daemon")
    .description("Manage the Cell 0 gateway service")
    .argument("[action]", "start | stop | restart | status | install | uninstall", "status")
    .action(async (action) => {
    const { getServiceStatus, startService, stopService, restartService, uninstallService } = await import("../infra/daemon-ctl.js");
    switch (action) {
        case "status": {
            const s = getServiceStatus();
            console.log("\n🔧 Cell 0 Daemon Status\n");
            console.log(`  Platform:  ${s.platform}`);
            console.log(`  Label:     ${s.label ?? "—"}`);
            console.log(`  Installed: ${s.installed ? "✅ yes" : "❌ no"}`);
            console.log(`  Running:   ${s.running ? `✅ yes${s.pid ? ` (PID ${s.pid})` : ""}` : "❌ no"}`);
            if (s.detail)
                console.log(`\n  Detail:\n${s.detail.split("\n").map((l) => "    " + l).join("\n")}`);
            if (!s.installed)
                console.log("\n  → Run: cell0 daemon install  (or: cell0 onboard)");
            if (s.installed && !s.running)
                console.log("\n  → Run: cell0 daemon start");
            console.log();
            break;
        }
        case "start": {
            console.log("Starting Cell 0 gateway service…");
            try {
                startService();
                console.log("✅ Service started.");
            }
            catch (err) {
                console.error(`❌ ${err instanceof Error ? err.message : String(err)}`);
                process.exit(1);
            }
            break;
        }
        case "stop": {
            console.log("Stopping Cell 0 gateway service…");
            try {
                stopService();
                console.log("✅ Service stopped.");
            }
            catch (err) {
                console.error(`❌ ${err instanceof Error ? err.message : String(err)}`);
                process.exit(1);
            }
            break;
        }
        case "restart": {
            console.log("Restarting Cell 0 gateway service…");
            try {
                restartService();
                console.log("✅ Service restarted.");
            }
            catch (err) {
                console.error(`❌ ${err instanceof Error ? err.message : String(err)}`);
                process.exit(1);
            }
            break;
        }
        case "install": {
            console.log("Installing Cell 0 gateway service…");
            const { DaemonManager } = await import("../infra/daemon.js");
            const { CELL0_PROJECT_ROOT } = await import("../config/config.js");
            const mgr = new DaemonManager(CELL0_PROJECT_ROOT);
            const ok = await mgr.installService();
            if (ok) {
                console.log("✅ Service installed. Starting…");
                try {
                    startService();
                    console.log("✅ Service started.");
                }
                catch { /* ignore */ }
            }
            else {
                console.error("❌ Service installation failed. Run: cell0 onboard --install-daemon");
                process.exit(1);
            }
            break;
        }
        case "uninstall": {
            console.log("Uninstalling Cell 0 gateway service…");
            try {
                uninstallService();
                console.log("✅ Service uninstalled.");
            }
            catch (err) {
                console.error(`❌ ${err instanceof Error ? err.message : String(err)}`);
                process.exit(1);
            }
            break;
        }
        default:
            console.error(`Unknown action: ${action}. Use start, stop, restart, status, install, or uninstall.`);
            process.exit(1);
    }
});
// ─── cell0 logs ─────────────────────────────────────────────────────────────
program
    .command("logs")
    .description("Tail Cell 0 gateway logs")
    .option("-f, --follow", "Follow log output (like tail -f)")
    .option("-n, --lines <n>", "Number of lines to show", "50")
    .option("--error", "Show error log instead of stdout log")
    .action(async (opts) => {
    const fs = await import("node:fs");
    const path = await import("node:path");
    const os = await import("node:os");
    const logsDir = path.join(os.homedir(), ".cell0", "logs");
    const logFile = opts.error
        ? path.join(logsDir, "gateway.err.log")
        : path.join(logsDir, "gateway.log");
    if (!fs.existsSync(logFile)) {
        const legacy = opts.error
            ? path.join(os.homedir(), ".cell0", "gateway.err")
            : path.join(os.homedir(), ".cell0", "gateway.log");
        if (!fs.existsSync(legacy)) {
            console.log(`No log file found at:\n  ${logFile}\n\nStart the gateway first: cell0 gateway`);
            process.exit(0);
        }
        console.log(`[Using legacy log path: ${legacy}]`);
    }
    const target = fs.existsSync(logFile)
        ? logFile
        : opts.error
            ? path.join(os.homedir(), ".cell0", "gateway.err")
            : path.join(os.homedir(), ".cell0", "gateway.log");
    const lines = parseInt(opts.lines, 10) || 50;
    console.log(`\n📋 ${opts.error ? "Error" : "Gateway"} Log${opts.follow ? " (following…)" : ""}`);
    console.log(`   ${target}\n`);
    if (!opts.follow) {
        const content = fs.readFileSync(target, "utf-8");
        const allLines = content.split("\n").filter(Boolean);
        console.log(allLines.slice(-lines).join("\n"));
        return;
    }
    // Follow mode
    let position = fs.statSync(target).size;
    const printNew = () => {
        const stat = fs.statSync(target);
        if (stat.size < position)
            position = 0;
        if (stat.size === position)
            return;
        const stream = fs.createReadStream(target, {
            start: position,
            end: stat.size,
            encoding: "utf-8",
        });
        stream.on("data", (chunk) => process.stdout.write(chunk));
        stream.on("end", () => { position = stat.size; });
    };
    const content = fs.readFileSync(target, "utf-8");
    const allLines = content.split("\n").filter(Boolean);
    console.log(allLines.slice(-lines).join("\n"));
    console.log("\n--- following (Ctrl+C to stop) ---\n");
    fs.watch(target, () => { printNew(); });
    await new Promise((resolve) => {
        process.on("SIGINT", () => { console.log("\nStopped."); resolve(); });
        process.on("SIGTERM", () => resolve());
    });
});
// ─── cell0 library ──────────────────────────────────────────────────────────
program
    .command("library")
    .description("Browse the Agent Library — categories and specialists")
    .option("-c, --category <slug>", "Show specialists in a specific category")
    .option("--json", "Output as JSON")
    .action(async (opts) => {
    const { DEFAULT_CATEGORIES, getSpecialistCount } = await import("../library/manifest.js");
    const totalSpecialists = getSpecialistCount();
    if (opts.json) {
        const { buildManifest } = await import("../library/manifest.js");
        console.log(JSON.stringify(buildManifest(), null, 2));
        return;
    }
    if (opts.category) {
        const cat = DEFAULT_CATEGORIES.find(c => c.slug === opts.category);
        if (!cat) {
            console.log(`\n  ❌ Unknown category: ${opts.category}`);
            console.log(`     Available: ${DEFAULT_CATEGORIES.map(c => c.slug).join(', ')}\n`);
            return;
        }
        console.log(`\n  📂 ${cat.name}  (${cat.icon})  ${cat.color}`);
        console.log(`  ${'─'.repeat(50)}`);
        for (const spec of cat.specialists) {
            const binding = spec.channelBinding ? ` ← ${spec.channelBinding}` : '';
            console.log(`    🤖 ${spec.name}${binding}`);
            console.log(`       ${spec.description}`);
            console.log(`       Tools: ${spec.tools.join(', ')}`);
        }
        console.log('');
        return;
    }
    console.log(`\n  🧬 Agent Library — ${DEFAULT_CATEGORIES.length} Categories, ${totalSpecialists} Specialists\n`);
    for (const cat of DEFAULT_CATEGORIES) {
        const badge = cat.dynamic ? ' (dynamic)' : '';
        console.log(`  📂 ${cat.name}${badge}  [${cat.specialists.length} specialists]  ${cat.color}`);
        for (const spec of cat.specialists) {
            const binding = spec.channelBinding ? ` ← ${spec.channelBinding}` : '';
            console.log(`     └─ 🤖 ${spec.name}${binding}`);
        }
        console.log('');
    }
});
// ─── cell0 config ───────────────────────────────────────────────────────────
program
    .command("config")
    .description("Manage Cell 0 configuration")
    .argument("[action]", "show | backup | history | restore", "show")
    .argument("[target]", "Backup file path for restore")
    .action(async (action, target) => {
    const { readConfigFileSnapshot, listConfigBackups, restoreConfigBackup, CONFIG_PATH, } = await import("../config/config.js");
    switch (action) {
        case "show": {
            const snap = readConfigFileSnapshot();
            if (!snap.exists) {
                console.log("No config found. Run: cell0 onboard");
                break;
            }
            if (!snap.valid) {
                console.log("⚠️  Config exists but is invalid. Run: cell0 doctor --repair");
                break;
            }
            // Pretty-print config (redact sensitive values)
            const cfg = JSON.parse(JSON.stringify(snap.config));
            if (cfg.agent?.apiKey)
                cfg.agent.apiKey = "***";
            if (cfg.gateway?.auth?.token)
                cfg.gateway.auth.token = "***";
            if (cfg.gateway?.auth?.password)
                cfg.gateway.auth.password = "***";
            console.log("\n📋 Cell 0 Configuration\n");
            console.log(`   Path: ${CONFIG_PATH}\n`);
            console.log(JSON.stringify(cfg, null, 2));
            break;
        }
        case "backup": {
            const snap2 = readConfigFileSnapshot();
            if (!snap2.valid) {
                console.error("Cannot backup: config is invalid or missing.");
                process.exit(1);
            }
            const { writeConfig } = await import("../config/config.js");
            writeConfig(snap2.config);
            const backups = listConfigBackups();
            if (backups.length > 0) {
                console.log(`✅ Backup created: ${backups[0].file}`);
            }
            else {
                console.log("✅ Config written (backup created if previous config existed).");
            }
            break;
        }
        case "history": {
            const backups = listConfigBackups();
            if (backups.length === 0) {
                console.log("No config backups found.");
                break;
            }
            console.log("\n📂 Config Backups\n");
            for (const b of backups) {
                console.log(`  ${b.file}  (${b.mtime.toLocaleString()}, ${Math.round(b.size / 1024 * 10) / 10} KB)`);
            }
            console.log(`\n  Restore with: cell0 config restore <filename>`);
            break;
        }
        case "restore": {
            if (!target) {
                const backups = listConfigBackups();
                if (backups.length === 0) {
                    console.error("No backups found.");
                    process.exit(1);
                }
                target = backups[0].path;
                console.log(`Restoring latest backup: ${backups[0].file}`);
            }
            try {
                restoreConfigBackup(target);
                console.log("✅ Config restored successfully.");
            }
            catch (err) {
                console.error(`Failed: ${err instanceof Error ? err.message : String(err)}`);
                process.exit(1);
            }
            break;
        }
        default:
            console.error(`Unknown action: ${action}. Use show, backup, history, or restore.`);
            process.exit(1);
    }
});
// ─── Reset ──────────────────────────────────────────────────────────────────
program
    .command("reset")
    .description("Wipe all Cell 0 data and remove the daemon service")
    .option("--yes", "Skip confirmation prompt")
    .action(async (opts) => {
    const p = await import("@clack/prompts");
    p.intro("cell0 reset");
    if (!opts.yes) {
        const confirmed = await p.confirm({
            message: "This will delete ~/.cell0/ and uninstall the daemon. Continue?",
            initialValue: false,
        });
        if (!confirmed || p.isCancel(confirmed)) {
            p.cancel("Reset cancelled.");
            return;
        }
    }
    const s = p.spinner();
    s.start("Resetting Cell 0…");
    try {
        const { uninstallService } = await import("../infra/daemon-ctl.js");
        uninstallService();
    }
    catch { /* daemon may not be installed */ }
    const { default: fs } = await import("node:fs");
    const { default: os } = await import("node:os");
    const { default: path } = await import("node:path");
    const cell0Home = path.join(os.homedir(), ".cell0");
    if (fs.existsSync(cell0Home)) {
        fs.rmSync(cell0Home, { recursive: true, force: true });
    }
    s.stop("Cell 0 data removed.");
    p.outro("Reset complete. Run `cell0 onboard` to start fresh.");
});
// ─── Parse ──────────────────────────────────────────────────────────────────
program.parse();
//# sourceMappingURL=index.js.map