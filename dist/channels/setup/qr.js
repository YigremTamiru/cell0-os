/**
 * Cell 0 OS — Channel QR Setup Utility
 *
 * Displays QR codes in the terminal for channel pairing flows.
 * Used by the onboarding wizard and `cell0 configure channels` command.
 */
import os from "node:os";
import path from "node:path";
import fs from "node:fs";
export const CREDS_BASE = path.join(os.homedir(), ".cell0", "credentials");
export function isChannelPaired(channelId) {
    const credPath = path.join(CREDS_BASE, channelId);
    // Check for a credentials marker file
    return (fs.existsSync(path.join(credPath, "creds.json")) ||
        fs.existsSync(path.join(credPath, "paired.json")) ||
        fs.existsSync(path.join(credPath, ".paired")));
}
export async function showQRInTerminal(data, label) {
    let qrcode;
    try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        qrcode = await import("qrcode-terminal");
        console.log(`\n  ${label}:`);
        qrcode.default?.generate(data, { small: true }) ??
            qrcode.generate(data, { small: true });
        console.log(`\n  Data: ${data}\n`);
    }
    catch {
        // Fallback: print the raw data
        console.log(`\n  ${label}: ${data}\n`);
        console.log("  (Install qrcode-terminal for QR display: npm install qrcode-terminal)\n");
    }
}
export async function showOAuthQR(channelId, authUrl) {
    await showQRInTerminal(authUrl, `Scan to authorize ${channelId}`);
    console.log(`  Or open manually: ${authUrl}\n`);
}
export function saveChannelCreds(channelId, data) {
    const dir = path.join(CREDS_BASE, channelId);
    fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
    fs.writeFileSync(path.join(dir, "creds.json"), JSON.stringify({ ...data, savedAt: new Date().toISOString() }, null, 2), { encoding: "utf-8", mode: 0o600 });
}
export function loadChannelCreds(channelId) {
    const credPath = path.join(CREDS_BASE, channelId, "creds.json");
    if (!fs.existsSync(credPath))
        return null;
    try {
        return JSON.parse(fs.readFileSync(credPath, "utf-8"));
    }
    catch {
        return null;
    }
}
//# sourceMappingURL=qr.js.map