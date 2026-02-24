/**
 * Cell 0 OS — TUI Onboarding Wizard
 *
 * Full interactive setup wizard matching OpenClaw's onboarding flow.
 * Uses @clack/prompts for beautiful TUI elements.
 *
 * Flow:
 * 1. Banner → 2. Security warning → 3. QuickStart/Manual →
 * 4. Model provider → 5. API key → 6. Workspace → 7. Gateway config →
 * 8. Daemon install → 9. Health check → 10. Portal URL
 */

import * as p from "@clack/prompts";
import crypto from "node:crypto";
import fs from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";

import { emitBannerArt } from "../cli/banner.js";
import { theme } from "../cli/theme.js";
import {
    type Cell0Config,
    CONFIG_PATH,
    DEFAULT_GATEWAY_PORT,
    DEFAULT_PORTAL_PORT,
    DEFAULT_WORKSPACE,
    readConfigFileSnapshot,
    resolveGatewayPort,
    resolveUserPath,
    summarizeConfig,
    writeConfig,
} from "../config/config.js";
import {
    type AuthChoice,
    buildProviderGroups,
    getApiKeyPrompt,
    getDefaultModelForProvider,
    requiresApiKey,
} from "../config/providers.js";

// ─── Constants ────────────────────────────────────────────────────────────

const VERSION = "1.2.0";

// ─── Main Wizard ──────────────────────────────────────────────────────────

