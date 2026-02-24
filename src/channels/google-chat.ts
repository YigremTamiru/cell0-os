/**
 * Cell 0 OS — Google Chat Adapter
 *
 * Outbound: Google Chat incoming webhooks (no auth required per webhook).
 * Inbound: Requires Google Cloud Pub/Sub or Cloud Run webhook endpoint.
 *
 * Setup: Google Chat → Manage webhooks → Copy webhook URL
 * Run: cell0 configure channels google-chat
 */

import { EventEmitter } from "node:events";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import {
    type ChannelAdapter,
    type InboundMessage,
    type OutboundMessage,
    type ChannelDomain,
} from "./adapter.js";

const CREDS_PATH = path.join(os.homedir(), ".cell0", "credentials", "google-chat", "creds.json");

export class GoogleChatAdapter extends EventEmitter implements ChannelAdapter {
    public readonly id = "google-chat";
    public readonly defaultDomain: ChannelDomain = "productivity";
    private connected = false;
    private webhookUrl: string | null = null;

    async connect(): Promise<void> {
        if (fs.existsSync(CREDS_PATH)) {
            const creds = JSON.parse(fs.readFileSync(CREDS_PATH, "utf-8")) as { webhookUrl: string };
            this.webhookUrl = creds.webhookUrl ?? null;
        }
        if (!this.webhookUrl) {
            console.warn("[Google Chat] No webhook URL. Run: cell0 configure channels google-chat");
            return;
        }
        this.connected = true;
        this.emit("connected");
        console.log("[Google Chat] ✅ Webhook configured (outbound only)");
    }

    async disconnect(): Promise<void> {
        this.connected = false;
        this.emit("disconnected");
    }

    async send(message: OutboundMessage): Promise<void> {
        if (!this.webhookUrl) throw new Error("Google Chat not configured");
        const resp = await fetch(this.webhookUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: message.text }),
        });
        if (!resp.ok) throw new Error(`Google Chat webhook ${resp.status}: ${await resp.text()}`);
    }

    isConnected(): boolean { return this.connected; }
}
