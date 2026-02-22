import { EventEmitter } from 'node:events';
export class GoogleChatAdapter extends EventEmitter {
    id = 'google-chat';
    defaultDomain = 'productivity';
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
            throw new Error('Google Chat adapter not connected');
    }
}
//# sourceMappingURL=google-chat.js.map