export async function runOnboardingWizard(opts: {
    installDaemon?: boolean;
    flow?: string;
    skipChannels?: boolean;
    skipHealth?: boolean;
    acceptRisk?: boolean;
}): Promise<void> {
    // 1. Banner
    emitBannerArt(VERSION);

    p.intro(theme.heading("Cell 0 OS Onboarding"));

    // 2. Security acknowledgement
    await requireRiskAcknowledgement(opts.acceptRisk);

    // 3. Read existing config
    const snapshot = readConfigFileSnapshot();
    let baseConfig: Cell0Config = snapshot.valid ? snapshot.config : {};

    if (snapshot.exists && !snapshot.valid) {
        p.note(
            "Config file exists but has issues. Run `cell0 doctor` to repair.",
            "⚠️  Invalid Config"
        );
        p.outro("Fix config issues, then re-run onboarding.");
        process.exit(1);
    }

    // Handle existing config
    if (snapshot.exists && snapshot.valid) {
        p.note(summarizeConfig(baseConfig), "📋 Existing config detected");

        const action = (await p.select({
            message: "Config handling",
            options: [
                { value: "keep", label: "Use existing values" },
                { value: "modify", label: "Update values" },
                { value: "reset", label: "Reset" },
            ],
        })) as string;

        if (p.isCancel(action)) {
            p.cancel("Onboarding cancelled.");
            process.exit(0);
        }

        if (action === "reset") {
            baseConfig = {};
        }
    }

    // 4. QuickStart vs Manual
    const explicitFlow = opts.flow?.trim();
    type WizardFlow = "quickstart" | "advanced";
    let flow: WizardFlow;

    if (explicitFlow === "quickstart" || explicitFlow === "advanced") {
        flow = explicitFlow;
    } else {
        const selected = await p.select({
            message: "Onboarding mode",
            options: [
                {
                    value: "quickstart",
                    label: "QuickStart",
                    hint: "Configure details later via cell0 configure.",
                },
                {
                    value: "advanced",
                    label: "Manual",
                    hint: "Configure port, network, auth, and provider options.",
                },
            ],
            initialValue: "quickstart",
        });

        if (p.isCancel(selected)) {
            p.cancel("Onboarding cancelled.");
            process.exit(0);
        }
        flow = selected as WizardFlow;
    }

    // QuickStart defaults note
    if (flow === "quickstart") {
        p.note(
            [
                `Gateway port: ${DEFAULT_GATEWAY_PORT}`,
                "Gateway bind: Loopback (127.0.0.1)",
                "Gateway auth: Token (auto-generated)",
                "Tailscale exposure: Off",
                "Direct to model/auth provider.",
            ].join("\n"),
            "⚡ QuickStart"
        );
    }

    // 5. Model/auth provider selection
    const { groups, skipOption } = buildProviderGroups(true);
    const providerOptions = [
        ...groups.map((group) => ({
            value: group.value,
            label: group.label,
            hint: group.hint,
        })),
        ...(skipOption ? [{ value: "skip", label: skipOption.label }] : []),
    ];

    const providerSelection = (await p.select({
        message: "Model/auth provider",
        options: providerOptions as any,
    })) as string;

    if (p.isCancel(providerSelection)) {
        p.cancel("Onboarding cancelled.");
        process.exit(0);
    }

    let nextConfig: Cell0Config = { ...baseConfig };

    if (providerSelection !== "skip") {
        // Find the selected group
        const selectedGroup = groups.find((g) => g.value === providerSelection);

        let authChoice: AuthChoice;

        if (selectedGroup && selectedGroup.options.length > 1) {
            // Sub-selection for providers with multiple auth methods
            const methodSelection = await p.select({
                message: `${selectedGroup.label} auth method`,
                options: [
                    ...selectedGroup.options.map((opt) => ({
                        value: opt.value,
                        label: opt.label,
                        hint: opt.hint,
                    })),
                    { value: "__back" as const, label: "Back" },
                ] as any,
            });

            if (p.isCancel(methodSelection) || methodSelection === "__back") {
                authChoice = selectedGroup.options[0].value;
            } else {
                authChoice = methodSelection as AuthChoice;
            }
        } else if (selectedGroup && selectedGroup.options.length === 1) {
            authChoice = selectedGroup.options[0].value;
        } else {
            authChoice = "skip";
        }

        // 6. API key input
        if (authChoice !== "skip" && requiresApiKey(authChoice)) {
            const { message, placeholder } = getApiKeyPrompt(authChoice);

            const apiKey = await p.password({
                message,
                validate: (val) => {
                    if (!val || val.trim().length === 0) {
                        return "API key is required. Select 'Skip' to configure later.";
                    }
                    return undefined;
                },
            });

            if (p.isCancel(apiKey)) {
                p.cancel("Onboarding cancelled.");
                process.exit(0);
            }

            nextConfig.agent = {
                ...nextConfig.agent,
                provider: providerSelection,
                apiKey: apiKey as string,
            };
        } else if (authChoice !== "skip") {
            nextConfig.agent = {
                ...nextConfig.agent,
                provider: providerSelection,
            };
        }

        // Set default model for provider
        const defaultModel = getDefaultModelForProvider(providerSelection);
        nextConfig.agent = {
            ...nextConfig.agent,
            model: defaultModel,
        };
    }

    // 7. Workspace directory
    let workspaceDir: string;

    if (flow === "quickstart") {
        workspaceDir = resolveUserPath(
            baseConfig.agents?.defaults?.workspace ?? DEFAULT_WORKSPACE
        );
    } else {
        const wsInput = await p.text({
            message: "Workspace directory",
            initialValue:
                baseConfig.agents?.defaults?.workspace ?? DEFAULT_WORKSPACE,
            placeholder: DEFAULT_WORKSPACE,
        });

        if (p.isCancel(wsInput)) {
            p.cancel("Onboarding cancelled.");
            process.exit(0);
        }
        workspaceDir = resolveUserPath(
            (wsInput as string).trim() || DEFAULT_WORKSPACE
        );
    }

    nextConfig.agents = {
        ...nextConfig.agents,
        defaults: {
            ...nextConfig.agents?.defaults,
            workspace: workspaceDir,
        },
    };

    // 8. Gateway config (Manual mode only)
    let gatewayToken = crypto.randomBytes(32).toString("hex");

    if (flow === "advanced") {
        const portInput = await p.text({
            message: "Gateway port",
            initialValue: String(
                baseConfig.gateway?.port ?? DEFAULT_GATEWAY_PORT
            ),
        });

        if (p.isCancel(portInput)) {
            p.cancel("Onboarding cancelled.");
            process.exit(0);
        }

        const bind = (await p.select({
            message: "Gateway bind",
            options: [
                { value: "loopback", label: "Loopback (127.0.0.1)" },
                { value: "lan", label: "LAN (0.0.0.0)" },
                { value: "auto", label: "Auto" },
            ],
            initialValue: baseConfig.gateway?.bind ?? "loopback",
        })) as string;

        if (p.isCancel(bind)) {
            p.cancel("Onboarding cancelled.");
            process.exit(0);
        }

        const authMode = (await p.select({
            message: "Gateway auth",
            options: [
                { value: "token", label: "Token (default)" },
                { value: "password", label: "Password" },
                { value: "none", label: "None (loopback only)" },
            ],
            initialValue: "token",
        })) as "token" | "password" | "none";

        if (p.isCancel(authMode)) {
            p.cancel("Onboarding cancelled.");
            process.exit(0);
        }

        if (authMode === "password") {
            const pw = await p.password({
                message: "Gateway password",
            });
            if (!p.isCancel(pw)) {
                nextConfig.gateway = {
                    ...nextConfig.gateway,
                    auth: { mode: "password", password: pw as string },
                };
            }
        } else if (authMode === "token") {
            nextConfig.gateway = {
                ...nextConfig.gateway,
                auth: { mode: "token", token: gatewayToken },
            };
        } else {
            nextConfig.gateway = {
                ...nextConfig.gateway,
                auth: { mode: "none" },
            };
        }

        nextConfig.gateway = {
            ...nextConfig.gateway,
            port: parseInt(portInput as string, 10) || DEFAULT_GATEWAY_PORT,
            bind: bind as "loopback" | "lan" | "auto",
        };
    } else {
        // QuickStart defaults
        nextConfig.gateway = {
            ...nextConfig.gateway,
            port: baseConfig.gateway?.port ?? DEFAULT_GATEWAY_PORT,
            bind: baseConfig.gateway?.bind ?? "loopback",
            auth: baseConfig.gateway?.auth ?? {
                mode: "token",
                token: gatewayToken,
            },
        };
        if (baseConfig.gateway?.auth?.token) {
            gatewayToken = baseConfig.gateway.auth.token;
        }
    }

    // 9. Write config
    nextConfig.meta = {
        wizard: "onboard",
        version: VERSION,
    };

    writeConfig(nextConfig);
    p.note(`Config saved to ${CONFIG_PATH}`, "💾 Configuration");

    // 10. Ensure workspace
    await ensureWorkspace(workspaceDir);

    // 10.2. Install shell completions
    try {
        const { installCompletions } = await import("../cli/completions.js");
        await installCompletions();
    } catch {
        // Non-fatal — user can run `cell0 completions install` manually
    }

    // 10.5. Optional channel setup
    if (!opts.skipChannels) {
        nextConfig = await runChannelSetup(nextConfig);
        writeConfig(nextConfig);
    }

    // 11. Daemon install
    const installDaemon =
        opts.installDaemon ??
        (flow === "quickstart"
            ? true
            : ((await p.confirm({
                message: "Install Gateway service (recommended)",
                initialValue: true,
            })) as boolean));

    if (installDaemon && !p.isCancel(installDaemon)) {
        await installDaemonService(nextConfig, gatewayToken);
    }

    // 12. Health check
    if (!opts.skipHealth) {
        await runHealthCheck(nextConfig);
    }

    // 13. Show final info
    const port = resolveGatewayPort(nextConfig);
    const portalPort = DEFAULT_PORTAL_PORT;
    const authCfg = nextConfig.gateway?.auth;
    const tokenLine =
        authCfg?.mode === "token" && authCfg.token
            ? `Token:     ${authCfg.token}`
            : "";

    p.note(
        [
            `Gateway:   ws://127.0.0.1:${port}`,
            `Portal:    http://127.0.0.1:${portalPort}`,
            tokenLine,
            `Config:    ${CONFIG_PATH}`,
            `Workspace: ${workspaceDir}`,
            "",
            "Next steps:",
            `  ${theme.command("cell0 gateway")}     — Start the gateway`,
            `  ${theme.command("cell0 doctor")}      — Run diagnostics`,
            `  ${theme.command("cell0 configure")}   — Change settings`,
            `  ${theme.command("cell0 portal")}      — Open web dashboard`,
        ]
            .filter(Boolean)
            .join("\n"),
        "🧬 Cell 0 OS Ready"
    );

    p.outro("Your sovereign AI is ready. Start with: cell0 gateway");
}

