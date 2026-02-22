import { EventEmitter } from 'node:events';
export class SlackAdapter extends EventEmitter {
    id = 'slack';
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
            throw new Error('Slack adapter not connected');
    }
}
//# sourceMappingURL=slack.js.map