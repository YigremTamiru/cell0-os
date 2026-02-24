/**
 * Cell 0 OS — Slack Channel Adapter
 *
 * Uses Slack's Socket Mode (WebSocket) — no public URL required.
 * App-level token from Slack App settings.
 *
 * Setup:
 *   1. Create Slack App at https://api.slack.com/apps
 *   2. Enable Socket Mode → App-Level Token (connections:write scope)
 *   3. Add Bot Token scopes: chat:write, channels:history, im:history, im:read, im:write
 *   4. Install to workspace → copy Bot User OAuth Token
 *   5. Run: cell0 configure channels slack
 */

import { EventEmitter } from "node:events";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import WebSocket from "ws";
import {
    type ChannelAdapter,
    type InboundMessage,
    type OutboundMessage,
    type ChannelDomain,
} from "./adapter.js";

const CREDS_PATH = path.join(os.homedir(), ".cell0", "credentials", "slack", "creds.json");
const SLACK_API = "https://slack.com/api";

interface SlackCreds {
    appToken: string;   // xapp-... (Socket Mode)
    botToken: string;   // xoxb-...
}

export class SlackAdapter extends EventEmitter implements ChannelAdapter {
    public readonly id = "slack";
    public readonly defaultDomain: ChannelDomain = "productivity";
    private connected = false;
    private creds: SlackCreds | null = null;
    private ws: WebSocket | null = null;
    private pingInterval: NodeJS.Timeout | null = null;

    private loadCreds(): SlackCreds | null {
        if (!fs.existsSync(CREDS_PATH)) return null;
        try {
            return JSON.parse(fs.readFileSync(CREDS_PATH, "utf-8")) as SlackCreds;
        } catch {
            return null;
        }
    }

    private async slackApi(method: string, body: Record<string, unknown> = {}): Promise<any> {
        const resp = await fetch(`${SLACK_API}/${method}`, {
            method: "POST",
            headers: {
                Authorization: `Bearer ${this.creds!.botToken}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify(body),
        });
        return resp.json();
    }

    async connect(): Promise<void> {
        this.creds = this.loadCreds();
        if (!this.creds?.appToken || !this.creds?.botToken) {
            console.warn(
                "[Slack] No credentials configured.\n" +
                "  Create a Slack App with Socket Mode enabled.\n" +
                "  Run: cell0 configure channels slack"
            );
            return;
        }

        // Get WebSocket URL via apps.connections.open
        const resp = await fetch(`${SLACK_API}/apps.connections.open`, {
            method: "POST",
            headers: {
                Authorization: `Bearer ${this.creds.appToken}`,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        });
        const data = await resp.json() as any;
        if (!data.ok) {
            this.emit("error", new Error(`[Slack] Cannot open connection: ${data.error}`));
            return;
        }

        this.ws = new WebSocket(data.url);

        this.ws.on("open", () => {
            this.connected = true;
            this.emit("connected");
            console.log("[Slack] Socket Mode connected");
            this.pingInterval = setInterval(() => {
                this.ws?.send(JSON.stringify({ type: "ping" }));
            }, 30_000);
        });

        this.ws.on("message", async (raw) => {
            try {
                const event = JSON.parse(raw.toString());
                await this.handleEvent(event);
            } catch { /* ignore */ }
        });

        this.ws.on("close", () => {
            this.connected = false;
            if (this.pingInterval) { clearInterval(this.pingInterval); this.pingInterval = null; }
            this.emit("disconnected");
        });

        this.ws.on("error", (err) => this.emit("error", err));
    }

    private async handleEvent(event: any): Promise<void> {
        // ACK events to Slack
        if (event.envelope_id) {
            this.ws?.send(JSON.stringify({ envelope_id: event.envelope_id }));
        }

        const payload = event.payload;
        if (!payload) return;

        if (payload.type === "event_callback") {
            const e = payload.event;
            if (e.type === "message" && !e.bot_id && e.text) {
                const inbound: InboundMessage = {
                    id: e.client_msg_id ?? e.ts,
                    channelId: this.id,
                    domain: this.defaultDomain,
                    senderId: e.user ?? "unknown",
                    threadId: e.channel,
                    groupId: payload.team_id,
                    text: e.text,
                    timestamp: Math.floor(parseFloat(e.ts) * 1000),
                    isEncrypted: false,
                    rawPayload: e,
                };
                this.emit("message", inbound);
            }
        }
    }

    async disconnect(): Promise<void> {
        this.connected = false;
        if (this.pingInterval) { clearInterval(this.pingInterval); this.pingInterval = null; }
        if (this.ws) { this.ws.close(); this.ws = null; }
        this.emit("disconnected");
    }

    async send(message: OutboundMessage): Promise<void> {
        if (!this.connected) throw new Error("Slack adapter not connected");
        await this.slackApi("chat.postMessage", {
            channel: message.threadId ?? message.recipientId,
            text: message.text,
        });
    }

    /** Show setup instructions + QR */
    async setup(appToken: string, botToken: string): Promise<void> {
        const dir = path.dirname(CREDS_PATH);
        fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
        fs.writeFileSync(CREDS_PATH, JSON.stringify({ appToken, botToken }, null, 2), { mode: 0o600 });
        const appUrl = "https://api.slack.com/apps";
        console.log(`\n[Slack] Credentials saved. Manage your app at:\n  ${appUrl}\n`);
        let qrcode: any;
        try {
            qrcode = await import("qrcode-terminal");
            (qrcode.default ?? qrcode).generate(appUrl, { small: true });
        } catch { /* ignore */ }
    }

    isConnected(): boolean { return this.connected; }
}
