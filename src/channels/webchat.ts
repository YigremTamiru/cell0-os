import { EventEmitter } from 'node:events';
import { ChannelAdapter, InboundMessage, OutboundMessage, ChannelDomain } from './adapter.js';

/**
 * WebChat Adapter
 * Connects directly to the Cell 0 OS Gateway WebSocket server (e.g., from the Portal or mobile apps).
 * Payloads sent over WSS are TLS encrypted, but we can enforce payload E2E if configured.
 */
export class WebChatAdapter extends EventEmitter implements ChannelAdapter {
    public readonly id = 'webchat';
    public readonly defaultDomain: ChannelDomain = 'system'; // Default to system/root access for the portal
    private connected = false;

    async connect(): Promise<void> {
        // Automatically considered connected since it rides on the Gateway WS
        this.connected = true;
        this.emit('connected');
    }

    async disconnect(): Promise<void> {
        this.connected = false;
        this.emit('disconnected');
    }

    async send(message: OutboundMessage): Promise<void> {
        if (!this.connected) throw new Error('WebChat adapter not connected');
        // Will route messages back to connected WS clients via gateway/index.ts
    }
}
