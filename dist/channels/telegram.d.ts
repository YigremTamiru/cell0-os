/**
 * Cell 0 OS — Telegram Channel Adapter
 *
 * Uses the Telegram Bot API via native Node.js fetch (no external SDK).
 * Bot token is obtained from @BotFather and stored in ~/.cell0/credentials/telegram/creds.json
 *
 * Setup flow:
 *   1. Message @BotFather → /newbot → copy token
 *   2. cell0 onboard → selects Telegram → pastes token
 *   3. QR code of t.me/<botname> shown for phone scan
 */
import { EventEmitter } from "node:events";
import { type ChannelAdapter, type OutboundMessage, type ChannelDomain } from "./adapter.js";
export declare class TelegramAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "telegram";
    readonly defaultDomain: ChannelDomain;
    private connected;
    private creds;
    private pollOffset;
    private pollTimer;
    private get apiBase();
    private api;
    private loadCreds;
    connect(): Promise<void>;
    private startPolling;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
    /** Called by wizard to save token and show setup QR */
    setup(token: string): Promise<void>;
    isConnected(): boolean;
}
//# sourceMappingURL=telegram.d.ts.map