/**
 * Cell 0 OS — Wire Protocol Type Definitions
 *
 * OpenClaw-compatible WebSocket wire protocol:
 * - connect: First frame with auth + device identity
 * - req/res: Request-response pairs with idempotency
 * - event: Server-pushed events with optional sequencing
 */
import { Type } from "@sinclair/typebox";
// ─── Frame Types ────────────────────────────────────────────────────────────
export const ConnectFrame = Type.Object({
    type: Type.Literal("connect"),
    token: Type.Optional(Type.String()),
    deviceId: Type.Optional(Type.String()),
    deviceName: Type.Optional(Type.String()),
    version: Type.Optional(Type.String()),
});
export const RequestFrame = Type.Object({
    type: Type.Literal("req"),
    id: Type.String({ minLength: 1 }),
    method: Type.String({ minLength: 1 }),
    params: Type.Optional(Type.Record(Type.String(), Type.Unknown())),
    idempotencyKey: Type.Optional(Type.String()),
});
export const ResponseFrame = Type.Object({
    type: Type.Literal("res"),
    id: Type.String(),
    ok: Type.Boolean(),
    payload: Type.Optional(Type.Unknown()),
    error: Type.Optional(Type.Object({
        code: Type.String(),
        message: Type.String(),
        details: Type.Optional(Type.Unknown()),
    })),
});
export const EventFrame = Type.Object({
    type: Type.Literal("event"),
    event: Type.String(),
    payload: Type.Optional(Type.Unknown()),
    seq: Type.Optional(Type.Number()),
    stateVersion: Type.Optional(Type.Number()),
});
// ─── Method Registry ────────────────────────────────────────────────────────
export const GATEWAY_METHODS = {
    // Session
    "session.create": "Create a new chat session",
    "session.list": "List active sessions",
    "session.get": "Get session details",
    "session.delete": "Delete a session",
    // Chat
    "chat.send": "Send a message to the active session",
    "chat.history": "Get message history for a session",
    "chat.stream": "Stream a chat response",
    // Agent
    "agent.list": "List available agents",
    "agent.status": "Get agent status",
    "agent.restart": "Restart an agent",
    // Model
    "model.list": "List loaded models",
    "model.load": "Load a model",
    "model.unload": "Unload a model",
    // System
    "system.status": "Get system status",
    "system.health": "Health check",
    "system.config": "Get configuration",
    // Channel
    "channel.list": "List configured channels",
    "channel.status": "Get channel status",
    // Skills
    "skill.list": "List installed skills",
    "skill.invoke": "Invoke a skill",
    // MLX
    "mlx.status": "Get MLX bridge status",
    "mlx.generate": "Generate text via MLX",
    "mlx.embed": "Generate embeddings via MLX",
};
// ─── Event Types ────────────────────────────────────────────────────────────
export const GATEWAY_EVENTS = {
    "gateway.ready": "Gateway is ready to accept requests",
    "gateway.heartbeat": "Periodic heartbeat",
    "session.updated": "Session state changed",
    "chat.chunk": "Streaming chat chunk",
    "chat.done": "Chat stream completed",
    "chat.error": "Chat error occurred",
    "agent.stateChanged": "Agent state changed",
    "channel.message": "Inbound channel message",
    "presence.update": "Presence state update",
    "tool.progress": "Tool execution progress",
    "tool.result": "Tool execution result",
};
// ─── Protocol Helpers ───────────────────────────────────────────────────────
export function makeResponse(id, payload) {
    return { type: "res", id, ok: true, payload };
}
export function makeError(id, code, message, details) {
    return { type: "res", id, ok: false, error: { code, message, details } };
}
export function makeEvent(event, payload, seq) {
    return { type: "event", event, payload, seq };
}
//# sourceMappingURL=protocol.js.map