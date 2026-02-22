/**
 * Cell 0 OS — Chat Commands
 *
 * In-session slash commands matching OpenClaw's chat command system.
 * These are intercepted by the gateway before reaching the AI model.
 */
import type { SessionManager } from "./sessions.js";
export interface ChatCommandResult {
    handled: boolean;
    response?: string;
    action?: "reset" | "compact" | "restart";
}
export type ThinkingLevel = "off" | "minimal" | "low" | "medium" | "high" | "xhigh";
export interface SessionSettings {
    thinkingLevel: ThinkingLevel;
    verbose: boolean;
    usageDisplay: "off" | "tokens" | "full";
    model?: string;
}
export declare function parseChatCommand(message: string, sessionId: string, sessions: SessionManager): ChatCommandResult;
//# sourceMappingURL=chat-commands.d.ts.map