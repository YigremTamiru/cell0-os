/**
 * AgentRuntime
 *
 * TypeScript wrapper for cell0/engine/agents/agent_mesh.py.
 * Provides the execution layer for orchestrating specific agent personas,
 * transmitting inputs through the Python Bridge, and managing synchronous
 * or asynchronous streams back to the Gateway.
 */
export class AgentRuntime {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Executes a task on the Agent Mesh synchronously.
     */
    async executeTask(request, options = {}) {
        if (!this.bridge.isReady()) {
            throw new Error("Python backend is not ready");
        }
        try {
            // Map the Node task request to the Python completion format
            const reqBody = {
                model: request.context.specialist || "default", // Route to specific specialist if identified
                messages: [{ role: "user", content: request.input }],
                domain_context: request.context.domain,
                session_id: request.context.sessionId,
            };
            const result = await this.bridge.post("/api/chat/completions", reqBody);
            return {
                status: "success",
                content: result.content || result.text || "", // Fallbacks based on typical Python response
                metadata: {
                    latency: result.latency_ms,
                    provider: result.provider,
                }
            };
        }
        catch (error) {
            console.error("[AgentRuntime] execution failed:", error);
            return {
                status: "error",
                content: "Internal execution failure",
                metadata: { error: error.message }
            };
        }
    }
    /**
     * Executes a task on the Agent Mesh and streams the response via real-time WebSocket.
     */
    async streamTask(request, onChunk, options = {}) {
        if (!this.bridge.isReady()) {
            throw new Error("Python backend is not ready");
        }
        const taskId = request.taskId || crypto.randomUUID();
        // Register listener for streaming events over WS
        const listener = (msg) => {
            if (msg.type === "stream_chunk" && msg.taskId === taskId) {
                onChunk(msg.chunk);
            }
        };
        this.bridge.on("message", listener);
        try {
            // Trigger stream over WebSocket
            this.bridge.sendWsMessage({
                type: "execute_stream",
                taskId,
                request: {
                    model: request.context.specialist || "default",
                    messages: [{ role: "user", content: request.input }],
                    domain_context: request.context.domain,
                    session_id: request.context.sessionId,
                }
            });
            // In a real execution environment, we would await a "stream_end" signal.
            // For this abstract simulation bridge, we resolve once transmission begins,
            // leaving the EventEmitter to pump chunks asynchronously.
        }
        catch (error) {
            this.bridge.off("message", listener);
            throw error;
        }
    }
}
//# sourceMappingURL=runtime.js.map