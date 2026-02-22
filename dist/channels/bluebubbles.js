import { EventEmitter } from 'node:events';
export class BlueBubblesAdapter extends EventEmitter {
    id = 'bluebubbles';
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
            throw new Error('BlueBubbles adapter not connected');
    }
}
//# sourceMappingURL=bluebubbles.js.map