// ─── Security Acknowledgement ─────────────────────────────────────────────

async function requireRiskAcknowledgement(
    preAccepted?: boolean
): Promise<void> {
    if (preAccepted) return;

    p.note(
        [
            "Security warning — please read.",
            "",
            "Cell 0 OS is a powerful tool that can run actions on your machine.",
            "A bad prompt can trick it into doing unsafe things.",
            "",
            "Recommended baseline:",
            "- Pairing/allowlists + mention gating.",
            "- Sandbox + least-privilege tools.",
            "- Keep secrets out of the agent's reachable filesystem.",
            "- Use the strongest available model for bots with tools.",
            "",
            "Run regularly:",
            "  cell0 security audit --deep",
            "  cell0 security audit --fix",
            "",
            "Must read: https://docs.cell0.ai/gateway/security",
        ].join("\n"),
        "🔒 Security"
    );

    const ok = await p.confirm({
        message:
            "I understand this is powerful and inherently risky. Continue?",
        initialValue: false,
    });

    if (p.isCancel(ok) || !ok) {
        p.cancel("Risk not accepted. Onboarding cancelled.");
        process.exit(0);
    }
}

// ─── Channel Setup ────────────────────────────────────────────────────────

async function runChannelSetup(config: Cell0Config): Promise<Cell0Config> {
    const channel = await p.select({
        message: "Connect a messaging channel? (optional)",
        options: [
            { value: "skip", label: "Skip — configure later with `cell0 configure`" },
            { value: "whatsapp", label: "WhatsApp" },
            { value: "telegram", label: "Telegram" },
        ],
        initialValue: "skip",
    });
    if (p.isCancel(channel) || channel === "skip") return config;

    if (channel === "whatsapp") {
        const phone = await p.text({
            message: "Your WhatsApp number (E.164, e.g. +1234567890)",
            placeholder: "+1234567890",
            validate: (v) => (!v?.trim() ? "Required" : undefined),
        });
        if (!p.isCancel(phone) && phone) {
            config = {
                ...config,
                channels: {
                    ...config.channels,
                    whatsapp: { enabled: true, dmPolicy: "pairing", allowFrom: [(phone as string).trim()] } as any,
                },
            };
        }
    } else if (channel === "telegram") {
        const tok = await p.text({
            message: "Telegram Bot Token (from @BotFather)",
            placeholder: "123456789:ABCdef...",
            validate: (v) => (!v?.trim() ? "Required" : undefined),
        });
        if (!p.isCancel(tok) && tok) {
            config = {
                ...config,
                channels: {
                    ...config.channels,
                    telegram: { enabled: true, dmPolicy: "open", token: (tok as string).trim() } as any,
                },
            };
        }
    }
    return config;
}

