/**
 * Cell 0 OS — Presence Tracker
 *
 * Wraps cell0/service/presence.py
 * Tracks the multi-device connected states across the OS mesh.
 */
export class PresenceManager {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Pings the internal Python broker to announce this Node layer's connection state.
     */
    async heartbeat(deviceId, isOnline) {
        if (!this.bridge.isReady())
            return false;
        try {
            const res = await this.bridge.post("/api/presence/heartbeat", {
                deviceId,
                status: isOnline ? "online" : "offline"
            });
            return res.success ?? true;
        }
        catch {
            return false;
        }
    }
    /**
     * Polls the master presence database to discover who is connected across the network.
     */
    async getGlobalState() {
        if (!this.bridge.isReady())
            return [];
        try {
            const res = await this.bridge.post("/api/presence/list", {});
            return res.states || [];
        }
        catch {
            return [];
        }
    }
}
//# sourceMappingURL=presence.js.map