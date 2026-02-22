import { EventEmitter } from 'node:events';
export class DiscordAdapter extends EventEmitter {
    id = 'discord';
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
            throw new Error('Discord adapter not connected');
    }
}
//# sourceMappingURL=discord.js.map