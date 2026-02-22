import { EventEmitter } from 'node:events';
/**
 * WebChat Adapter
 * Connects directly to the Cell 0 OS Gateway WebSocket server (e.g., from the Portal or mobile apps).
 * Payloads sent over WSS are TLS encrypted, but we can enforce payload E2E if configured.
 */
export class WebChatAdapter extends EventEmitter {
    id = 'webchat';
    defaultDomain = 'system'; // Default to system/root access for the portal
    connected = false;
    async connect() {
        // Automatically considered connected since it rides on the Gateway WS
        this.connected = true;
        this.emit('connected');
    }
    async disconnect() {
        this.connected = false;
        this.emit('disconnected');
    }
    async send(message) {
        if (!this.connected)
            throw new Error('WebChat adapter not connected');
        // Will route messages back to connected WS clients via gateway/index.ts
    }
}
//# sourceMappingURL=webchat.js.map