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

import Fastify from "fastify";
import fastifyWebsocket from "@fastify/websocket";
import fastifyCors from "@fastify/cors";
import { type WebSocket } from "ws";
import { randomUUID } from "node:crypto";

import {
    type RequestFrame,
    type ConnectFrame,
    type EventFrame,
    type ResponseFrame,
    makeResponse,
    makeError,
    makeEvent,
} from "./protocol.js";
import { SessionManager, type ChatMessage } from "./sessions.js";
import { PythonBridge, type PythonBridgeConfig } from "../agents/python-bridge.js";

// Channels and Routing
import { ChannelAdapter } from "../channels/adapter.js";
import { DomainRouter } from "./router.js";
import { WhatsAppAdapter } from "../channels/whatsapp.js";
import { TelegramAdapter } from "../channels/telegram.js";
import { DiscordAdapter } from "../channels/discord.js";
import { SlackAdapter } from "../channels/slack.js";
import { SignalAdapter } from "../channels/signal.js";
import { GoogleChatAdapter } from "../channels/google-chat.js";
import { MSTeamsAdapter } from "../channels/msteams.js";
import { IMessageAdapter } from "../channels/imessage.js";
import { BlueBubblesAdapter } from "../channels/bluebubbles.js";
import { MatrixAdapter } from "../channels/matrix.js";
import { WebChatAdapter } from "../channels/webchat.js";

// ─── Configuration ──────────────────────────────────────────────────────────

export interface GatewayConfig {
    port: number;
    host: string;
    pythonPort: number;
    projectRoot: string;
    autoStartPython: boolean;
    logLevel: string;
    verbose: boolean;
}

const DEFAULT_GATEWAY_CONFIG: GatewayConfig = {
    port: 18789,
    host: "127.0.0.1",
    pythonPort: 18800,
    projectRoot: process.cwd(),
    autoStartPython: true,
    logLevel: "info",
    verbose: false,
};

// ─── Client Connection ─────────────────────────────────────────────────────

interface ClientConnection {
    id: string;
    ws: WebSocket;
    deviceId?: string;
    deviceName?: string;
    authenticated: boolean;
    sessionId: string;
    connectedAt: string;
    seq: number;
}

// ─── Gateway Class ──────────────────────────────────────────────────────────

export class Gateway {
    private config: GatewayConfig;
    private sessions: SessionManager;
    private python: PythonBridge;
    private clients = new Map<string, ClientConnection>();
    private idempotencyCache = new Map<string, ResponseFrame>();
    private fastify = Fastify({ logger: false });
    private eventSeq = 0;

    // Phase 4: Channels & Routing
    private router: DomainRouter;
    private adapters: Map<string, ChannelAdapter> = new Map();

    constructor(config?: Partial<GatewayConfig>) {
        this.config = { ...DEFAULT_GATEWAY_CONFIG, ...config };
        this.sessions = new SessionManager();
        this.python = new PythonBridge({
            projectRoot: this.config.projectRoot,
            pythonPort: this.config.pythonPort,
            autoStart: this.config.autoStartPython,
            logLevel: this.config.logLevel,
        });

        // Initialize Router and all 11 Adapters
        this.router = new DomainRouter();
        this.registerAdapters([
            new WhatsAppAdapter(),
            new TelegramAdapter(),
            new DiscordAdapter(),
            new SlackAdapter(),
            new SignalAdapter(),
            new GoogleChatAdapter(),
            new MSTeamsAdapter(),
            new IMessageAdapter(),
            new BlueBubblesAdapter(),
            new MatrixAdapter(),
            new WebChatAdapter()
        ]);
    }

