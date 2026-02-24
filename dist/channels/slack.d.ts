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
import { type ChannelAdapter, type OutboundMessage, type ChannelDomain } from "./adapter.js";
export declare class SlackAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "slack";
    readonly defaultDomain: ChannelDomain;
    private connected;
    private creds;
    private ws;
    private pingInterval;
    private loadCreds;
    private slackApi;
    connect(): Promise<void>;
    private handleEvent;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
    /** Show setup instructions + QR */
    setup(appToken: string, botToken: string): Promise<void>;
    isConnected(): boolean;
}
//# sourceMappingURL=slack.d.ts.map