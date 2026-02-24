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
import { type ChannelAdapter, type OutboundMessage, type ChannelDomain } from "./adapter.js";
export declare class MSTeamsAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "msteams";
    readonly defaultDomain: ChannelDomain;
    private connected;
    private webhookUrl;
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
    isConnected(): boolean;
}
//# sourceMappingURL=msteams.d.ts.map