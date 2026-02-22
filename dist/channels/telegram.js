import { EventEmitter } from 'node:events';
export class TelegramAdapter extends EventEmitter {
    id = 'telegram';
    defaultDomain = 'social';
    connected = false;
    async connect() {
        this.connected = true;
        this.emit('connected');
    }
    async disconnect() {
        this.connected = false;
        this.emit('disconnected');
    }
    async send(message) {
        if (!this.connected)
            throw new Error('Telegram adapter not connected');
    }
}
//# sourceMappingURL=telegram.js.map