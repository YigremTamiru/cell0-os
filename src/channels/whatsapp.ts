import { EventEmitter } from 'node:events';
import { ChannelAdapter, InboundMessage, OutboundMessage, ChannelDomain } from './adapter.js';

/**
 * WhatsApp Channel Adapter (Stub)
 * Natively supports End-to-End Encryption.
 */
export class WhatsAppAdapter extends EventEmitter implements ChannelAdapter {
    public readonly id = 'whatsapp';
    public readonly defaultDomain: ChannelDomain = 'social';
    private connected = false;

    async connect(): Promise<void> {
        // TODO: Implement actual WhatsApp Web/Business API connection
        this.connected = true;
        this.emit('connected');
    }

    async disconnect(): Promise<void> {
        this.connected = false;
        this.emit('disconnected');
    }

    async send(message: OutboundMessage): Promise<void> {
        if (!this.connected) throw new Error('WhatsApp adapter not connected');
        // TODO: Implement sending logic
    }
}