    private registerAdapters(adapterList: ChannelAdapter[]) {
        for (const adapter of adapterList) {
            this.adapters.set(adapter.id, adapter);

            adapter.on('message', async (msg) => {
                // Route message to correct domain session
                const decision = await this.router.route(msg, adapter.defaultDomain);
                const session = this.sessions.getOrCreateDomainSession(decision.domain);

                // Add to session history
                const chatMsg = this.sessions.addMessage(session.id, {
                    role: "user",
                    content: msg.text,
                    sender: msg.senderId,
                    channel: msg.channelId,
                    metadata: {
                        isEncrypted: msg.isEncrypted,
                        intent: decision.intent
                    }
                });

                // Broadcast to all active portal/web clients for real-time Nerve Map / Chat UI updates
                this.broadcastEvent("chat.inbound", {
                    sessionId: session.id,
                    domain: decision.domain,
                    message: chatMsg
                });

                // Future: Pipe directly to Python backend for AI response generation
            });

            adapter.on('error', (err) => {
                console.error(`[Adapter Error] ${adapter.id}:`, err);
            });
        }
    }

    async start(): Promise<void> {
        console.log(`\n🧬 Cell 0 OS Gateway v1.2.0`);
        console.log(`   Port: ${this.config.port}`);
        console.log(`   Host: ${this.config.host}`);
        console.log(`   Python backend: 127.0.0.1:${this.config.pythonPort}`);
        console.log();

        // Register plugins
        await this.fastify.register(fastifyCors, { origin: true });
        await this.fastify.register(fastifyWebsocket);

        // HTTP routes
        this.setupHttpRoutes();

        // WebSocket handler
        this.setupWebSocket();

        // Start Python backend
        if (this.config.autoStartPython) {
            try {
                await this.python.start();
            } catch (err) {
                console.warn(`⚠️  Python backend failed to start: ${err}`);
                console.warn("   Gateway will run in standalone mode.");
            }
        }

        // Connect all 11 Channel Adapters
        console.log(`\n🔌 Connecting ${this.adapters.size} Channel Adapters...`);
        for (const adapter of this.adapters.values()) {
            try {
                await adapter.connect();
                console.log(`   [OK] ${adapter.id} connected (${adapter.defaultDomain})`);
            } catch (err) {
                console.warn(`   [FAIL] ${adapter.id} failed to connect: ${err}`);
            }
        }

        // Start listening
        await this.fastify.listen({
            port: this.config.port,
            host: this.config.host,
        });

        console.log(`\n✅ Gateway ready`);
        console.log(`   WebSocket: ws://${this.config.host}:${this.config.port}`);
        console.log(`   HTTP:      http://${this.config.host}:${this.config.port}`);
        console.log(`   Health:    http://${this.config.host}:${this.config.port}/health`);
        console.log(`   Docs:      http://${this.config.host}:${this.config.port}/docs`);
        console.log();

        // Emit heartbeat every 30 seconds
        setInterval(() => this.broadcastEvent("gateway.heartbeat", {
            uptime: process.uptime(),
            clients: this.clients.size,
            sessions: this.sessions.listSessions().length,
        }), 30_000);
    }

    // ─── HTTP Routes ────────────────────────────────────────────────────────

    private setupHttpRoutes(): void {
        // Health check (public)
        this.fastify.get("/health", async () => ({
            status: "healthy",
            version: "1.2.0",
            gateway: true,
            python: this.python.isReady(),
            clients: this.clients.size,
            sessions: this.sessions.listSessions().length,
            timestamp: new Date().toISOString(),
        }));

        // API Health check (detailed)
        this.fastify.get("/api/health", async () => ({
            status: "healthy",
            version: "1.2.0",
            components: {
                gateway: "ok",
                python_bridge: this.python.isReady() ? "ok" : "degraded",
                channels: Array.from(this.adapters.keys())
            },
            metrics: {
                clients_connected: this.clients.size,
                active_sessions: this.sessions.listSessions().length,
                uptime_seconds: Math.floor(process.uptime()),
            },
            timestamp: new Date().toISOString(),
        }));

        // API status
        this.fastify.get("/api/status", async () => {
            const pythonStatus = this.python.isReady()
                ? await this.python.getStatus().catch(() => ({ error: "unreachable" }))
                : { error: "not started" };

            return {
                gateway: {
                    version: "1.2.0",
                    uptime: process.uptime(),
                    clients: this.clients.size,
                    sessions: this.sessions.listSessions().length,
                },
                python: pythonStatus,
            };
        });

        // Docs (simple JSON description of the API)
        this.fastify.get("/docs", async () => ({
            name: "Cell 0 OS Gateway",
            version: "1.2.0",
            protocol: "WebSocket + HTTP",
            ws: `ws://${this.config.host}:${this.config.port}`,
            endpoints: {
                "GET /health": "Health check",
                "GET /api/status": "System status",
                "GET /docs": "This documentation",
                "WS /": "WebSocket gateway (wire protocol)",
            },
        }));
    }

