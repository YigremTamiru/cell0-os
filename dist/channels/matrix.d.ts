import { EventEmitter } from 'node:events';
import { ChannelAdapter, OutboundMessage, ChannelDomain } from './adapter.js';
/**
 * Matrix Protocol Adapter
 * Natively supports E2E encryption for rooms.
 */
export declare class MatrixAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "matrix";
    readonly defaultDomain: ChannelDomain;
    private connected;
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
}
//# sourceMappingURL=matrix.d.ts.map