/**
 * Cell 0 OS — Python Bridge
 *
 * Bridges the TypeScript gateway to the Cell 0 Python backend.
 * Spawns the Python daemon as a subprocess and communicates
 * via HTTP (localhost) or JSON-RPC over stdio.
 *
 * This is the hybrid approach: TypeScript handles the gateway
 * protocol, sessions, channels, and CLI. Python handles the
 * COL orchestrator, agent coordination, and AI inference.
 */

import { spawn, type ChildProcess } from "node:child_process";
import { existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { homedir } from "node:os";
import { EventEmitter } from "node:events";
import WebSocket from "ws";

export interface PythonBridgeConfig {
    /** Path to Python project root (where cell0d.py lives) */
    projectRoot: string;
    /** HTTP port the Python daemon listens on */
    pythonPort: number;
    /** Whether to auto-start Python daemon */
    autoStart: boolean;
    /** Log level for Python daemon */
    logLevel: string;
}

const DEFAULT_CONFIG: PythonBridgeConfig = {
    projectRoot: resolve(join(homedir(), "cell0")),
    pythonPort: 18800,
    autoStart: true,
    logLevel: "INFO",
};

export class PythonBridge extends EventEmitter {
    private config: PythonBridgeConfig;
    private process: ChildProcess | null = null;
    private ready = false;
    private baseUrl: string;
    private wsUrl: string;
    private ws: WebSocket | null = null;
    private heartbeatInterval: NodeJS.Timeout | null = null;
    private pingCallbacks: Map<number, (time: number) => void> = new Map();

    constructor(config?: Partial<PythonBridgeConfig>) {
        super();
        this.config = { ...DEFAULT_CONFIG, ...config };
        this.baseUrl = `http://127.0.0.1:${this.config.pythonPort}`;
        this.wsUrl = `ws://127.0.0.1:${this.config.pythonPort}`;
    }

    /** Find the correct Python interpreter */
    findPython(): string {
        const root = this.config.projectRoot;
        const candidates = [
            join(root, ".venv", "bin", "python3"),
            join(root, "venv", "bin", "python3"),
            join(homedir(), ".cell0", "venv", "bin", "python3"),
            join(homedir(), ".cell0", ".venv", "bin", "python3"),
        ];

        for (const p of candidates) {
            if (existsSync(p)) return p;
        }

        // Fall back to system Python
        return "python3";
    }

    /** Find the daemon script */
    findDaemon(): string {
        const root = this.config.projectRoot;
        const candidates = [
            join(root, "cell0", "cell0d.py"),
            join(root, "cell0d.py"),
            join(root, "service", "cell0d.py"),
        ];

        for (const p of candidates) {
            if (existsSync(p)) return p;
        }

        throw new Error(
            `Cannot find cell0d.py daemon script. Searched in: ${candidates.join(", ")}`
        );
    }

    /** Start the Python daemon as a subprocess */
    async start(): Promise<void> {
        if (this.process) {
            console.log("[python-bridge] Python daemon already running");
            return;
        }

        const python = this.findPython();
        const daemon = this.findDaemon();

        console.log(`[python-bridge] Starting Python daemon: ${python} ${daemon}`);

        const env = {
            ...process.env,
            CELL0_PORT: String(this.config.pythonPort),
            CELL0_ENV: "production",
            CELL0_LOG_LEVEL: this.config.logLevel,
            PYTHONPATH: this.config.projectRoot,
        };

        this.process = spawn(python, [daemon], {
            cwd: this.config.projectRoot,
            env,
            stdio: ["pipe", "pipe", "pipe"],
        });

        this.process.stdout?.on("data", (data: Buffer) => {
            const msg = data.toString().trim();
            if (msg) console.log(`[python] ${msg}`);
        });

        this.process.stderr?.on("data", (data: Buffer) => {
            const msg = data.toString().trim();
            if (msg) console.error(`[python:err] ${msg}`);
        });

        this.process.on("close", (code) => {
            console.log(`[python-bridge] Python daemon exited with code ${code}`);
            this.process = null;
            this.ready = false;
        });

        // Wait for the daemon to become ready
        await this.waitForReady();
    }

    /** Wait for the Python daemon to respond to health checks */
    private async waitForReady(
        maxRetries = 30,
        intervalMs = 1000
    ): Promise<void> {
        for (let i = 0; i < maxRetries; i++) {
            try {
                const res = await fetch(`${this.baseUrl}/health`);
                if (res.ok) {
                    this.ready = true;
                    console.log("[python-bridge] Python daemon (HTTP) is ready");
                    await this.connectWebSocket();
                    return;
                }
            } catch {
                // Not ready yet
            }
            await new Promise((r) => setTimeout(r, intervalMs));
        }
        throw new Error(
            `Python daemon did not become ready after ${maxRetries * intervalMs}ms`
        );
    }

    /** Connect WebSocket for real-time streaming and heartbeats */
    private async connectWebSocket(): Promise<void> {
        return new Promise((resolve, reject) => {
            console.log(`[python-bridge] Connecting WebSocket to ${this.wsUrl}/ws/agents/node-gateway`);
            this.ws = new WebSocket(`${this.wsUrl}/ws/agents/node-gateway`);

            this.ws.on("open", () => {
                console.log("[python-bridge] WebSocket connected");
                this.startHeartbeat();
                resolve();
            });

            this.ws.on("message", (data) => {
                try {
                    const msg = JSON.parse(data.toString());
                    if (msg.type === "pong") {
                        // Handle heartbeat pong
                        const cb = this.pingCallbacks.get(msg.seq || 0);
                        if (cb) {
                            cb(Date.now());
                            this.pingCallbacks.delete(msg.seq || 0);
                        }
                    } else {
                        // Emit other messages for the runtime to handle (streams, agent events)
                        this.emit("message", msg);
                    }
                } catch (e) {
                    console.error("[python-bridge] Error parsing WS message", e);
                }
            });

            this.ws.on("error", (err) => {
                console.error("[python-bridge] WebSocket error:", err);
                reject(err);
            });

            this.ws.on("close", () => {
                console.log("[python-bridge] WebSocket closed");
                this.stopHeartbeat();
                this.ws = null;
            });
        });
    }

    private startHeartbeat() {
        if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
        let seq = 0;
        this.heartbeatInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                const currentSeq = ++seq;
                this.pingCallbacks.set(currentSeq, (time) => {
                    // console.debug(`[python-bridge] Heartbeat latency: ${Date.now() - time}ms`);
                });
                this.ws.send(JSON.stringify({ type: "ping", seq: currentSeq, timestamp: Date.now() }));
            }
        }, 10000);
    }

    private stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    /** Broadcast an event via WebSocket to Python backend */
    sendWsMessage(msg: Record<string, unknown>) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(msg));
        } else {
            throw new Error("Python WebSocket not connected");
        }
    }

    /** Check if Python backend is alive */
    isReady(): boolean {
        return this.ready && this.process !== null && this.ws !== null && this.ws.readyState === WebSocket.OPEN;
    }

    /** Forward a request to the Python backend */
    async request<T = unknown>(
        method: string,
        path: string,
        body?: unknown
    ): Promise<T> {
        const url = `${this.baseUrl}${path}`;
        const opts: RequestInit = {
            method,
            headers: { "Content-Type": "application/json" },
        };

        if (body && method !== "GET") {
            opts.body = JSON.stringify(body);
        }

        const res = await fetch(url, opts);
        if (!res.ok) {
            const err = await res.text();
            throw new Error(`Python backend error (${res.status}): ${err}`);
        }

        return res.json() as Promise<T>;
    }

    /** Convenience shortcuts */
    async get<T = unknown>(path: string): Promise<T> {
        return this.request<T>("GET", path);
    }

    async post<T = unknown>(path: string, body?: unknown): Promise<T> {
        return this.request<T>("POST", path, body);
    }

    /** Get system status from Python backend */
    async getStatus(): Promise<Record<string, unknown>> {
        return this.get("/api/system/status");
    }

    /** Get health from Python backend */
    async getHealth(): Promise<Record<string, unknown>> {
        return this.get("/api/system/health");
    }

    /** Send a chat message through Python backend */
    async chat(
        message: string,
        sender: string,
        channel = "general"
    ): Promise<Record<string, unknown>> {
        return this.post("/api/chat/messages", { message, sender, channel });
    }

    /** Run chat completions through Python backend */
    async complete(
        messages: Array<{ role: string; content: string }>,
        model = "default"
    ): Promise<Record<string, unknown>> {
        return this.post("/api/chat/completions", { model, messages });
    }

    /** Stop the Python daemon */
    async stop(): Promise<void> {
        this.stopHeartbeat();
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }

        if (this.process) {
            console.log("[python-bridge] Stopping Python daemon...");
            this.process.kill("SIGTERM");

            // Wait for graceful shutdown
            await new Promise<void>((resolve) => {
                const timeout = setTimeout(() => {
                    this.process?.kill("SIGKILL");
                    resolve();
                }, 5000);

                this.process?.on("close", () => {
                    clearTimeout(timeout);
                    resolve();
                });
            });

            this.process = null;
            this.ready = false;
        }
    }

    /** Get diagnostic information */
    getDiagnostics(): Record<string, unknown> {
        return {
            pythonPath: this.findPython(),
            daemonPath: (() => { try { return this.findDaemon(); } catch { return "NOT FOUND"; } })(),
            port: this.config.pythonPort,
            running: this.process !== null,
            ready: this.ready,
            pid: this.process?.pid,
        };
    }
}
