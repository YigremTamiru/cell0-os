/**
 * Type stubs for optional channel dependencies.
 * These are loaded dynamically at runtime; actual types come from the packages if installed.
 */

declare module "qrcode-terminal" {
    function generate(text: string, opts?: { small?: boolean }, cb?: (qr: string) => void): void;
    export default { generate };
    export { generate };
}

declare module "@whiskeysockets/baileys" {
    import type { EventEmitter } from "node:events";
    export function makeWASocket(config: Record<string, unknown>): any;
    export function useMultiFileAuthState(dir: string): Promise<{ state: any; saveCreds: () => Promise<void> }>;
    export const Browsers: Record<string, (name: string) => string[]>;
    export const DisconnectReason: Record<string, number>;
    export default {
        makeWASocket,
        useMultiFileAuthState,
        Browsers,
        DisconnectReason,
    };
}
