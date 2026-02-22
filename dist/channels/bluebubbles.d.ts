import { EventEmitter } from 'node:events';
import { ChannelAdapter, OutboundMessage, ChannelDomain } from './adapter.js';
export declare class BlueBubblesAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "bluebubbles";
    readonly defaultDomain: ChannelDomain;
    private connected;
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
}
//# sourceMappingURL=bluebubbles.d.ts.map