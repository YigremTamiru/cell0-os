import { EventEmitter } from 'node:events';
export class MSTeamsAdapter extends EventEmitter {
    id = 'msteams';
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
            throw new Error('MS Teams adapter not connected');
    }
}
//# sourceMappingURL=msteams.js.map