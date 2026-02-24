/**
 * Cell 0 OS — Matrix Channel Adapter
 *
 * Uses Matrix Client-Server API via native fetch (no external SDK).
 * Connects to any Matrix homeserver (matrix.org, Element, self-hosted).
 *
 * Setup: cell0 configure channels matrix
 */
import { EventEmitter } from "node:events";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
const CREDS_PATH = path.join(os.homedir(), ".cell0", "credentials", "matrix", "creds.json");
export class MatrixAdapter extends EventEmitter {
    id = "matrix";
    defaultDomain = "social";
    connected = false;
    creds = null;
    syncToken = null;
    syncTimer = null;
    loadCreds() {
        if (!fs.existsSync(CREDS_PATH))
            return null;
        try {
            return JSON.parse(fs.readFileSync(CREDS_PATH, "utf-8"));
        }
        catch {
            return null;
        }
    }
    async matrixApi(method, endpoint, body) {
        const resp = await fetch(`${this.creds.homeserver}/_matrix/client/v3${endpoint}`, {
            method,
            headers: {
                Authorization: `Bearer ${this.creds.accessToken}`,
                "Content-Type": "application/json",
            },
            body: body ? JSON.stringify(body) : undefined,
        });
        if (!resp.ok)
            throw new Error(`Matrix ${resp.status}: ${await resp.text()}`);
        return resp.json();
    }
    async connect() {
        this.creds = this.loadCreds();
        if (!this.creds?.accessToken) {
            console.warn("[Matrix] No credentials. Run: cell0 configure channels matrix");
            return;
        }
        try {
            const whoami = await this.matrixApi("GET", "/account/whoami");
            console.log(`[Matrix] ✅ Connected as ${whoami.user_id}`);
            this.connected = true;
            this.emit("connected");
            this.startSync();
        }
        catch (err) {
            this.emit("error", new Error(`[Matrix] Auth failed: ${err}`));
        }
    }
    startSync() {
        const doSync = async () => {
            if (!this.connected)
                return;
            try {
                const params = new URLSearchParams({ timeout: "20000", full_state: "false" });
                if (this.syncToken)
                    params.set("since", this.syncToken);
                const result = await this.matrixApi("GET", `/sync?${params}`);
                this.syncToken = result.next_batch;
                for (const [roomId, room] of Object.entries((result.rooms?.join ?? {}))) {
                    for (const event of room.timeline?.events ?? []) {
                        if (event.type !== "m.room.message" || event.sender === this.creds?.userId)
                            continue;
                        const inbound = {
                            id: event.event_id,
                            channelId: this.id,
                            domain: this.defaultDomain,
                            senderId: event.sender,
                            threadId: roomId,
                            text: event.content?.body ?? "",
                            timestamp: event.origin_server_ts,
                            isEncrypted: false,
                            rawPayload: event,
                        };
                        this.emit("message", inbound);
                    }
                }
            }
            catch (err) {
                if (this.connected)
                    console.error("[Matrix] Sync error:", err);
            }
            if (this.connected)
                this.syncTimer = setTimeout(doSync, 1000);
        };
        doSync();
    }
    async disconnect() {
        this.connected = false;
        if (this.syncTimer) {
            clearTimeout(this.syncTimer);
            this.syncTimer = null;
        }
        this.emit("disconnected");
    }
    async send(message) {
        if (!this.connected)
            throw new Error("Matrix adapter not connected");
        const txnId = `cell0.${Date.now()}`;
        await this.matrixApi("PUT", `/rooms/${encodeURIComponent(message.threadId ?? message.recipientId)}/send/m.room.message/${txnId}`, { msgtype: "m.text", body: message.text });
    }
    isConnected() { return this.connected; }
}
//# sourceMappingURL=matrix.js.map