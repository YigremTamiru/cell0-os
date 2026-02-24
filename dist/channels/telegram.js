/**
 * Cell 0 OS — Telegram Channel Adapter
 *
 * Uses the Telegram Bot API via native Node.js fetch (no external SDK).
 * Bot token is obtained from @BotFather and stored in ~/.cell0/credentials/telegram/creds.json
 *
 * Setup flow:
 *   1. Message @BotFather → /newbot → copy token
 *   2. cell0 onboard → selects Telegram → pastes token
 *   3. QR code of t.me/<botname> shown for phone scan
 */
import { EventEmitter } from "node:events";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
const CREDS_PATH = path.join(os.homedir(), ".cell0", "credentials", "telegram", "creds.json");
export class TelegramAdapter extends EventEmitter {
    id = "telegram";
    defaultDomain = "social";
    connected = false;
    creds = null;
    pollOffset = 0;
    pollTimer = null;
    get apiBase() {
        return `https://api.telegram.org/bot${this.creds.token}`;
    }
    async api(method, body = {}) {
        const resp = await fetch(`${this.apiBase}/${method}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            throw new Error(`Telegram API error ${resp.status}: ${await resp.text()}`);
        }
        return resp.json();
    }
    loadCreds() {
        if (!fs.existsSync(CREDS_PATH))
            return null;
        try {
            return JSON.parse(fs.readFileSync(CREDS_PATH, "utf-8"));
        }
        catch {
            return null;
        }
    }
    async connect() {
        this.creds = this.loadCreds();
        if (!this.creds?.token) {
            console.warn("[Telegram] No bot token configured.\n" +
                "  1. Message @BotFather → /newbot\n" +
                "  2. Run: cell0 configure channels telegram");
            return;
        }
        // Verify token and get bot info
        let me;
        try {
            const result = await this.api("getMe");
            me = result.result;
        }
        catch (err) {
            this.emit("error", new Error(`[Telegram] Auth failed: ${err}`));
            return;
        }
        this.creds.botUsername = me.username;
        this.creds.botId = me.id;
        console.log(`[Telegram] Connected as @${me.username} (id:${me.id})`);
        this.connected = true;
        this.emit("connected");
        this.startPolling();
    }
    startPolling() {
        const poll = async () => {
            if (!this.connected)
                return;
            try {
                const result = await this.api("getUpdates", {
                    offset: this.pollOffset,
                    timeout: 20,
                    allowed_updates: ["message", "callback_query"],
                });
                if (result.ok) {
                    for (const update of result.result) {
                        this.pollOffset = update.update_id + 1;
                        const msg = update.message;
                        if (!msg?.text)
                            continue;
                        const inbound = {
                            id: String(update.update_id),
                            channelId: this.id,
                            domain: this.defaultDomain,
                            senderId: String(msg.from?.id ?? "unknown"),
                            senderName: msg.from?.username ??
                                [msg.from?.first_name, msg.from?.last_name]
                                    .filter(Boolean)
                                    .join(" ") ??
                                undefined,
                            threadId: String(msg.chat.id),
                            groupId: msg.chat.type !== "private"
                                ? String(msg.chat.id)
                                : undefined,
                            text: msg.text,
                            timestamp: msg.date * 1000,
                            isEncrypted: false,
                            rawPayload: msg,
                        };
                        this.emit("message", inbound);
                    }
                }
            }
            catch (err) {
                if (this.connected) {
                    console.error("[Telegram] Poll error:", err);
                }
            }
            if (this.connected) {
                this.pollTimer = setTimeout(poll, 500);
            }
        };
        poll();
    }
    async disconnect() {
        this.connected = false;
        if (this.pollTimer) {
            clearTimeout(this.pollTimer);
            this.pollTimer = null;
        }
        this.emit("disconnected");
    }
    async send(message) {
        if (!this.connected)
            throw new Error("Telegram adapter not connected");
        const chatId = message.threadId ?? message.recipientId;
        await this.api("sendMessage", {
            chat_id: chatId,
            text: message.text,
            parse_mode: "Markdown",
        });
    }
    /** Called by wizard to save token and show setup QR */
    async setup(token) {
        const dir = path.dirname(CREDS_PATH);
        fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
        fs.writeFileSync(CREDS_PATH, JSON.stringify({ token }, null, 2), {
            encoding: "utf-8",
            mode: 0o600,
        });
        // Quick verify to get bot username
        this.creds = { token };
        try {
            const result = await this.api("getMe");
            const me = result.result;
            const botUrl = `https://t.me/${me.username}`;
            console.log(`\n[Telegram] Bot: @${me.username}`);
            console.log("[Telegram] Share QR with users to start a conversation:\n");
            let qrcode;
            try {
                qrcode = await import("qrcode-terminal");
                (qrcode.default ?? qrcode).generate(botUrl, { small: true });
            }
            catch {
                console.log(`  ${botUrl}`);
            }
            console.log(`\n  Or share: ${botUrl}\n`);
            fs.writeFileSync(CREDS_PATH, JSON.stringify({ token, botUsername: me.username, botId: me.id }, null, 2), { mode: 0o600 });
        }
        catch (err) {
            console.warn("[Telegram] Could not verify token:", err);
        }
    }
    isConnected() {
        return this.connected;
    }
}
//# sourceMappingURL=telegram.js.map