/**
 * Cell 0 OS — Microsoft Teams Adapter
 *
 * Outbound: Teams incoming webhook (no auth required per webhook).
 * Inbound: Requires Azure Bot Service + public endpoint.
 *
 * Setup: Teams → Channel → Connectors → Incoming Webhook → Copy URL
 * Run: cell0 configure channels msteams
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

const CREDS_PATH = path.join(os.homedir(), ".cell0", "credentials", "msteams", "creds.json");

export class MSTeamsAdapter extends EventEmitter implements ChannelAdapter {
    public readonly id = "msteams";
    public readonly defaultDomain: ChannelDomain = "productivity";
    private connected = false;
    private webhookUrl: string | null = null;

    async connect(): Promise<void> {
        if (fs.existsSync(CREDS_PATH)) {
            const creds = JSON.parse(fs.readFileSync(CREDS_PATH, "utf-8")) as { webhookUrl: string };
            this.webhookUrl = creds.webhookUrl ?? null;
        }
        if (!this.webhookUrl) {
            console.warn("[MS Teams] No webhook URL. Run: cell0 configure channels msteams");
            return;
        }
        this.connected = true;
        this.emit("connected");
        console.log("[MS Teams] ✅ Webhook configured (outbound only)");
    }

    async disconnect(): Promise<void> {
        this.connected = false;
        this.emit("disconnected");
    }

    async send(message: OutboundMessage): Promise<void> {
        if (!this.webhookUrl) throw new Error("MS Teams not configured");
        const resp = await fetch(this.webhookUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                text: message.text,
            }),
        });
        if (!resp.ok) throw new Error(`Teams webhook ${resp.status}: ${await resp.text()}`);
    }

    isConnected(): boolean { return this.connected; }
}
