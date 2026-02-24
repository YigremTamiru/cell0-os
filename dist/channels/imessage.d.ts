/**
 * Cell 0 OS — iMessage Adapter
 *
 * Delegates to BlueBubblesAdapter — the only viable cross-platform iMessage bridge.
 * BlueBubbles runs on a Mac and proxies iMessage to Cell 0 OS over LAN.
 *
 * Setup: cell0 configure channels bluebubbles (configures both bluebubbles and imessage)
 */
import { EventEmitter } from "node:events";
import { type ChannelAdapter, type OutboundMessage, type ChannelDomain } from "./adapter.js";
export declare class IMessageAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "imessage";
    readonly defaultDomain: ChannelDomain;
    private proxy;
    constructor();
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
    isConnected(): boolean;
}
//# sourceMappingURL=imessage.d.ts.map