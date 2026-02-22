import { EventEmitter } from 'node:events';
import { ChannelAdapter, OutboundMessage, ChannelDomain } from './adapter.js';
export declare class SlackAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "slack";
    readonly defaultDomain: ChannelDomain;
    private connected;
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
}
//# sourceMappingURL=slack.d.ts.map