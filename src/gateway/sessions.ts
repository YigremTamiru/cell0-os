/**
 * Cell 0 OS — Session Manager
 *
 * Manages chat sessions with OpenClaw-compatible isolation:
 * - main: Primary session (always exists)
 * - group: Isolated sessions for multi-party channels
 * - Per-session agent routing and history
 */

import { randomUUID } from "node:crypto";

export interface Session {
    id: string;
    type: "main" | "group" | "domain";
    domain?: string; // e.g., 'social', 'productivity'
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

export class SessionManager {
    private sessions = new Map<string, Session>();
    private mainSessionId: string;

    constructor() {
        // Always create the main session
        this.mainSessionId = this.createSession("main").id;
    }

    createSession(
        type: "main" | "group" | "domain" = "group",
        options?: {
            channelId?: string;
            domain?: string;
            agentId?: string;
            metadata?: Record<string, unknown>;
        }
    ): Session {
        const session: Session = {
            id: randomUUID(),
            type,
            channelId: options?.channelId,
            domain: options?.domain,
            agentId: options?.agentId ?? "default",
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            history: [],
            metadata: options?.metadata ?? {},
        };
        this.sessions.set(session.id, session);
        return session;
    }

    getSession(id: string): Session | undefined {
        return this.sessions.get(id);
    }

    getMainSession(): Session {
        return this.sessions.get(this.mainSessionId)!;
    }

    /**
     * Retrieves an active domain session or creates a new one.
     * Ensures strict isolation between cognitive domains.
     */
    getOrCreateDomainSession(domain: string): Session {
        // Find existing strict domain session
        for (const session of this.sessions.values()) {
            if (session.type === 'domain' && session.domain === domain) {
                return session;
            }
        }

        // Create new isolated domain session
        return this.createSession('domain', { domain });
    }

    listSessions(): Session[] {
        return Array.from(this.sessions.values());
    }

    deleteSession(id: string): boolean {
        if (id === this.mainSessionId) return false; // Can't delete main
        return this.sessions.delete(id);
    }

    addMessage(sessionId: string, message: Omit<ChatMessage, "id" | "timestamp">): ChatMessage {
        const session = this.sessions.get(sessionId);
        if (!session) throw new Error(`Session not found: ${sessionId}`);

        const msg: ChatMessage = {
            ...message,
            id: randomUUID(),
            timestamp: new Date().toISOString(),
        };
        session.history.push(msg);
        session.updatedAt = msg.timestamp;

        // Keep history bounded
        if (session.history.length > 1000) {
            session.history = session.history.slice(-500);
        }

        return msg;
    }

    getHistory(sessionId: string, limit = 100): ChatMessage[] {
        const session = this.sessions.get(sessionId);
        if (!session) return [];
        return session.history.slice(-limit);
    }

    /** Prune inactive group sessions older than maxAge (ms) */
    pruneInactive(maxAgeMs = 24 * 60 * 60 * 1000): number {
        const cutoff = new Date(Date.now() - maxAgeMs).toISOString();
        let pruned = 0;
        for (const [id, session] of this.sessions) {
            if (session.type === "group" && session.updatedAt < cutoff) {
                this.sessions.delete(id);
                pruned++;
            }
        }
        return pruned;
    }
}