// ─── Workspace Setup ──────────────────────────────────────────────────────

async function ensureWorkspace(dir: string): Promise<void> {
    const s = p.spinner();
    s.start("Setting up workspace…");

    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }

    // Create default workspace files if they don't exist
    const defaults: Record<string, string> = {
        "AGENTS.md": [
            "# Cell 0 Agents",
            "",
            "Define your agent behaviors and capabilities here.",
            "",
            "## Default Agent",
            "",
            "The default agent handles all incoming messages.",
            "Customize its behavior by editing this file.",
        ].join("\n"),
        "SOUL.md": [
            "# Cell 0 Soul",
            "",
            "This file defines the personality and values of your AI assistant.",
            "",
            "## Core Values",
            "",
            "- Privacy-first: Your data stays on your hardware",
            "- Sovereignty: You control what the AI can do",
            "- Transparency: Actions are logged and auditable",
            "- Safety: Conservative defaults, explicit opt-in for risky actions",
        ].join("\n"),
        "TOOLS.md": [
            "# Cell 0 Tools",
            "",
            "Available tools and their configurations.",
            "",
            "## Built-in Tools",
            "",
            "- `bash` — Execute shell commands",
            "- `read` — Read files",
            "- `write` — Write files",
            "- `edit` — Edit files",
            "- `browser` — Browser automation",
            "- `canvas` — Visual workspace (A2UI)",
        ].join("\n"),
    };

    for (const [filename, content] of Object.entries(defaults)) {
        const filepath = path.join(dir, filename);
        if (!fs.existsSync(filepath)) {
            fs.writeFileSync(filepath, content + "\n", "utf-8");
        }
    }

    // Create skills directory
    const skillsDir = path.join(dir, "skills");
    if (!fs.existsSync(skillsDir)) {
        fs.mkdirSync(skillsDir, { recursive: true });
    }

    s.stop("Workspace ready.");
}

