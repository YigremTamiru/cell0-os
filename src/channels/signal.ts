import { EventEmitter } from 'node:events';
import { ChannelAdapter, InboundMessage, OutboundMessage, ChannelDomain } from './adapter.js';
// TODO: Import Python bridge IPC mechanisms when ready to wrap signal_bot.py

/**
 * Signal Channel Adapter
 * Wraps cell0/integrations/signal_bot.py. 
 * Signal is natively E2E encrypted, so all parsed messages are marked isEncrypted: true.
 */
export class SignalAdapter extends EventEmitter implements ChannelAdapter {
    public readonly id = 'signal';
    public readonly defaultDomain: ChannelDomain = 'social';
    private connected = false;

    async connect(): Promise<void> {
        // TODO: Start or connect to the running signal_bot.py subprocess
        this.connected = true;
        this.emit('connected');
    }

    async disconnect(): Promise<void> {
        // TODO: Signal proper shutdown to signal_bot.py
        this.connected = false;
        this.emit('disconnected');
    }

    async send(message: OutboundMessage): Promise<void> {
        if (!this.connected) throw new Error('Signal adapter not connected');
        // TODO: IPC send to signal_bot.py
        // Note: Signal messages are E2E encrypted natively by the client
    }
}
