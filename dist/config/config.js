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
// ─── Read/Write ───────────────────────────────────────────────────────────
export function ensureConfigDir() {
    if (!fs.existsSync(CELL0_HOME)) {
        fs.mkdirSync(CELL0_HOME, { recursive: true });
    }
}
export function readConfigFileSnapshot() {
    ensureConfigDir();
    if (!fs.existsSync(CONFIG_PATH)) {
        return { exists: false, valid: true, config: {}, issues: [] };
    }
    try {
        const raw = fs.readFileSync(CONFIG_PATH, "utf-8");
        const config = JSON.parse(raw);
        const issues = validateConfig(config);
        return {
            exists: true,
            valid: issues.length === 0,
            config,
            issues,
            raw,
        };
    }
    catch (err) {
        return {
            exists: true,
            valid: false,
            config: {},
            issues: [
                {
                    path: "root",
                    message: err instanceof Error
                        ? `Parse error: ${err.message}`
                        : "Unknown parse error",
                },
            ],
        };
    }
}
export function writeConfig(config) {
    ensureConfigDir();
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
export function resolveGatewayPort(config) {
    return config?.gateway?.port ?? DEFAULT_GATEWAY_PORT;
}
export function resolveWorkspace(config) {
    const ws = config?.agents?.defaults?.workspace ?? DEFAULT_WORKSPACE;
    return resolveUserPath(ws);
}
export function resolveUserPath(p) {
    if (p.startsWith("~/")) {
        return path.join(os.homedir(), p.slice(2));
    }
    return path.resolve(p);
}
// ─── Validation ───────────────────────────────────────────────────────────
function validateConfig(config) {
    const issues = [];
    if (config.gateway?.port !== undefined &&
        (typeof config.gateway.port !== "number" ||
            config.gateway.port < 1 ||
            config.gateway.port > 65535)) {
        issues.push({
            path: "gateway.port",
            message: "Must be a number between 1 and 65535",
        });
    }
    if (config.gateway?.bind !== undefined &&
        !["loopback", "lan", "auto", "custom", "tailnet"].includes(config.gateway.bind)) {
        issues.push({
            path: "gateway.bind",
            message: 'Must be one of: loopback, lan, auto, custom, tailnet',
        });
    }
    if (config.gateway?.auth?.mode !== undefined &&
        !["token", "password", "none"].includes(config.gateway.auth.mode)) {
        issues.push({
            path: "gateway.auth.mode",
            message: "Must be one of: token, password, none",
        });
    }
    return issues;
}
// ─── Config Summary ───────────────────────────────────────────────────────
export function summarizeConfig(config) {
    const lines = [];
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
        ? Object.keys(config.channels).filter((k) => config.channels[k]?.enabled)
        : [];
    if (channelNames.length > 0) {
        lines.push(`Channels: ${channelNames.join(", ")}`);
    }
    return lines.length > 0
        ? lines.join("\n")
        : "Empty configuration";
}
//# sourceMappingURL=config.js.map