// ─── Daemon Installer ─────────────────────────────────────────────────────

async function installDaemonService(
    config: Cell0Config,
    token: string
): Promise<void> {
    const s = p.spinner();
    s.start("Installing Gateway service…");

    try {
        const port = resolveGatewayPort(config);

        if (process.platform === "darwin") {
            const authToken = config.gateway?.auth?.mode === "token" ? token : "";
            await installLaunchAgent(port, authToken);
            s.stop("Gateway service installed (launchd).");
        } else if (process.platform === "linux") {
            const authToken = config.gateway?.auth?.mode === "token" ? token : "";
            await installSystemdService(port, authToken);
            s.stop("Gateway service installed (systemd).");
        } else {
            s.stop(
                "Gateway service: manual start required (unsupported platform for auto-install)."
            );
        }
    } catch (err) {
        s.stop("Gateway service install failed.");
        p.note(
            `Error: ${err instanceof Error ? err.message : String(err)}\n\nStart manually: cell0 gateway`,
            "⚠️  Service Install"
        );
    }
}

async function installLaunchAgent(
    port: number,
    token: string
): Promise<void> {
    const plistDir = path.join(os.homedir(), "Library", "LaunchAgents");
    const plistPath = path.join(plistDir, "io.cell0.gateway.plist");
    const logsDir = path.join(os.homedir(), ".cell0", "logs");

    // Ensure logs directory exists
    fs.mkdirSync(logsDir, { recursive: true });

    // Find cell0 binary
    const binPath = process.argv[1] ?? "cell0";

    const plist = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.cell0.gateway</string>
    <key>Comment</key>
    <string>Cell 0 OS Gateway (v${VERSION})</string>
    <key>ProgramArguments</key>
    <array>
        <string>${process.execPath}</string>
        <string>${binPath}</string>
        <string>gateway</string>
        <string>--port</string>
        <string>${port}</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>${os.homedir()}</string>
        <key>PATH</key>
        <string>${process.env.PATH ?? "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin"}</string>
        <key>CELL0_GATEWAY_PORT</key>
        <string>${port}</string>
        ${token ? `<key>CELL0_GATEWAY_TOKEN</key>
        <string>${token}</string>` : ""}
        <key>CELL0_LAUNCHD_LABEL</key>
        <string>io.cell0.gateway</string>
        <key>CELL0_SERVICE_MARKER</key>
        <string>cell0</string>
        <key>CELL0_SERVICE_KIND</key>
        <string>gateway</string>
        <key>CELL0_SERVICE_VERSION</key>
        <string>${VERSION}</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${path.join(os.homedir(), ".cell0", "logs", "gateway.log")}</string>
    <key>StandardErrorPath</key>
    <string>${path.join(os.homedir(), ".cell0", "logs", "gateway.err.log")}</string>
</dict>
</plist>`;

    if (!fs.existsSync(plistDir)) {
        fs.mkdirSync(plistDir, { recursive: true });
    }

    // Unload + delete stale plists before installing new one
    const { execSync } = await import("node:child_process");
    const stalePlists = [
        "com.cell0.gateway.plist",
        "com.cell0.daemon.plist",
        "io.cell0.daemon.plist",
        "com.kulluai.cell0.plist",
    ];
    for (const stale of stalePlists) {
        const stalePath = path.join(plistDir, stale);
        if (fs.existsSync(stalePath)) {
            try {
                execSync(`launchctl unload "${stalePath}" 2>/dev/null`, {
                    stdio: "ignore",
                });
            } catch {
                // Ignore unload errors
            }
            fs.unlinkSync(stalePath);
        }
    }

    fs.writeFileSync(plistPath, plist, "utf-8");

    // Load the service
    try {
        execSync(`launchctl unload "${plistPath}" 2>/dev/null`, {
            stdio: "ignore",
        });
    } catch {
        // Ignore — might not be loaded yet
    }
    execSync(`launchctl load "${plistPath}"`, { stdio: "inherit" });
}

async function installSystemdService(
    port: number,
    token: string
): Promise<void> {
    const unitDir = path.join(
        process.env.HOME ?? "~",
        ".config",
        "systemd",
        "user"
    );
    const unitPath = path.join(unitDir, "cell0-gateway.service");

    const binPath = process.argv[1] ?? "cell0";

    const unit = `[Unit]
Description=Cell 0 OS Gateway
After=network.target

[Service]
Type=simple
ExecStart=${process.execPath} ${binPath} gateway --port ${port}
Environment=CELL0_GATEWAY_TOKEN=${token}
Environment=PATH=/usr/local/bin:/usr/bin:/bin
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
`;

    if (!fs.existsSync(unitDir)) {
        fs.mkdirSync(unitDir, { recursive: true });
    }
    fs.writeFileSync(unitPath, unit, "utf-8");

    const { execSync } = await import("node:child_process");
    execSync("systemctl --user daemon-reload", { stdio: "inherit" });
    execSync("systemctl --user enable cell0-gateway.service", {
        stdio: "inherit",
    });
    execSync("systemctl --user start cell0-gateway.service", {
        stdio: "inherit",
    });
}

// ─── Health Check ─────────────────────────────────────────────────────────

async function runHealthCheck(config: Cell0Config): Promise<void> {
    const s = p.spinner();
    s.start("Running health check…");

    const port = resolveGatewayPort(config);

    // Wait briefly for daemon to start
    await new Promise((r) => setTimeout(r, 2000));

    // Try to connect to the gateway
    const isReachable = await probePort(port);

    if (isReachable) {
        s.stop("Gateway is running and healthy.");
    } else {
        s.stop("Gateway not yet reachable (start with: cell0 gateway).");
    }
}

function probePort(port: number): Promise<boolean> {
    return new Promise((resolve) => {
        const socket = new net.Socket();
        socket.setTimeout(3000);
        socket.on("connect", () => {
            socket.destroy();
            resolve(true);
        });
        socket.on("timeout", () => {
            socket.destroy();
            resolve(false);
        });
        socket.on("error", () => {
            resolve(false);
        });
        socket.connect(port, "127.0.0.1");
    });
}