    // ─── WebSocket Handler ──────────────────────────────────────────────────

    private setupWebSocket(): void {
        this.fastify.register(async (app) => {
            app.get("/", { websocket: true }, (socket) => {
                const clientId = randomUUID();
                const mainSession = this.sessions.getMainSession();

                const client: ClientConnection = {
                    id: clientId,
                    ws: socket as unknown as WebSocket,
                    authenticated: false,
                    sessionId: mainSession.id,
                    connectedAt: new Date().toISOString(),
                    seq: 0,
                };

                this.clients.set(clientId, client);
                console.log(`[ws] Client connected: ${clientId}`);

                // Send welcome
                this.sendToClient(client, makeEvent("gateway.ready", {
                    gatewayVersion: "1.2.0",
                    sessionId: mainSession.id,
                    features: {
                        python: this.python.isReady(),
                        sessions: true,
                        streaming: true,
                    },
                }));

                // Handle messages
                socket.on("message", async (data: Buffer) => {
                    try {
                        const raw = data.toString();
                        const frame = JSON.parse(raw);
                        await this.handleFrame(client, frame);
                    } catch (err) {
                        console.error(`[ws] Error handling message from ${clientId}:`, err);
                    }
                });

                socket.on("close", () => {
                    this.clients.delete(clientId);
                    console.log(`[ws] Client disconnected: ${clientId}`);
                });

                socket.on("error", (err) => {
                    console.error(`[ws] Socket error for ${clientId}:`, err.message);
                });
            });
        });
    }

    // ─── Frame Handler ──────────────────────────────────────────────────────

    private async handleFrame(
        client: ClientConnection,
        frame: Record<string, unknown>
    ): Promise<void> {
        const type = frame.type as string;

        switch (type) {
            case "connect":
                await this.handleConnect(client, frame as unknown as ConnectFrame);
                break;
            case "req":
                await this.handleRequest(client, frame as unknown as RequestFrame);
                break;
            default:
                this.sendToClient(client, makeError(
                    (frame.id as string) ?? "unknown",
                    "INVALID_FRAME",
                    `Unknown frame type: ${type}`
                ));
        }
    }

    private async handleConnect(
        client: ClientConnection,
        frame: ConnectFrame
    ): Promise<void> {
        // For loopback connections, auto-authenticate
        client.authenticated = true;
        client.deviceId = frame.deviceId;
        client.deviceName = frame.deviceName;

        this.sendToClient(client, makeEvent("gateway.ready", {
            authenticated: true,
            sessionId: client.sessionId,
            devicePaired: true,
        }));
    }

    private async handleRequest(
        client: ClientConnection,
        frame: RequestFrame
    ): Promise<void> {
        // Idempotency check
        if (frame.idempotencyKey) {
            const cached = this.idempotencyCache.get(frame.idempotencyKey);
            if (cached) {
                this.sendToClient(client, { ...cached, id: frame.id });
                return;
            }
        }

        let response: ResponseFrame;

        try {
            response = await this.routeMethod(client, frame);
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            response = makeError(frame.id, "INTERNAL_ERROR", message);
        }

        // Cache idempotent responses
        if (frame.idempotencyKey && response.ok) {
            this.idempotencyCache.set(frame.idempotencyKey, response);
            // Evict cache entries after 5 minutes
            setTimeout(() => this.idempotencyCache.delete(frame.idempotencyKey!), 300_000);
        }

        this.sendToClient(client, response);
    }

