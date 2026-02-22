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
export declare class PresenceManager {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Pings the internal Python broker to announce this Node layer's connection state.
     */
    heartbeat(deviceId: string, isOnline: boolean): Promise<boolean>;
    /**
     * Polls the master presence database to discover who is connected across the network.
     */
    getGlobalState(): Promise<PresenceState[]>;
}
//# sourceMappingURL=presence.d.ts.map