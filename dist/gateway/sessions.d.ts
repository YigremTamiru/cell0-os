/**
 * Cell 0 OS — Session Manager
 *
 * Manages chat sessions with OpenClaw-compatible isolation:
 * - main: Primary session (always exists)
 * - group: Isolated sessions for multi-party channels
 * - Per-session agent routing and history
 */
export interface Session {
    id: string;
    type: "main" | "group" | "domain";
    domain?: string;
    channelId?: string;
    agentId: string;
    createdAt: string;
    updatedAt: string;
    history: ChatMessage[];
    metadata: Record<string, unknown>;
}
export interface ChatMessage {
    id: string;
    role: "user" | "assistant" | "system" | "tool";
    content: string;
    sender?: string;
    channel?: string;
    timestamp: string;
    metadata?: Record<string, unknown>;
}
export declare class SessionManager {
    private sessions;
    private mainSessionId;
    constructor();
    private get sessionsDir();
    private ensureSessionsDir;
    private writeSnapshot;
    private loadSnapshots;
    createSession(type?: "main" | "group" | "domain", options?: {
        channelId?: string;
        domain?: string;
        agentId?: string;
        metadata?: Record<string, unknown>;
    }): Session;
    getSession(id: string): Session | undefined;
    getMainSession(): Session;
    /**
     * Retrieves an active domain session or creates a new one.
     * Ensures strict isolation between cognitive domains.
     */
    getOrCreateDomainSession(domain: string): Session;
    listSessions(): Session[];
    deleteSession(id: string): boolean;
    addMessage(sessionId: string, message: Omit<ChatMessage, "id" | "timestamp">): ChatMessage;
    getHistory(sessionId: string, limit?: number): ChatMessage[];
    /** Prune inactive group sessions older than maxAge (ms) */
    pruneInactive(maxAgeMs?: number): number;
}
//# sourceMappingURL=sessions.d.ts.map