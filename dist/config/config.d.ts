/**
 * Cell 0 OS — Configuration System
 *
 * Manages the Cell 0 config file at ~/.cell0/cell0.json
 * Mirrors OpenClaw's config/config.ts pattern.
 */
export declare const CELL0_PROJECT_ROOT: string;
export declare const CELL0_HOME: string;
export declare const CONFIG_PATH: string;
export declare const CELL0_PATHS: {
    home: string;
    config: string;
    identity: {
        root: string;
        keys: string;
        certs: string;
    };
    workspace: {
        root: string;
        agents: string;
        skills: string;
        data: string;
    };
    runtime: {
        root: string;
        sessions: string;
        logs: string;
        cron: string;
        pids: string;
        memory: string;
    };
    snapshots: string;
    library: {
        root: string;
        manifest: string;
        categories: string;
    };
    workspaces: string;
    credentials: string;
    canvas: string;
    kernel: {
        root: string;
        policies: string;
    };
};
export declare const DEFAULT_WORKSPACE: string;
export declare const DEFAULT_GATEWAY_PORT = 18789;
export declare const DEFAULT_PORTAL_PORT = 18790;
export declare const DEFAULT_PYTHON_PORT = 18800;
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
export interface ConfigSnapshot {
    exists: boolean;
    valid: boolean;
    config: Cell0Config;
    issues: Array<{
        path: string;
        message: string;
    }>;
    raw?: string;
}
export declare function ensureConfigDir(): void;
export declare function listConfigBackups(): Array<{
    file: string;
    path: string;
    mtime: Date;
    size: number;
}>;
export declare function restoreConfigBackup(backupPath: string): void;
export declare function readConfigFileSnapshot(): ConfigSnapshot;
export declare function writeConfig(config: Cell0Config): void;
export declare function resolveGatewayPort(config?: Cell0Config | null): number;
export declare function resolveWorkspace(config?: Cell0Config | null): string;
export declare function resolveUserPath(p: string): string;
export declare function summarizeConfig(config: Cell0Config): string;
//# sourceMappingURL=config.d.ts.map