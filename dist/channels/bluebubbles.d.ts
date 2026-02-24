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
import { type ChannelAdapter, type OutboundMessage, type ChannelDomain } from "./adapter.js";
export declare class BlueBubblesAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "bluebubbles";
    readonly defaultDomain: ChannelDomain;
    connected: boolean;
    private creds;
    private ws;
    private loadCreds;
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
    isConnected(): boolean;
}
//# sourceMappingURL=bluebubbles.d.ts.map