/**
 * Cell 0 OS — Wire Protocol Type Definitions
 *
 * OpenClaw-compatible WebSocket wire protocol:
 * - connect: First frame with auth + device identity
 * - req/res: Request-response pairs with idempotency
 * - event: Server-pushed events with optional sequencing
 */
import { type Static } from "@sinclair/typebox";
export declare const ConnectFrame: import("@sinclair/typebox").TObject<{
    type: import("@sinclair/typebox").TLiteral<"connect">;
    token: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TString>;
    deviceId: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TString>;
    deviceName: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TString>;
    version: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TString>;
}>;
export declare const RequestFrame: import("@sinclair/typebox").TObject<{
    type: import("@sinclair/typebox").TLiteral<"req">;
    id: import("@sinclair/typebox").TString;
    method: import("@sinclair/typebox").TString;
    params: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TRecord<import("@sinclair/typebox").TString, import("@sinclair/typebox").TUnknown>>;
    idempotencyKey: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TString>;
}>;
export declare const ResponseFrame: import("@sinclair/typebox").TObject<{
    type: import("@sinclair/typebox").TLiteral<"res">;
    id: import("@sinclair/typebox").TString;
    ok: import("@sinclair/typebox").TBoolean;
    payload: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TUnknown>;
    error: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TObject<{
        code: import("@sinclair/typebox").TString;
        message: import("@sinclair/typebox").TString;
        details: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TUnknown>;
    }>>;
}>;
export declare const EventFrame: import("@sinclair/typebox").TObject<{
    type: import("@sinclair/typebox").TLiteral<"event">;
    event: import("@sinclair/typebox").TString;
    payload: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TUnknown>;
    seq: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TNumber>;
    stateVersion: import("@sinclair/typebox").TOptional<import("@sinclair/typebox").TNumber>;
}>;
export type ConnectFrame = Static<typeof ConnectFrame>;
export type RequestFrame = Static<typeof RequestFrame>;
export type ResponseFrame = Static<typeof ResponseFrame>;
export type EventFrame = Static<typeof EventFrame>;
export type InboundFrame = ConnectFrame | RequestFrame;
export type OutboundFrame = ResponseFrame | EventFrame;
export declare const GATEWAY_METHODS: {
    readonly "session.create": "Create a new chat session";
    readonly "session.list": "List active sessions";
    readonly "session.get": "Get session details";
    readonly "session.delete": "Delete a session";
    readonly "chat.send": "Send a message to the active session";
    readonly "chat.history": "Get message history for a session";
    readonly "chat.stream": "Stream a chat response";
    readonly "agent.list": "List available agents";
    readonly "agent.status": "Get agent status";
    readonly "agent.restart": "Restart an agent";
    readonly "model.list": "List loaded models";
    readonly "model.load": "Load a model";
    readonly "model.unload": "Unload a model";
    readonly "system.status": "Get system status";
    readonly "system.health": "Health check";
    readonly "system.config": "Get configuration";
    readonly "channel.list": "List configured channels";
    readonly "channel.status": "Get channel status";
    readonly "skill.list": "List installed skills";
    readonly "skill.invoke": "Invoke a skill";
    readonly "mlx.status": "Get MLX bridge status";
    readonly "mlx.generate": "Generate text via MLX";
    readonly "mlx.embed": "Generate embeddings via MLX";
};
export type GatewayMethod = keyof typeof GATEWAY_METHODS;
export declare const GATEWAY_EVENTS: {
    readonly "gateway.ready": "Gateway is ready to accept requests";
    readonly "gateway.heartbeat": "Periodic heartbeat";
    readonly "session.updated": "Session state changed";
    readonly "chat.chunk": "Streaming chat chunk";
    readonly "chat.done": "Chat stream completed";
    readonly "chat.error": "Chat error occurred";
    readonly "agent.stateChanged": "Agent state changed";
    readonly "channel.message": "Inbound channel message";
    readonly "presence.update": "Presence state update";
    readonly "tool.progress": "Tool execution progress";
    readonly "tool.result": "Tool execution result";
};
export type GatewayEvent = keyof typeof GATEWAY_EVENTS;
export declare function makeResponse(id: string, payload: unknown): ResponseFrame;
export declare function makeError(id: string, code: string, message: string, details?: unknown): ResponseFrame;
export declare function makeEvent(event: string, payload?: unknown, seq?: number): EventFrame;
//# sourceMappingURL=protocol.d.ts.map