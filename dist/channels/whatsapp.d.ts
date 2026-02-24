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
import { type ChannelAdapter, type OutboundMessage, type ChannelDomain } from "./adapter.js";
export declare class WhatsAppAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "whatsapp";
    readonly defaultDomain: ChannelDomain;
    private sock;
    private connected;
    private reconnectAttempts;
    private maxReconnectAttempts;
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
    /** Called during onboarding to display QR in terminal */
    showSetupQR(): Promise<void>;
    isConnected(): boolean;
}
//# sourceMappingURL=whatsapp.d.ts.map