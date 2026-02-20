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
    channelId: string; // The ID of the adapter (e.g., 'whatsapp', 'signal', 'slack')
    domain: ChannelDomain;

    // Sender Information
    senderId: string;
    senderName?: string;

    // Context
    threadId?: string;
    groupId?: string;

    // Payload
    text: string;
    attachments?: Array<{ type: string; url: string; mime: string }>;

    // Timestamp
    timestamp: number;

    // Security / E2E
    isEncrypted: boolean;
    encryptionMetadata?: Record<string, any>;

    // Raw original payload for deep debugging if needed
    rawPayload?: any;
}

/**
 * Represents a standard outgoing message to be formatted and sent via an adapter.
 */
export interface OutboundMessage {
    channelId: string;
    recipientId: string; // User ID, Phone Number, or Group ID

    // Context
    threadId?: string;
    groupId?: string;

    // Payload
    text: string;
    attachments?: Array<{ type: string; url: string; mime: string }>;

    // Security / E2E directive
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

    // Event Emitter Signatures
    on(event: 'message', listener: (msg: InboundMessage) => void): this;
    on(event: 'connected', listener: () => void): this;
    on(event: 'disconnected', listener: () => void): this;
    on(event: 'error', listener: (error: Error) => void): this;
}