    // ─── Method Router ──────────────────────────────────────────────────────

    private async routeMethod(
        client: ClientConnection,
        frame: RequestFrame
    ): Promise<ResponseFrame> {
        const params = (frame.params ?? {}) as Record<string, unknown>;

        switch (frame.method) {
            // Session methods
            case "session.create": {
                const session = this.sessions.createSession("group", {
                    channelId: params.channelId as string,
                    agentId: params.agentId as string,
                    metadata: params.metadata as Record<string, unknown>,
                });
                return makeResponse(frame.id, session);
            }

            case "session.list":
                return makeResponse(frame.id, this.sessions.listSessions());

            case "session.get": {
                const session = this.sessions.getSession(params.sessionId as string);
                if (!session) return makeError(frame.id, "NOT_FOUND", "Session not found");
                return makeResponse(frame.id, session);
            }

            case "session.delete": {
                const deleted = this.sessions.deleteSession(params.sessionId as string);
                return makeResponse(frame.id, { deleted });
            }

            // Chat methods
            case "chat.send": {
                const sessionId = (params.sessionId as string) || client.sessionId;
                const msg = this.sessions.addMessage(sessionId, {
                    role: "user",
                    content: params.message as string,
                    sender: params.sender as string,
                    channel: params.channel as string,
                });

                // If Python backend is available, forward for AI processing
                if (this.python.isReady()) {
                    try {
                        const aiResp = await this.python.complete(
                            [{ role: "user", content: params.message as string }],
                            (params.model as string) || "default"
                        );
                        const assistantMsg = this.sessions.addMessage(sessionId, {
                            role: "assistant",
                            content: (aiResp.content as string) || "[No response]",
                        });

                        // Emit chat event to all connected clients
                        this.broadcastEvent("chat.done", {
                            sessionId,
                            userMessage: msg,
                            assistantMessage: assistantMsg,
                        });

                        return makeResponse(frame.id, {
                            userMessage: msg,
                            assistantMessage: assistantMsg,
                        });
                    } catch (err) {
                        const errMsg = err instanceof Error ? err.message : String(err);
                        return makeResponse(frame.id, {
                            userMessage: msg,
                            error: `Python backend error: ${errMsg}`,
                        });
                    }
                }

                return makeResponse(frame.id, {
                    userMessage: msg,
                    note: "Python backend not connected. No AI response.",
                });
            }

            case "chat.history": {
                const sessionId = (params.sessionId as string) || client.sessionId;
                const limit = (params.limit as number) || 100;
                const history = this.sessions.getHistory(sessionId, limit);
                return makeResponse(frame.id, { messages: history, count: history.length });
            }

            // System methods
            case "system.status": {
                const pythonStatus = this.python.isReady()
                    ? await this.python.getStatus().catch(() => ({ error: "unreachable" }))
                    : { status: "not started" };

                return makeResponse(frame.id, {
                    gateway: {
                        version: "1.2.0",
                        uptime: process.uptime(),
                        clients: this.clients.size,
                        sessions: this.sessions.listSessions().length,
                    },
                    python: pythonStatus,
                });
            }

            case "system.health": {
                const health = this.python.isReady()
                    ? await this.python.getHealth().catch(() => ({ status: "unreachable" }))
                    : { status: "not started" };

                return makeResponse(frame.id, {
                    gateway: "healthy",
                    python: health,
                });
            }

            case "system.config":
                return makeResponse(frame.id, {
                    port: this.config.port,
                    host: this.config.host,
                    pythonPort: this.config.pythonPort,
                    pythonReady: this.python.isReady(),
                });

            // MLX methods (proxied to Python)
            case "mlx.status":
                return this.proxyToPython(frame, "/api/mlx/status", "GET");

            case "mlx.generate":
                return this.proxyToPython(frame, "/api/mlx/generate", "POST", params);

            case "mlx.embed":
                return this.proxyToPython(frame, "/api/mlx/embed", "POST", params);

            // Agent methods (proxied to Python)
            case "agent.list":
                return this.proxyToPython(frame, "/api/agents", "GET");

            case "agent.status":
                return this.proxyToPython(frame, `/api/agents/${params.agentId}`, "GET");

            case "agent.restart":
                return this.proxyToPython(frame, `/api/agents/${params.agentId}/restart`, "POST");

            // Model methods (proxied to Python)
            case "model.list":
                return this.proxyToPython(frame, "/api/models", "GET");

            case "model.load":
                return this.proxyToPython(frame, "/api/models/load", "POST", params);

            case "model.unload":
                return this.proxyToPython(frame, "/api/models/unload", "POST", params);

            default:
                return makeError(frame.id, "METHOD_NOT_FOUND", `Unknown method: ${frame.method}`);
        }
    }

