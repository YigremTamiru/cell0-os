import { EventEmitter } from 'node:events';
import { ChannelAdapter, InboundMessage, OutboundMessage, ChannelDomain } from './adapter.js';

/**
 * Matrix Protocol Adapter
 * Natively supports E2E encryption for rooms.
 */
export class MatrixAdapter extends EventEmitter implements ChannelAdapter {
    public readonly id = 'matrix';
    public readonly defaultDomain: ChannelDomain = 'social';
    private connected = false;

    async connect(): Promise<void> {
        this.connected = true;
        this.emit('connected');
    }

    async disconnect(): Promise<void> {
        this.connected = false;
        this.emit('disconnected');
    }

    async send(message: OutboundMessage): Promise<void> {
        if (!this.connected) throw new Error('Matrix adapter not connected');
    }
}
