import { EventEmitter } from 'node:events';
import { ChannelAdapter, OutboundMessage, ChannelDomain } from './adapter.js';
/**
 * Signal Channel Adapter
 * Wraps cell0/integrations/signal_bot.py.
 * Signal is natively E2E encrypted, so all parsed messages are marked isEncrypted: true.
 */
export declare class SignalAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "signal";
    readonly defaultDomain: ChannelDomain;
    private connected;
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
}
//# sourceMappingURL=signal.d.ts.map