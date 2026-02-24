/**
 * Cell 0 OS — Signal Channel Adapter
 *
 * Wraps signal-cli (https://github.com/AsamK/signal-cli) via JSON-RPC stdio.
 * signal-cli must be installed separately (requires Java 17+).
 *
 * Setup:
 *   1. Install signal-cli: https://github.com/AsamK/signal-cli/releases
 *   2. Register: signal-cli register -u +1234567890
 *   3. Verify: signal-cli verify -u +1234567890 --verificationCode 123-456
 *   4. Run: cell0 configure channels signal
 */
import { EventEmitter } from "node:events";
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
const CREDS_PATH = path.join(os.homedir(), ".cell0", "credentials", "signal", "creds.json");
export class SignalAdapter extends EventEmitter {
    id = "signal";
    defaultDomain = "social";
    connected = false;
    creds = null;
    proc = null;
    rpcId = 0;
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
    findSignalCli() {
        const candidates = [
            this.creds?.signalCliPath,
            "/usr/local/bin/signal-cli",
            "/opt/homebrew/bin/signal-cli",
            path.join(os.homedir(), "bin", "signal-cli"),
        ].filter(Boolean);
        return candidates.find((c) => fs.existsSync(c)) ?? null;
    }
    async connect() {
        this.creds = this.loadCreds();
        if (!this.creds?.phoneNumber) {
            console.warn("[Signal] No phone number configured. Run: cell0 configure channels signal");
            return;
        }
        const signalCli = this.findSignalCli();
        if (!signalCli) {
            console.warn("[Signal] signal-cli not found.\n" +
                "  Install from: https://github.com/AsamK/signal-cli/releases\n" +
                "  Requires Java 17+. Place binary in /usr/local/bin/signal-cli");
            return;
        }
        this.proc = spawn(signalCli, [
            "--config", path.join(os.homedir(), ".local", "share", "signal-cli"),
            "--output", "json",
            "-u", this.creds.phoneNumber,
            "jsonRpc",
        ], { stdio: ["pipe", "pipe", "pipe"] });
        this.proc.stderr?.on("data", (d) => {
            const msg = d.toString().trim();
            if (msg)
                console.error(`[Signal] ${msg}`);
        });
        const rl = createInterface({ input: this.proc.stdout });
        rl.on("line", (line) => {
            try {
                const event = JSON.parse(line);
                if (event.method === "receive") {
                    const envelope = event.params?.envelope;
                    if (!envelope?.dataMessage?.message)
                        return;
                    const inbound = {
                        id: String(envelope.timestamp),
                        channelId: this.id,
                        domain: this.defaultDomain,
                        senderId: envelope.source ?? "unknown",
                        senderName: envelope.sourceName ?? undefined,
                        groupId: envelope.dataMessage.groupInfo?.groupId ?? undefined,
                        text: envelope.dataMessage.message,
                        timestamp: envelope.timestamp,
                        isEncrypted: true,
                        rawPayload: envelope,
                    };
                    this.emit("message", inbound);
                }
            }
            catch { /* ignore parse errors */ }
        });
        this.proc.on("exit", (code) => {
            console.log(`[Signal] signal-cli exited (${code})`);
            this.connected = false;
            this.emit("disconnected");
        });
        this.connected = true;
        this.emit("connected");
        console.log("[Signal] ✅ signal-cli JSON-RPC connected");
    }
    async disconnect() {
        this.connected = false;
        if (this.proc) {
            this.proc.kill("SIGTERM");
            this.proc = null;
        }
        this.emit("disconnected");
    }
    async send(message) {
        if (!this.connected || !this.proc)
            throw new Error("Signal adapter not connected");
        const rpc = {
            jsonrpc: "2.0",
            method: "send",
            id: ++this.rpcId,
            params: { recipient: [message.recipientId], message: message.text },
        };
        this.proc.stdin.write(JSON.stringify(rpc) + "\n");
    }
    isConnected() { return this.connected; }
}
//# sourceMappingURL=signal.js.map