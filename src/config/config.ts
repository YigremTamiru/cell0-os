/**
 * Cell 0 OS — Configuration System
 *
 * Manages the Cell 0 config file at ~/.cell0/cell0.json
 * Mirrors OpenClaw's config/config.ts pattern.
 */

import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
export const CELL0_PROJECT_ROOT = path.resolve(__dirname, "../../");

// ─── Paths ────────────────────────────────────────────────────────────────

export const CELL0_HOME = path.join(os.homedir(), ".cell0");
export const CONFIG_PATH = path.join(CELL0_HOME, "cell0.json");

export const CELL0_PATHS = {
    home: CELL0_HOME,
    config: CONFIG_PATH,
    identity: {
        root: path.join(CELL0_HOME, "identity"),
        keys: path.join(CELL0_HOME, "identity", "keys"),
        certs: path.join(CELL0_HOME, "identity", "certs"),
    },
    workspace: {
        root: path.join(CELL0_HOME, "workspace"),
        agents: path.join(CELL0_HOME, "workspace", "agents"),
        skills: path.join(CELL0_HOME, "workspace", "skills"),
        data: path.join(CELL0_HOME, "workspace", "data"),
    },
    runtime: {
        root: path.join(CELL0_HOME, "runtime"),
        sessions: path.join(CELL0_HOME, "runtime", "sessions"),
        logs: path.join(CELL0_HOME, "runtime", "logs"),
        cron: path.join(CELL0_HOME, "runtime", "cron"),
        pids: path.join(CELL0_HOME, "runtime", "pids"),
        memory: path.join(CELL0_HOME, "runtime", "memory"),
    },
    snapshots: path.join(CELL0_HOME, "snapshots"),
    // ─── Agent Library (Phase 3B) ─────────────────────────────────────────
    library: {
        root: path.join(CELL0_HOME, "library"),
        manifest: path.join(CELL0_HOME, "library", "manifest.json"),
        categories: path.join(CELL0_HOME, "library", "categories"),
    },
    workspaces: path.join(CELL0_HOME, "workspaces"),
    credentials: path.join(CELL0_HOME, "credentials"),
    canvas: path.join(CELL0_HOME, "canvas"),
    kernel: {
        root: path.join(CELL0_HOME, "kernel"),
        policies: path.join(CELL0_HOME, "kernel", "policies"),
    },
};

export const DEFAULT_WORKSPACE = CELL0_PATHS.workspace.root;
export const DEFAULT_GATEWAY_PORT = 18789;
export const DEFAULT_PORTAL_PORT = 18790;
export const DEFAULT_PYTHON_PORT = 18800;

// ─── Types ────────────────────────────────────────────────────────────────

export interface IdentityConfig {
    ipv4?: string;
    ipv6?: string;
    publicKey?: string;
}

export interface RuntimeConfig {
    logLevel?: "debug" | "info" | "warn" | "error";
    maxLogSize?: number;
}

export interface GatewayAuthConfig {
    mode: "token" | "password" | "none";
    token?: string;
    password?: string;
}

export interface GatewayTailscaleConfig {
    mode: "off" | "serve" | "funnel";
    resetOnExit?: boolean;
}

export interface GatewayConfig {
    port?: number;
    bind?: "loopback" | "lan" | "auto" | "custom" | "tailnet";
    customBindHost?: string;
    auth?: GatewayAuthConfig;
    tailscale?: GatewayTailscaleConfig;
    controlUi?: {
        enabled?: boolean;
        basePath?: string;
    };
    remote?: {
        url?: string;
        token?: string;
    };
}

export interface AgentConfig {
    model?: string;
    provider?: string;
    apiKey?: string;
    baseUrl?: string;
    workspace?: string;
    sandbox?: {
        mode?: "off" | "non-main";
    };
}

export interface AgentsConfig {
    defaults?: AgentConfig;
    list?: Array<{
        name: string;
        workspace?: string;
        agentDir?: string;
        model?: string;
    }>;
}

export interface ChannelConfig {
    enabled?: boolean;
    dmPolicy?: "pairing" | "open";
    allowFrom?: string[];
    [key: string]: unknown;
}

export interface ChannelsConfig {
    whatsapp?: ChannelConfig;
    telegram?: ChannelConfig;
    discord?: ChannelConfig;
    slack?: ChannelConfig;
    signal?: ChannelConfig;
    googlechat?: ChannelConfig;
    bluebubbles?: ChannelConfig;
    imessage?: ChannelConfig;
    msteams?: ChannelConfig;
    matrix?: ChannelConfig;
    webchat?: ChannelConfig;
    [key: string]: ChannelConfig | undefined;
}

export interface Cell0Config {
    agent?: {
        model?: string;
        provider?: string;
        apiKey?: string;
        baseUrl?: string;
    };
    identity?: IdentityConfig;
    runtime?: RuntimeConfig;
    gateway?: GatewayConfig;
    agents?: AgentsConfig;
    channels?: ChannelsConfig;
    meta?: {
        wizard?: string;
        version?: string;
        lastModified?: string;
    };
}

// ─── Config Snapshot ──────────────────────────────────────────────────────

export interface ConfigSnapshot {
    exists: boolean;
    valid: boolean;
    config: Cell0Config;
    issues: Array<{ path: string; message: string }>;
    raw?: string;
}

// ─── Read/Write ───────────────────────────────────────────────────────────

export function ensureConfigDir(): void {
    if (!fs.existsSync(CELL0_HOME)) {
        fs.mkdirSync(CELL0_HOME, { recursive: true });
    }
}

// ─── Backup ───────────────────────────────────────────────────────────────

const SNAPSHOTS_DIR = CELL0_PATHS.snapshots;

