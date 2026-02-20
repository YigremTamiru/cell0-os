/**
 * Cell 0 OS — Credentials Vault Tool
 *
 * Wraps the Zero-Trust Secrets Management system in Python (cell0/engine/security/secrets.py).
 * Exposes methods for agents to encrypt and decrypt sensitive API keys,
 * utilizing the backend's 1Password CLI fallback and encrypted TPV store.
 */

import { PythonBridge } from "../agents/python-bridge.js";

export class VaultTool {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Retrieves a decrypted secret from the Vault.
     */
    async getSecret(key: string, defaultValue?: string): Promise<string | null> {
        if (!this.bridge.isReady()) throw new Error("Python backend is not ready to access the Vault.");

        try {
            const response = await this.bridge.post<any>("/api/tools/secrets/get", { key, default: defaultValue });
            return response.value ?? null;
        } catch (error) {
            console.error(`[VaultTool] Failed to get secret '${key}':`, error);
            return defaultValue ?? null;
        }
    }

    /**
     * Stores an encrypted secret in the Vault.
     */
    async setSecret(key: string, value: string, tags: string[] = []): Promise<boolean> {
        if (!this.bridge.isReady()) throw new Error("Python backend is not ready to access the Vault.");

        try {
            const response = await this.bridge.post<any>("/api/tools/secrets/set", { key, value, metadata: { tags } });
            return response.success ?? true;
        } catch (error) {
            console.error(`[VaultTool] Failed to set secret '${key}':`, error);
            return false;
        }
    }

    /**
     * Deletes a secret from the Vault.
     */
    async deleteSecret(key: string): Promise<boolean> {
        if (!this.bridge.isReady()) return false;

        try {
            const response = await this.bridge.post<any>("/api/tools/secrets/delete", { key });
            return response.success ?? true;
        } catch (error) {
            return false;
        }
    }

    /**
     * Lists all keys available in the Vault (without revealing values).
     */
    async listSecrets(): Promise<string[]> {
        if (!this.bridge.isReady()) return [];

        try {
            const response = await this.bridge.post<any>("/api/tools/secrets/list", {});
            return response.keys || [];
        } catch (error) {
            return [];
        }
    }
}
