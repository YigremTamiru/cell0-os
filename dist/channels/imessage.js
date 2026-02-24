/**
 * Cell 0 OS — iMessage Adapter
 *
 * Delegates to BlueBubblesAdapter — the only viable cross-platform iMessage bridge.
 * BlueBubbles runs on a Mac and proxies iMessage to Cell 0 OS over LAN.
 *
 * Setup: cell0 configure channels bluebubbles (configures both bluebubbles and imessage)
 */
import { EventEmitter } from "node:events";
import { BlueBubblesAdapter } from "./bluebubbles.js";
export class IMessageAdapter extends EventEmitter {
    id = "imessage";
    defaultDomain = "social";
    proxy;
    constructor() {
        super();
        this.proxy = new BlueBubblesAdapter();
        this.proxy.on("message", (msg) => this.emit("message", { ...msg, channelId: "imessage" }));
        this.proxy.on("connected", () => this.emit("connected"));
        this.proxy.on("disconnected", () => this.emit("disconnected"));
        this.proxy.on("error", (err) => this.emit("error", err));
    }
    async connect() { return this.proxy.connect(); }
    async disconnect() { return this.proxy.disconnect(); }
    async send(message) {
        return this.proxy.send({ ...message, channelId: "bluebubbles" });
    }
    isConnected() { return this.proxy.connected; }
}
//# sourceMappingURL=imessage.js.map