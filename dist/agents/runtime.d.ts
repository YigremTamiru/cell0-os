import { PythonBridge } from "./python-bridge.js";
export interface AgentContext {
    sessionId: string;
    domain: string;
    specialist?: string;
    channelId: string;
    channelSource: string;
}
export interface TaskRequest {
    taskId?: string;
    intent: string;
    input: string;
    context: AgentContext;
    encryptedPayload?: boolean;
}
export interface TaskResponse {
    status: "success" | "error" | "streaming";
    content: string;
    metadata?: Record<string, unknown>;
}
export interface ExecutionOptions {
    stream?: boolean;
    timeoutMs?: number;
    requireEncryption?: boolean;
}
/**
 * AgentRuntime
 *
 * TypeScript wrapper for cell0/engine/agents/agent_mesh.py.
 * Provides the execution layer for orchestrating specific agent personas,
 * transmitting inputs through the Python Bridge, and managing synchronous
 * or asynchronous streams back to the Gateway.
 */
export declare class AgentRuntime {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Executes a task on the Agent Mesh synchronously.
     */
    executeTask(request: TaskRequest, options?: ExecutionOptions): Promise<TaskResponse>;
    /**
     * Executes a task on the Agent Mesh and streams the response via real-time WebSocket.
     */
    streamTask(request: TaskRequest, onChunk: (chunk: string) => void, options?: ExecutionOptions): Promise<void>;
}
//# sourceMappingURL=runtime.d.ts.map