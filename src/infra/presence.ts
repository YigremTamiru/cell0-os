/**
 * Cell 0 OS — Presence Tracker
 *
 * Wraps cell0/service/presence.py
 * Tracks the multi-device connected states across the OS mesh.
 */

import { PythonBridge } from "../agents/python-bridge.js";

export interface PresenceState {
    deviceId: string;
    alias: string;
    status: "online" | "away" | "dnd" | "offline";
    channel: string;
    lastSeen: string;
}

export class PresenceManager {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Pings the internal Python broker to announce this Node layer's connection state.
     */
    async heartbeat(deviceId: string, isOnline: boolean): Promise<boolean> {
        if (!this.bridge.isReady()) return false;
        try {
            const res = await this.bridge.post<any>("/api/presence/heartbeat", {
                deviceId,
                status: isOnline ? "online" : "offline"
            });
            return res.success ?? true;
        } catch {
            return false;
        }
    }

    /**
     * Polls the master presence database to discover who is connected across the network.
     */
    async getGlobalState(): Promise<PresenceState[]> {
        if (!this.bridge.isReady()) return [];
        try {
            const res = await this.bridge.post<{ states: PresenceState[] }>("/api/presence/list", {});
            return res.states || [];
        } catch {
            return [];
        }
    }
}
