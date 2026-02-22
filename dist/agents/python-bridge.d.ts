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
import { EventEmitter } from "node:events";
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
export declare class PythonBridge extends EventEmitter {
    private config;
    private process;
    private ready;
    private baseUrl;
    private wsUrl;
    private ws;
    private heartbeatInterval;
    private pingCallbacks;
    constructor(config?: Partial<PythonBridgeConfig>);
    /** Find the correct Python interpreter */
    findPython(): string;
    /** Find the daemon script */
    findDaemon(): string;
    /** Start the Python daemon as a subprocess */
    start(): Promise<void>;
    /** Wait for the Python daemon to respond to health checks */
    private waitForReady;
    /** Connect WebSocket for real-time streaming and heartbeats */
    private connectWebSocket;
    private startHeartbeat;
    private stopHeartbeat;
    /** Broadcast an event via WebSocket to Python backend */
    sendWsMessage(msg: Record<string, unknown>): void;
    /** Check if Python backend is alive */
    isReady(): boolean;
    /** Forward a request to the Python backend */
    request<T = unknown>(method: string, path: string, body?: unknown): Promise<T>;
    /** Convenience shortcuts */
    get<T = unknown>(path: string): Promise<T>;
    post<T = unknown>(path: string, body?: unknown): Promise<T>;
    /** Get system status from Python backend */
    getStatus(): Promise<Record<string, unknown>>;
    /** Get health from Python backend */
    getHealth(): Promise<Record<string, unknown>>;
    /** Send a chat message through Python backend */
    chat(message: string, sender: string, channel?: string): Promise<Record<string, unknown>>;
    /** Run chat completions through Python backend */
    complete(messages: Array<{
        role: string;
        content: string;
    }>, model?: string): Promise<Record<string, unknown>>;
    /** Stop the Python daemon */
    stop(): Promise<void>;
    /** Get diagnostic information */
    getDiagnostics(): Record<string, unknown>;
}
//# sourceMappingURL=python-bridge.d.ts.map