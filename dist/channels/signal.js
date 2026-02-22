import { EventEmitter } from 'node:events';
// TODO: Import Python bridge IPC mechanisms when ready to wrap signal_bot.py
/**
 * Signal Channel Adapter
 * Wraps cell0/integrations/signal_bot.py.
 * Signal is natively E2E encrypted, so all parsed messages are marked isEncrypted: true.
 */
export class SignalAdapter extends EventEmitter {
    id = 'signal';
    defaultDomain = 'social';
    connected = false;
    async connect() {
        // TODO: Start or connect to the running signal_bot.py subprocess
        this.connected = true;
        this.emit('connected');
    }
    async disconnect() {
        // TODO: Signal proper shutdown to signal_bot.py
        this.connected = false;
        this.emit('disconnected');
    }
    async send(message) {
        if (!this.connected)
            throw new Error('Signal adapter not connected');
        // TODO: IPC send to signal_bot.py
        // Note: Signal messages are E2E encrypted natively by the client
    }
}
//# sourceMappingURL=signal.js.map