/**
 * Cell 0 OS — Session Manager
 *
 * Manages chat sessions with OpenClaw-compatible isolation:
 * - main: Primary session (always exists)
 * - group: Isolated sessions for multi-party channels
 * - Per-session agent routing and history
 */
import { randomUUID } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { CELL0_PATHS } from "../config/config.js";
export class SessionManager {
    sessions = new Map();
    mainSessionId;
    constructor() {
        // Load existing snapshots from disk before creating main session
        this.loadSnapshots();
        // Always create the main session
        this.mainSessionId = this.createSession("main").id;
    }
    get sessionsDir() {
        return CELL0_PATHS.runtime.sessions;
    }
    ensureSessionsDir() {
        try {
            if (!fs.existsSync(this.sessionsDir)) {
                fs.mkdirSync(this.sessionsDir, { recursive: true, mode: 0o700 });
            }
        }
        catch {
            // Ignore errors — snapshots are best-effort
        }
    }
    writeSnapshot(session) {
        try {
            this.ensureSessionsDir();
            const filePath = path.join(this.sessionsDir, `${session.id}.json`);
            fs.writeFileSync(filePath, JSON.stringify(session, null, 2), { encoding: "utf-8", mode: 0o600 });
        }
        catch {
            // Snapshot failures must not break session logic
        }
    }
    loadSnapshots() {
        try {
            if (!fs.existsSync(this.sessionsDir))
                return;
            const files = fs.readdirSync(this.sessionsDir).filter(f => f.endsWith(".json"));
            for (const file of files) {
                try {
                    const filePath = path.join(this.sessionsDir, file);
                    const raw = fs.readFileSync(filePath, "utf-8");
                    const session = JSON.parse(raw);
                    if (session.id && session.type) {
                        this.sessions.set(session.id, session);
                    }
                }
                catch {
                    // Skip malformed snapshot files
                }
            }
        }
        catch {
            // Ignore errors — snapshots are best-effort
        }
    }
    createSession(type = "group", options) {
        const session = {
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
        this.writeSnapshot(session);
        return session;
    }
    getSession(id) {
        return this.sessions.get(id);
    }
    getMainSession() {
        return this.sessions.get(this.mainSessionId);
    }
    /**
     * Retrieves an active domain session or creates a new one.
     * Ensures strict isolation between cognitive domains.
     */
    getOrCreateDomainSession(domain) {
        // Find existing strict domain session
        for (const session of this.sessions.values()) {
            if (session.type === 'domain' && session.domain === domain) {
                return session;
            }
        }
        // Create new isolated domain session
        return this.createSession('domain', { domain });
    }
    listSessions() {
        return Array.from(this.sessions.values());
    }
    deleteSession(id) {
        if (id === this.mainSessionId)
            return false; // Can't delete main
        return this.sessions.delete(id);
    }
    addMessage(sessionId, message) {
        const session = this.sessions.get(sessionId);
        if (!session)
            throw new Error(`Session not found: ${sessionId}`);
        const msg = {
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
        this.writeSnapshot(session);
        return msg;
    }
    getHistory(sessionId, limit = 100) {
        const session = this.sessions.get(sessionId);
        if (!session)
            return [];
        return session.history.slice(-limit);
    }
    /** Prune inactive group sessions older than maxAge (ms) */
    pruneInactive(maxAgeMs = 24 * 60 * 60 * 1000) {
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
//# sourceMappingURL=sessions.js.map