    // ─── Python Proxy ───────────────────────────────────────────────────────

    private async proxyToPython(
        frame: RequestFrame,
        path: string,
        method: string,
        body?: unknown
    ): Promise<ResponseFrame> {
        if (!this.python.isReady()) {
            return makeError(frame.id, "PYTHON_UNAVAILABLE", "Python backend is not running");
        }

        try {
            const result = await this.python.request(method, path, body);
            return makeResponse(frame.id, result);
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            return makeError(frame.id, "PYTHON_ERROR", message);
        }
    }

    // ─── Event Broadcasting ─────────────────────────────────────────────────

    private sendToClient(client: ClientConnection, frame: ResponseFrame | EventFrame): void {
        try {
            if (client.ws.readyState === 1) { // OPEN
                client.ws.send(JSON.stringify(frame));
            }
        } catch (err) {
            console.error(`[ws] Failed to send to ${client.id}:`, err);
        }
    }

    private broadcastEvent(event: string, payload?: unknown): void {
        this.eventSeq++;
        const frame = makeEvent(event, payload, this.eventSeq);
        for (const client of this.clients.values()) {
            this.sendToClient(client, frame);
        }
    }

    // ─── Shutdown ───────────────────────────────────────────────────────────

    async stop(): Promise<void> {
        console.log("\n🛑 Gateway shutting down...");

        // Close all WebSocket connections
        for (const client of this.clients.values()) {
            try {
                client.ws.close(1001, "Gateway shutting down");
            } catch { }
        }
        this.clients.clear();

        // Stop Python backend
        await this.python.stop();

        // Stop HTTP server
        await this.fastify.close();

        console.log("✅ Gateway stopped");
    }
}

// ─── Standalone Entry Point ─────────────────────────────────────────────────

async function main(): Promise<void> {
    const port = parseInt(process.env.CELL0_GATEWAY_PORT ?? "18789", 10);
    const host = process.env.CELL0_GATEWAY_HOST ?? "127.0.0.1";
    const pythonPort = parseInt(process.env.CELL0_PORT ?? "18800", 10);
    const autoStartPython = process.env.CELL0_NO_PYTHON !== "1";

    const gateway = new Gateway({
        port,
        host,
        pythonPort,
        projectRoot: process.cwd(),
        autoStartPython,
    });

    // Graceful shutdown
    const shutdown = async () => {
        await gateway.stop();
        process.exit(0);
    };

    process.on("SIGTERM", shutdown);
    process.on("SIGINT", shutdown);

    await gateway.start();
}

// Run if called directly
const isDirectRun =
    process.argv[1]?.endsWith("gateway/index.js") ||
    process.argv[1]?.endsWith("gateway/index.ts");

if (isDirectRun) {
    main().catch((err) => {
        console.error("Fatal error:", err);
        process.exit(1);
    });
}
