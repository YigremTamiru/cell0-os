import { EventEmitter } from 'node:events';
export class IMessageAdapter extends EventEmitter {
    id = 'imessage';
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
            throw new Error('iMessage adapter not connected');
    }
}
//# sourceMappingURL=imessage.js.map