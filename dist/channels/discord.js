/**
 * Cell 0 OS — Discord Channel Adapter
 *
 * Uses Discord Gateway WebSocket API with native ws module.
 * Bot token from Discord Developer Portal (no OAuth needed for bots).
 *
 * Setup: https://discord.com/developers/applications → New App → Bot → Copy Token
 * Invite: https://discord.com/api/oauth2/authorize?client_id=<ID>&permissions=2048&scope=bot
 */
import { EventEmitter } from "node:events";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import WebSocket from "ws";
const CREDS_PATH = path.join(os.homedir(), ".cell0", "credentials", "discord", "creds.json");
const DISCORD_API = "https://discord.com/api/v10";
export class DiscordAdapter extends EventEmitter {
    id = "discord";
    defaultDomain = "social";
    connected = false;
    creds = null;
    ws = null;
    heartbeatInterval = null;
    sessionId = null;
    lastSeq = null;
    resumeGatewayUrl = null;
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
    async discordApi(method, endpoint, body) {
        const resp = await fetch(`${DISCORD_API}${endpoint}`, {
            method,
            headers: {
                Authorization: `Bot ${this.creds.botToken}`,
                "Content-Type": "application/json",
            },
            body: body ? JSON.stringify(body) : undefined,
        });
        if (!resp.ok) {
            throw new Error(`Discord API ${resp.status}: ${await resp.text()}`);
        }
        return resp.json();
    }
    async connect() {
        this.creds = this.loadCreds();
        if (!this.creds?.botToken) {
            console.warn("[Discord] No bot token. Create a bot at:\n" +
                "  https://discord.com/developers/applications\n" +
                "  Then run: cell0 configure channels discord");
            return;
        }
        // Get Gateway URL
        const gatewayInfo = await this.discordApi("GET", "/gateway/bot").catch(() => null);
        const gatewayUrl = gatewayInfo?.url ?? "wss://gateway.discord.gg";
        this.connectGateway(`${gatewayUrl}/?v=10&encoding=json`);
    }
    connectGateway(url) {
        this.ws = new WebSocket(url);
        this.ws.on("message", (data) => {
            try {
                const payload = JSON.parse(data.toString());
                this.handlePayload(payload);
            }
            catch { /* ignore parse errors */ }
        });
        this.ws.on("close", () => {
            this.connected = false;
            this.emit("disconnected");
            if (this.heartbeatInterval) {
                clearInterval(this.heartbeatInterval);
                this.heartbeatInterval = null;
            }
        });
        this.ws.on("error", (err) => {
            this.emit("error", err);
        });
    }
    handlePayload(payload) {
        const { op, d, s, t } = payload;
        if (s)
            this.lastSeq = s;
        switch (op) {
            case 10: // Hello
                this.startHeartbeat(d.heartbeat_interval);
                this.identify();
                break;
            case 11: // Heartbeat ACK
                break;
            case 0: // Dispatch
                this.handleDispatch(t, d);
                break;
            case 7: // Reconnect
                this.ws?.close();
                this.connect();
                break;
            case 9: // Invalid Session
                setTimeout(() => this.identify(), 5000);
                break;
        }
    }
    startHeartbeat(intervalMs) {
        this.heartbeatInterval = setInterval(() => {
            if (this.ws?.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ op: 1, d: this.lastSeq }));
            }
        }, intervalMs);
    }
    identify() {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN)
            return;
        this.ws.send(JSON.stringify({
            op: 2,
            d: {
                token: this.creds.botToken,
                intents: 33280, // GUILDS + GUILD_MESSAGES + MESSAGE_CONTENT
                properties: { os: "linux", browser: "cell0", device: "cell0" },
            },
        }));
    }
    handleDispatch(type, data) {
        switch (type) {
            case "READY":
                this.sessionId = data.session_id;
                this.resumeGatewayUrl = data.resume_gateway_url;
                this.creds.applicationId = data.application?.id;
                this.connected = true;
                this.emit("connected");
                console.log(`[Discord] Connected as ${data.user?.username}#${data.user?.discriminator}`);
                break;
            case "MESSAGE_CREATE":
                if (data.author?.bot)
                    return; // Ignore bots
                const inbound = {
                    id: data.id,
                    channelId: this.id,
                    domain: this.defaultDomain,
                    senderId: data.author?.id ?? "unknown",
                    senderName: data.author?.username,
                    threadId: data.channel_id,
                    groupId: data.guild_id,
                    text: data.content,
                    timestamp: new Date(data.timestamp).getTime(),
                    isEncrypted: false,
                    rawPayload: data,
                };
                this.emit("message", inbound);
                break;
        }
    }
    async disconnect() {
        this.connected = false;
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.emit("disconnected");
    }
    async send(message) {
        if (!this.connected)
            throw new Error("Discord adapter not connected");
        await this.discordApi("POST", `/channels/${message.threadId ?? message.recipientId}/messages`, {
            content: message.text,
        });
    }
    /** Show setup QR with bot invite link */
    async setup(botToken) {
        const dir = path.dirname(CREDS_PATH);
        fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
        fs.writeFileSync(CREDS_PATH, JSON.stringify({ botToken }, null, 2), { mode: 0o600 });
        this.creds = { botToken };
        try {
            const app = await this.discordApi("GET", "/oauth2/applications/@me");
            const inviteUrl = `https://discord.com/api/oauth2/authorize?client_id=${app.id}&permissions=2048&scope=bot`;
            console.log(`\n[Discord] Bot: ${app.name}`);
            console.log("[Discord] Scan QR to invite bot to your server:\n");
            let qrcode;
            try {
                qrcode = await import("qrcode-terminal");
                (qrcode.default ?? qrcode).generate(inviteUrl, { small: true });
            }
            catch {
                console.log(`  ${inviteUrl}`);
            }
        }
        catch {
            console.log("[Discord] Token saved. Start gateway to connect.");
        }
    }
    isConnected() { return this.connected; }
}
//# sourceMappingURL=discord.js.map