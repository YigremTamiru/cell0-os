import { EventEmitter } from 'node:events';
import { ChannelAdapter, OutboundMessage, ChannelDomain } from './adapter.js';
/**
 * WhatsApp Channel Adapter (Stub)
 * Natively supports End-to-End Encryption.
 */
export declare class WhatsAppAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "whatsapp";
    readonly defaultDomain: ChannelDomain;
    private connected;
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
}
//# sourceMappingURL=whatsapp.d.ts.map