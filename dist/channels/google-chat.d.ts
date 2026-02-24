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
import { type ChannelAdapter, type OutboundMessage, type ChannelDomain } from "./adapter.js";
export declare class GoogleChatAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "google-chat";
    readonly defaultDomain: ChannelDomain;
    private connected;
    private webhookUrl;
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
    isConnected(): boolean;
}
//# sourceMappingURL=google-chat.d.ts.map