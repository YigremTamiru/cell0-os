/**
 * Cell 0 OS — BlueBubbles Channel Adapter
 *
 * Connects to a BlueBubbles server (Mac-hosted iMessage proxy) via REST + WebSocket.
 * BlueBubbles bypasses Apple's iMessage restrictions for cross-platform access.
 *
 * Setup:
 *   1. Install BlueBubbles on a Mac: https://bluebubbles.app
 *   2. Enable HTTP API: BlueBubbles → Settings → Private API
 *   3. Run: cell0 configure channels bluebubbles
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

const CREDS_PATH = path.join(os.homedir(), ".cell0", "credentials", "bluebubbles", "creds.json");

interface BBCreds {
    serverUrl: string;
    serverPass: string;
}

export class BlueBubblesAdapter extends EventEmitter implements ChannelAdapter {
    public readonly id = "bluebubbles";
    public readonly defaultDomain: ChannelDomain = "social";
    public connected = false;
    private creds: BBCreds | null = null;
    private ws: WebSocket | null = null;

    private loadCreds(): BBCreds | null {
        if (!fs.existsSync(CREDS_PATH)) return null;
        try { return JSON.parse(fs.readFileSync(CREDS_PATH, "utf-8")) as BBCreds; }
        catch { return null; }
    }

    async connect(): Promise<void> {
        this.creds = this.loadCreds();
        if (!this.creds) {
            console.warn("[BlueBubbles] Not configured. Run: cell0 configure channels bluebubbles");
            return;
        }

        const wsUrl = this.creds.serverUrl
            .replace("https://", "wss://")
            .replace("http://", "ws://");

        this.ws = new WebSocket(`${wsUrl}/socket.io/?v=3&transport=websocket`);

        this.ws.on("open", () => {
            this.ws!.send(JSON.stringify({ type: "hello", data: { serverPass: this.creds!.serverPass } }));
        });

        this.ws.on("message", (raw) => {
            try {
                const msg = JSON.parse(raw.toString());
                if (msg.type === "welcome") {
                    this.connected = true;
                    this.emit("connected");
                    console.log("[BlueBubbles] ✅ Connected to iMessage proxy");
                }
                if (msg.type === "new-message" && msg.data) {
                    const d = msg.data;
                    const inbound: InboundMessage = {
                        id: d.guid,
                        channelId: this.id,
                        domain: this.defaultDomain,
                        senderId: d.handle?.id ?? "unknown",
                        senderName: d.handle?.id,
                        threadId: d.chats?.[0]?.guid,
                        text: d.text ?? "",
                        timestamp: d.dateCreated ?? Date.now(),
                        isEncrypted: false,
                        rawPayload: d,
                    };
                    this.emit("message", inbound);
                }
            } catch { /* ignore */ }
        });

        this.ws.on("close", () => {
            this.connected = false;
            this.emit("disconnected");
        });

        this.ws.on("error", (err) => this.emit("error", err));
    }

    async disconnect(): Promise<void> {
        this.connected = false;
        if (this.ws) { this.ws.close(); this.ws = null; }
        this.emit("disconnected");
    }

    async send(message: OutboundMessage): Promise<void> {
        if (!this.connected || !this.creds) throw new Error("BlueBubbles not connected");
        const resp = await fetch(`${this.creds.serverUrl}/api/v1/message/text`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "x-server-pass": this.creds.serverPass,
            },
            body: JSON.stringify({
                chatGuid: message.threadId ?? message.recipientId,
                message: message.text,
                method: "apple-script",
                tempGuid: `temp.${Date.now()}`,
            }),
        });
        if (!resp.ok) throw new Error(`BlueBubbles send error: ${resp.status}`);
    }

    isConnected(): boolean { return this.connected; }
}
