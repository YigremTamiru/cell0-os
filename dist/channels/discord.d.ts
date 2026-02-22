import { EventEmitter } from 'node:events';
import { ChannelAdapter, OutboundMessage, ChannelDomain } from './adapter.js';
export declare class DiscordAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "discord";
    readonly defaultDomain: ChannelDomain;
    private connected;
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
}
//# sourceMappingURL=discord.d.ts.map