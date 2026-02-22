/**
 * Cell 0 OS — WebSocket Gateway
 *
 * Main gateway daemon entry point. This is the OpenClaw-equivalent
 * core service. It provides:
 *
 * 1. WebSocket server with typed wire protocol (port 18789)
 * 2. HTTP server on same port (health, WebChat, Canvas, static)
 * 3. Python bridge to Cell 0 backend (COL, agents, inference)
 * 4. Session management with multi-agent routing
 * 5. Device pairing for DM security
 *
 * Architecture:
 *   Client ←→ [WS Gateway :18789] ←→ [Python Bridge] ←→ [cell0d :18800]
 */
export interface GatewayConfig {
    port: number;
    host: string;
    pythonPort: number;
    projectRoot: string;
    autoStartPython: boolean;
    logLevel: string;
    verbose: boolean;
}
export declare class Gateway {
    private config;
    private sessions;
    private python;
    private clients;
    private idempotencyCache;
    private fastify;
    private eventSeq;
    private router;
    private adapters;
    constructor(config?: Partial<GatewayConfig>);
    private registerAdapters;
    start(): Promise<void>;
    private setupHttpRoutes;
    private setupWebSocket;
    private handleFrame;
    private handleConnect;
    private handleRequest;
    private routeMethod;
    private proxyToPython;
    private sendToClient;
    private broadcastEvent;
    stop(): Promise<void>;
}
//# sourceMappingURL=index.d.ts.map