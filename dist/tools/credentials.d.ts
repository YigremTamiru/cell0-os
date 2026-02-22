/**
 * Cell 0 OS — Credentials Vault Tool
 *
 * Wraps the Zero-Trust Secrets Management system in Python (cell0/engine/security/secrets.py).
 * Exposes methods for agents to encrypt and decrypt sensitive API keys,
 * utilizing the backend's 1Password CLI fallback and encrypted TPV store.
 */
import { PythonBridge } from "../agents/python-bridge.js";
export declare class VaultTool {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Retrieves a decrypted secret from the Vault.
     */
    getSecret(key: string, defaultValue?: string): Promise<string | null>;
    /**
     * Stores an encrypted secret in the Vault.
     */
    setSecret(key: string, value: string, tags?: string[]): Promise<boolean>;
    /**
     * Deletes a secret from the Vault.
     */
    deleteSecret(key: string): Promise<boolean>;
    /**
     * Lists all keys available in the Vault (without revealing values).
     */
    listSecrets(): Promise<string[]>;
}
//# sourceMappingURL=credentials.d.ts.map