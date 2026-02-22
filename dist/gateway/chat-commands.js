/**
 * Cell 0 OS — Chat Commands
 *
 * In-session slash commands matching OpenClaw's chat command system.
 * These are intercepted by the gateway before reaching the AI model.
 */
// ─── Default Settings ─────────────────────────────────────────────────────
const DEFAULT_SESSION_SETTINGS = {
    thinkingLevel: "medium",
    verbose: false,
    usageDisplay: "off",
};
// Per-session settings store
const sessionSettings = new Map();
function getSettings(sessionId) {
    if (!sessionSettings.has(sessionId)) {
        sessionSettings.set(sessionId, { ...DEFAULT_SESSION_SETTINGS });
    }
    return sessionSettings.get(sessionId);
}
// ─── Command Parser ──────────────────────────────────────────────────────
export function parseChatCommand(message, sessionId, sessions) {
    const trimmed = message.trim();
    if (!trimmed.startsWith("/")) {
        return { handled: false };
    }
    const parts = trimmed.split(/\s+/);
    const cmd = parts[0].toLowerCase();
    const args = parts.slice(1);
    switch (cmd) {
        case "/status":
            return handleStatus(sessionId, sessions);
        case "/new":
        case "/reset":
            return handleReset(sessionId, sessions);
        case "/compact":
            return handleCompact(sessionId);
        case "/think":
            return handleThink(sessionId, args);
        case "/verbose":
            return handleVerbose(sessionId, args);
        case "/usage":
            return handleUsage(sessionId, args);
        case "/model":
            return handleModel(sessionId, args);
        case "/restart":
            return handleRestart();
        case "/help":
            return handleHelp();
        default:
            return {
                handled: true,
                response: `Unknown command: ${cmd}. Type /help for available commands.`,
            };
    }
}
// ─── Command Handlers ─────────────────────────────────────────────────────
function handleStatus(sessionId, sessions) {
    const session = sessions.getSession(sessionId);
    const settings = getSettings(sessionId);
    const lines = [
        "📊 Session Status",
        `  Session: ${sessionId}`,
        `  Model: ${settings.model ?? "default"}`,
        `  Thinking: ${settings.thinkingLevel}`,
        `  Verbose: ${settings.verbose ? "on" : "off"}`,
        `  Usage display: ${settings.usageDisplay}`,
    ];
    if (session) {
        lines.push(`  History: ${session.history.length} messages`);
        lines.push(`  Created: ${new Date(session.createdAt).toLocaleString()}`);
    }
    return {
        handled: true,
        response: lines.join("\n"),
    };
}
function handleReset(sessionId, sessions) {
    sessions.deleteSession(sessionId);
    sessions.createSession("group", { channelId: sessionId });
    sessionSettings.delete(sessionId);
    return {
        handled: true,
        response: "🔄 Session reset. Starting fresh.",
        action: "reset",
    };
}
function handleCompact(sessionId) {
    return {
        handled: true,
        response: "📦 Session compacted. Context summarized to save tokens.",
        action: "compact",
    };
}
function handleThink(sessionId, args) {
    const validLevels = [
        "off",
        "minimal",
        "low",
        "medium",
        "high",
        "xhigh",
    ];
    const level = args[0]?.toLowerCase();
    if (!level || !validLevels.includes(level)) {
        const settings = getSettings(sessionId);
        return {
            handled: true,
            response: `🧠 Current thinking level: ${settings.thinkingLevel}\n   Options: ${validLevels.join(", ")}`,
        };
    }
    const settings = getSettings(sessionId);
    settings.thinkingLevel = level;
    return {
        handled: true,
        response: `🧠 Thinking level set to: ${level}`,
    };
}
function handleVerbose(sessionId, args) {
    const settings = getSettings(sessionId);
    if (args[0] === "on") {
        settings.verbose = true;
        return { handled: true, response: "📝 Verbose mode: ON" };
    }
    if (args[0] === "off") {
        settings.verbose = false;
        return { handled: true, response: "📝 Verbose mode: OFF" };
    }
    return {
        handled: true,
        response: `📝 Verbose mode: ${settings.verbose ? "ON" : "OFF"}\n   Usage: /verbose on|off`,
    };
}
function handleUsage(sessionId, args) {
    const settings = getSettings(sessionId);
    const validModes = ["off", "tokens", "full"];
    const mode = args[0]?.toLowerCase();
    if (!mode || !validModes.includes(mode)) {
        return {
            handled: true,
            response: `📊 Usage display: ${settings.usageDisplay}\n   Options: off, tokens, full`,
        };
    }
    settings.usageDisplay = mode;
    return {
        handled: true,
        response: `📊 Usage display set to: ${mode}`,
    };
}
function handleModel(sessionId, args) {
    const settings = getSettings(sessionId);
    if (!args[0]) {
        return {
            handled: true,
            response: `🤖 Current model: ${settings.model ?? "default (from config)"}\n   Usage: /model <model-id>`,
        };
    }
    settings.model = args.join(" ");
    return {
        handled: true,
        response: `🤖 Model set to: ${settings.model}`,
    };
}
function handleRestart() {
    return {
        handled: true,
        response: "🔄 Gateway restart requested…",
        action: "restart",
    };
}
function handleHelp() {
    const lines = [
        "📖 Available Commands",
        "",
        "  /status           — Session status (model + tokens)",
        "  /new, /reset      — Reset the session",
        "  /compact          — Compact session context",
        "  /think <level>    — off|minimal|low|medium|high|xhigh",
        "  /verbose on|off   — Toggle verbose mode",
        "  /usage <mode>     — off|tokens|full (per-response usage)",
        "  /model <id>       — Change model for this session",
        "  /restart          — Restart the gateway",
        "  /help             — Show this help",
    ];
    return {
        handled: true,
        response: lines.join("\n"),
    };
}
//# sourceMappingURL=chat-commands.js.map