function backupConfig(): void {
    if (!fs.existsSync(CONFIG_PATH)) return;
    if (!fs.existsSync(SNAPSHOTS_DIR)) {
        fs.mkdirSync(SNAPSHOTS_DIR, { recursive: true });
    }
    const ts = new Date().toISOString().replace(/:/g, "-").replace(/\./g, "-");
    const backupPath = path.join(SNAPSHOTS_DIR, `cell0.json.bak.${ts}`);
    fs.copyFileSync(CONFIG_PATH, backupPath);

    // Prune: keep only the 5 most recent backups
    const backups = fs
        .readdirSync(SNAPSHOTS_DIR)
        .filter((f) => f.startsWith("cell0.json.bak."))
        .sort()
        .reverse();
    for (const old of backups.slice(5)) {
        fs.unlinkSync(path.join(SNAPSHOTS_DIR, old));
    }
}

export function listConfigBackups(): Array<{ file: string; path: string; mtime: Date; size: number }> {
    if (!fs.existsSync(SNAPSHOTS_DIR)) return [];
    return fs
        .readdirSync(SNAPSHOTS_DIR)
        .filter((f) => f.startsWith("cell0.json.bak."))
        .sort()
        .reverse()
        .map((f) => {
            const p = path.join(SNAPSHOTS_DIR, f);
            const stat = fs.statSync(p);
            return { file: f, path: p, mtime: stat.mtime, size: stat.size };
        });
}

export function restoreConfigBackup(backupPath: string): void {
    if (!fs.existsSync(backupPath)) {
        throw new Error(`Backup not found: ${backupPath}`);
    }
    // Backup current before restoring
    backupConfig();
    fs.copyFileSync(backupPath, CONFIG_PATH);
}

export function readConfigFileSnapshot(): ConfigSnapshot {
    ensureConfigDir();

    if (!fs.existsSync(CONFIG_PATH)) {
        return { exists: false, valid: true, config: {}, issues: [] };
    }

    try {
        const raw = fs.readFileSync(CONFIG_PATH, "utf-8");
        const config = JSON.parse(raw) as Cell0Config;
        const issues = validateConfig(config);
        return {
            exists: true,
            valid: issues.length === 0,
            config,
            issues,
            raw,
        };
    } catch (err) {
        return {
            exists: true,
            valid: false,
            config: {},
            issues: [
                {
                    path: "root",
                    message:
                        err instanceof Error
                            ? `Parse error: ${err.message}`
                            : "Unknown parse error",
                },
            ],
        };
    }
}

export function writeConfig(config: Cell0Config): void {
    ensureConfigDir();
    backupConfig();

    // Update metadata
    config.meta = {
        ...config.meta,
        version: "1.2.0",
        lastModified: new Date().toISOString(),
    };

    const json = JSON.stringify(config, null, 2);
    fs.writeFileSync(CONFIG_PATH, json + "\n", "utf-8");
}

// ─── Resolution Helpers ───────────────────────────────────────────────────

export function resolveGatewayPort(config?: Cell0Config | null): number {
    return config?.gateway?.port ?? DEFAULT_GATEWAY_PORT;
}

export function resolveWorkspace(config?: Cell0Config | null): string {
    const ws =
        config?.agents?.defaults?.workspace ?? DEFAULT_WORKSPACE;
    return resolveUserPath(ws);
}

export function resolveUserPath(p: string): string {
    if (p.startsWith("~/")) {
        return path.join(os.homedir(), p.slice(2));
    }
    return path.resolve(p);
}

// ─── Validation ───────────────────────────────────────────────────────────

function validateConfig(
    config: Cell0Config
): Array<{ path: string; message: string }> {
    const issues: Array<{ path: string; message: string }> = [];

    if (
        config.gateway?.port !== undefined &&
        (typeof config.gateway.port !== "number" ||
            config.gateway.port < 1 ||
            config.gateway.port > 65535)
    ) {
        issues.push({
            path: "gateway.port",
            message: "Must be a number between 1 and 65535",
        });
    }

    if (
        config.gateway?.bind !== undefined &&
        !["loopback", "lan", "auto", "custom", "tailnet"].includes(
            config.gateway.bind
        )
    ) {
        issues.push({
            path: "gateway.bind",
            message:
                'Must be one of: loopback, lan, auto, custom, tailnet',
        });
    }

    if (
        config.gateway?.auth?.mode !== undefined &&
        !["token", "password", "none"].includes(config.gateway.auth.mode)
    ) {
        issues.push({
            path: "gateway.auth.mode",
            message: "Must be one of: token, password, none",
        });
    }

    return issues;
}

// ─── Config Summary ───────────────────────────────────────────────────────

export function summarizeConfig(config: Cell0Config): string {
    const lines: string[] = [];

    if (config.agent?.model) {
        lines.push(`Model: ${config.agent.model}`);
    }
    if (config.gateway?.port) {
        lines.push(`Gateway port: ${config.gateway.port}`);
    }
    if (config.gateway?.bind) {
        lines.push(`Gateway bind: ${config.gateway.bind}`);
    }
    if (config.gateway?.auth?.mode) {
        lines.push(`Gateway auth: ${config.gateway.auth.mode}`);
    }
    if (config.agents?.defaults?.workspace) {
        lines.push(`Workspace: ${config.agents.defaults.workspace}`);
    }

    const channelNames = config.channels
        ? Object.keys(config.channels).filter(
            (k) => config.channels![k]?.enabled
        )
        : [];
    if (channelNames.length > 0) {
        lines.push(`Channels: ${channelNames.join(", ")}`);
    }

    return lines.length > 0
        ? lines.join("\n")
        : "Empty configuration";
}
