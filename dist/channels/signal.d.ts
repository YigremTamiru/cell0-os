/**
 * Cell 0 OS — Signal Channel Adapter
 *
 * Wraps signal-cli (https://github.com/AsamK/signal-cli) via JSON-RPC stdio.
 * signal-cli must be installed separately (requires Java 17+).
 *
 * Setup:
 *   1. Install signal-cli: https://github.com/AsamK/signal-cli/releases
 *   2. Register: signal-cli register -u +1234567890
 *   3. Verify: signal-cli verify -u +1234567890 --verificationCode 123-456
 *   4. Run: cell0 configure channels signal
 */
import { EventEmitter } from "node:events";
import { type ChannelAdapter, type OutboundMessage, type ChannelDomain } from "./adapter.js";
export declare class SignalAdapter extends EventEmitter implements ChannelAdapter {
    readonly id = "signal";
    readonly defaultDomain: ChannelDomain;
    private connected;
    private creds;
    private proc;
    private rpcId;
    private loadCreds;
    private findSignalCli;
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    send(message: OutboundMessage): Promise<void>;
    isConnected(): boolean;
}
//# sourceMappingURL=signal.d.ts.map