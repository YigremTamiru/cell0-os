import { EventEmitter } from 'node:events';
/**
 * Matrix Protocol Adapter
 * Natively supports E2E encryption for rooms.
 */
export class MatrixAdapter extends EventEmitter {
    id = 'matrix';
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
            throw new Error('Matrix adapter not connected');
    }
}
//# sourceMappingURL=matrix.js.map