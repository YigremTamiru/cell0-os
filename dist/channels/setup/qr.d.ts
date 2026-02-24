/**
 * Cell 0 OS — Channel QR Setup Utility
 *
 * Displays QR codes in the terminal for channel pairing flows.
 * Used by the onboarding wizard and `cell0 configure channels` command.
 */
export interface ChannelCredentials {
    channelId: string;
    paired: boolean;
    pairedAt?: string;
    metadata?: Record<string, unknown>;
}
export declare const CREDS_BASE: string;
export declare function isChannelPaired(channelId: string): boolean;
export declare function showQRInTerminal(data: string, label: string): Promise<void>;
export declare function showOAuthQR(channelId: string, authUrl: string): Promise<void>;
export declare function saveChannelCreds(channelId: string, data: Record<string, unknown>): void;
export declare function loadChannelCreds(channelId: string): Record<string, unknown> | null;
//# sourceMappingURL=qr.d.ts.map