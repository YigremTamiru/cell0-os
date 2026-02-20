import { EventEmitter } from 'node:events';
import { ChannelAdapter, InboundMessage, OutboundMessage, ChannelDomain } from './adapter.js';

export class TelegramAdapter extends EventEmitter implements ChannelAdapter {
    public readonly id = 'telegram';
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
        if (!this.connected) throw new Error('Telegram adapter not connected');
    }
}
