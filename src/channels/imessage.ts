/**
 * Cell 0 OS — iMessage Adapter
 *
 * Delegates to BlueBubblesAdapter — the only viable cross-platform iMessage bridge.
 * BlueBubbles runs on a Mac and proxies iMessage to Cell 0 OS over LAN.
 *
 * Setup: cell0 configure channels bluebubbles (configures both bluebubbles and imessage)
 */

import { EventEmitter } from "node:events";
import {
    type ChannelAdapter,
    type InboundMessage,
    type OutboundMessage,
    type ChannelDomain,
} from "./adapter.js";
import { BlueBubblesAdapter } from "./bluebubbles.js";

export class IMessageAdapter extends EventEmitter implements ChannelAdapter {
    public readonly id = "imessage";
    public readonly defaultDomain: ChannelDomain = "social";
    private proxy: BlueBubblesAdapter;

    constructor() {
        super();
        this.proxy = new BlueBubblesAdapter();
        this.proxy.on("message", (msg: InboundMessage) =>
            this.emit("message", { ...msg, channelId: "imessage" })
        );
        this.proxy.on("connected", () => this.emit("connected"));
        this.proxy.on("disconnected", () => this.emit("disconnected"));
        this.proxy.on("error", (err: Error) => this.emit("error", err));
    }

    async connect(): Promise<void> { return this.proxy.connect(); }
    async disconnect(): Promise<void> { return this.proxy.disconnect(); }
    async send(message: OutboundMessage): Promise<void> {
        return this.proxy.send({ ...message, channelId: "bluebubbles" });
    }
    isConnected(): boolean { return this.proxy.connected; }
}
