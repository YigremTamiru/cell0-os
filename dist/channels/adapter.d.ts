import { EventEmitter } from 'node:events';
/**
 * Represents the fundamental origin or destination domain for a message.
 * This determines which cognitive layer and vector memory the message interacts with.
 */
export type ChannelDomain = 'social' | 'productivity' | 'utilities' | 'finance' | 'travel' | 'creativity' | 'information' | 'entertainment' | 'system';
/**
 * Represents a standard incoming message parsed from a channel adapter.
 */
export interface InboundMessage {
    id: string;
    channelId: string;
    domain: ChannelDomain;
    senderId: string;
    senderName?: string;
    threadId?: string;
    groupId?: string;
    text: string;
    attachments?: Array<{
        type: string;
        url: string;
        mime: string;
    }>;
    timestamp: number;
    isEncrypted: boolean;
    encryptionMetadata?: Record<string, any>;
    rawPayload?: any;
}
/**
 * Represents a standard outgoing message to be formatted and sent via an adapter.
 */
export interface OutboundMessage {
    channelId: string;
    recipientId: string;
    threadId?: string;
    groupId?: string;
    text: string;
    attachments?: Array<{
        type: string;
        url: string;
        mime: string;
    }>;
    requireEncryption?: boolean;
}
/**
 * Core interface that all 11 Channel Adapters must implement.
 * Inherits from EventEmitter to emit 'message', 'connected', 'disconnected', 'error'
 */
export interface ChannelAdapter extends EventEmitter {
    /**
     * Unique identifier for this channel integration (e.g., 'signal', 'discord')
     */
    readonly id: string;
    /**
     * The default cognitive domain this channel routes into (e.g., 'social' for WhatsApp, 'productivity' for Slack)
     */
    readonly defaultDomain: ChannelDomain;
    /**
     * Initialize the connection to the underlying network or messaging service.
     */
    connect(): Promise<void>;
    /**
     * Cleanly close the connection and release resources.
     */
    disconnect(): Promise<void>;
    /**
     * Send an outbound message to a recipient on this channel.
     * @param message The formatted OutboundMessage
     */
    send(message: OutboundMessage): Promise<void>;
    on(event: 'message', listener: (msg: InboundMessage) => void): this;
    on(event: 'connected', listener: () => void): this;
    on(event: 'disconnected', listener: () => void): this;
    on(event: 'error', listener: (error: Error) => void): this;
}
//# sourceMappingURL=adapter.d.ts.map