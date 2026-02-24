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
import { type ChannelAdapter, type OutboundMessage, type ChannelDomain } from "./adapter.js";
export declare class DiscordAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "discord";
    readonly defaultDomain: ChannelDomain;
    private connected;
    private creds;
    private ws;
    private heartbeatInterval;
    private sessionId;
    private lastSeq;
    private resumeGatewayUrl;
    private loadCreds;
    private discordApi;
    connect(): Promise<void>;
    private connectGateway;
    private handlePayload;
    private startHeartbeat;
    private identify;
    private handleDispatch;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
    /** Show setup QR with bot invite link */
    setup(botToken: string): Promise<void>;
    isConnected(): boolean;
}
//# sourceMappingURL=discord.d.ts.map