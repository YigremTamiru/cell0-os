import { EventEmitter } from 'node:events';
import { ChannelAdapter, OutboundMessage, ChannelDomain } from './adapter.js';
/**
 * WebChat Adapter
 * Connects directly to the Cell 0 OS Gateway WebSocket server (e.g., from the Portal or mobile apps).
 * Payloads sent over WSS are TLS encrypted, but we can enforce payload E2E if configured.
 */
export declare class WebChatAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "webchat";
    readonly defaultDomain: ChannelDomain;
    private connected;
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
}
//# sourceMappingURL=webchat.d.ts.map