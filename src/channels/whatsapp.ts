/**
 * Cell 0 OS — WhatsApp Channel Adapter
 *
 * Uses @whiskeysockets/baileys (WhatsApp Web protocol) for QR-code pairing.
 * No Meta developer account required — pairs like WhatsApp Web.
 *
 * Setup flow:
 *   1. cell0 onboard  → selects WhatsApp → QR code displayed in terminal
 *   2. User scans with WhatsApp on phone
 *   3. Session saved to ~/.cell0/credentials/whatsapp/
 *   4. Adapter auto-connects on gateway start
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

const CREDS_DIR = path.join(os.homedir(), ".cell0", "credentials", "whatsapp");

export class WhatsAppAdapter extends EventEmitter implements ChannelAdapter {
    public readonly id = "whatsapp";
    public readonly defaultDomain: ChannelDomain = "social";
    private sock: any = null;
    private connected = false;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;

    async connect(): Promise<void> {
        let baileys: any;
        try {
            baileys = await import("@whiskeysockets/baileys").catch(() => null);
        } catch {
            baileys = null;
        }

        if (!baileys) {
            console.warn(
                "[WhatsApp] @whiskeysockets/baileys not installed.\n" +
                "  Run: npm install -g @whiskeysockets/baileys\n" +
                "  Then restart: cell0 daemon restart"
            );
            return;
        }

        const makeWASocket = baileys.default?.default ?? baileys.default ?? baileys.makeWASocket;
        const { useMultiFileAuthState, Browsers, DisconnectReason } = baileys.default ?? baileys;

        fs.mkdirSync(CREDS_DIR, { recursive: true, mode: 0o700 });
        const { state, saveCreds } = await useMultiFileAuthState(CREDS_DIR);

        this.sock = makeWASocket({
            auth: state,
            printQRInTerminal: true,
            browser: Browsers.ubuntu("Cell 0 OS"),
            logger: { level: "silent", child: () => ({ level: "silent", trace: () => {}, debug: () => {}, info: () => {}, warn: () => {}, error: () => {}, fatal: () => {} }) },
            connectTimeoutMs: 60_000,
            defaultQueryTimeoutMs: 60_000,
        });

        this.sock.ev.on("creds.update", saveCreds);

        this.sock.ev.on("connection.update", (update: any) => {
            const { connection, lastDisconnect, qr } = update;

            if (qr) {
                // Emit QR for wizard / portal display
                this.emit("qr", qr);
            }

            if (connection === "open") {
                this.connected = true;
                this.reconnectAttempts = 0;
                this.emit("connected");
                console.log("\n[WhatsApp] ✅ Paired and connected\n");
            }

            if (connection === "close") {
                this.connected = false;
                const statusCode = (lastDisconnect?.error as any)?.output?.statusCode;
                const loggedOut = statusCode === (DisconnectReason?.loggedOut ?? 401);

                if (loggedOut) {
                    console.log("[WhatsApp] Logged out — clearing credentials");
                    fs.rmSync(CREDS_DIR, { recursive: true, force: true });
                    this.emit("disconnected");
                } else if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    const delay = Math.min(3000 * this.reconnectAttempts, 30_000);
                    console.log(`[WhatsApp] Reconnecting in ${delay / 1000}s (attempt ${this.reconnectAttempts})...`);
                    setTimeout(() => this.connect(), delay);
                } else {
                    this.emit("disconnected");
                    this.emit("error", new Error("WhatsApp max reconnect attempts exceeded"));
                }
            }
        });

        this.sock.ev.on("messages.upsert", ({ messages, type }: any) => {
            if (type !== "notify") return;
            for (const msg of messages) {
                if (!msg.message || msg.key.fromMe) continue;
                const text =
                    msg.message.conversation ??
                    msg.message.extendedTextMessage?.text ??
                    msg.message.imageMessage?.caption ??
                    "";
                if (!text.trim()) continue;

                const inbound: InboundMessage = {
                    id: msg.key.id ?? Date.now().toString(),
                    channelId: this.id,
                    domain: this.defaultDomain,
                    senderId: msg.key.remoteJid ?? "unknown",
                    senderName: msg.pushName ?? undefined,
                    text,
                    groupId: msg.key.remoteJid?.endsWith("@g.us")
                        ? msg.key.remoteJid
                        : undefined,
                    timestamp: Number(msg.messageTimestamp ?? Date.now() / 1000) * 1000,
                    isEncrypted: true,
                    rawPayload: msg,
                };
                this.emit("message", inbound);
            }
        });
    }

    async disconnect(): Promise<void> {
        if (this.sock) {
            try {
                await this.sock.logout();
            } catch {
                // Ignore logout errors
            }
            this.sock = null;
        }
        this.connected = false;
        this.emit("disconnected");
    }

    async send(message: OutboundMessage): Promise<void> {
        if (!this.connected || !this.sock) {
            throw new Error("WhatsApp adapter not connected");
        }
        await this.sock.sendMessage(message.recipientId, {
            text: message.text,
        });
    }

    /** Called during onboarding to display QR in terminal */
    async showSetupQR(): Promise<void> {
        let qrcode: any;
        try {
            qrcode = await import("qrcode-terminal");
        } catch {
            console.warn("[WhatsApp] qrcode-terminal not available");
            return;
        }
        console.log("\n[WhatsApp] Starting QR pairing...");
        console.log("  Open WhatsApp → Settings → Linked Devices → Link a Device\n");
        await this.connect(); // Will print QR via printQRInTerminal: true
    }

    isConnected(): boolean {
        return this.connected;
    }
}
