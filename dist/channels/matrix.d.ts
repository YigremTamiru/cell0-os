/**
 * Cell 0 OS — Matrix Channel Adapter
 *
 * Uses Matrix Client-Server API via native fetch (no external SDK).
 * Connects to any Matrix homeserver (matrix.org, Element, self-hosted).
 *
 * Setup: cell0 configure channels matrix
 */
import { EventEmitter } from "node:events";
import { type ChannelAdapter, type OutboundMessage, type ChannelDomain } from "./adapter.js";
export declare class MatrixAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "matrix";
    readonly defaultDomain: ChannelDomain;
    private connected;
    private creds;
    private syncToken;
    private syncTimer;
    private loadCreds;
    private matrixApi;
    connect(): Promise<void>;
    private startSync;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
    isConnected(): boolean;
}
//# sourceMappingURL=matrix.d.ts.map