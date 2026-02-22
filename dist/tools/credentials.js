/**
 * Cell 0 OS — Credentials Vault Tool
 *
 * Wraps the Zero-Trust Secrets Management system in Python (cell0/engine/security/secrets.py).
 * Exposes methods for agents to encrypt and decrypt sensitive API keys,
 * utilizing the backend's 1Password CLI fallback and encrypted TPV store.
 */
export class VaultTool {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Retrieves a decrypted secret from the Vault.
     */
    async getSecret(key, defaultValue) {
        if (!this.bridge.isReady())
            throw new Error("Python backend is not ready to access the Vault.");
        try {
            const response = await this.bridge.post("/api/tools/secrets/get", { key, default: defaultValue });
            return response.value ?? null;
        }
        catch (error) {
            console.error(`[VaultTool] Failed to get secret '${key}':`, error);
            return defaultValue ?? null;
        }
    }
    /**
     * Stores an encrypted secret in the Vault.
     */
    async setSecret(key, value, tags = []) {
        if (!this.bridge.isReady())
            throw new Error("Python backend is not ready to access the Vault.");
        try {
            const response = await this.bridge.post("/api/tools/secrets/set", { key, value, metadata: { tags } });
            return response.success ?? true;
        }
        catch (error) {
            console.error(`[VaultTool] Failed to set secret '${key}':`, error);
            return false;
        }
    }
    /**
     * Deletes a secret from the Vault.
     */
    async deleteSecret(key) {
        if (!this.bridge.isReady())
            return false;
        try {
            const response = await this.bridge.post("/api/tools/secrets/delete", { key });
            return response.success ?? true;
        }
        catch (error) {
            return false;
        }
    }
    /**
     * Lists all keys available in the Vault (without revealing values).
     */
    async listSecrets() {
        if (!this.bridge.isReady())
            return [];
        try {
            const response = await this.bridge.post("/api/tools/secrets/list", {});
            return response.keys || [];
        }
        catch (error) {
            return [];
        }
    }
}
//# sourceMappingURL=credentials.js.map