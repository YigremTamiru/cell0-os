import fs from 'fs/promises';
import path from 'path';

export interface KernelPolicy {
    id: string;
    domain: string;
    action: string;
    is_allowed: boolean;
    cryptographic_signature: string;
}

/**
 * KernelLoader
 * 
 * The ultimate source of truth for OS limitations.
 * Interfaces with the constraints dictated by the low-level Rust `kernel/` module.
 * It reads immutable policies from `~/.cell0/kernel/policies/` to assert that no Swarm 
 * Agent, regardless of prompt-injection or hallucination, can break hard OS limitations.
 */
export class KernelLoader {
    private policiesDir: string;
    private cachedPolicies: Map<string, KernelPolicy> = new Map();

    constructor(cell0Home: string) {
        this.policiesDir = path.join(cell0Home, 'kernel', 'policies');
    }

    /**
     * Loads and caches all pre-compiled Rust kernel cryptographic constraints.
     */
    public async initialize(): Promise<number> {
        this.cachedPolicies.clear();
        try {
            // Ensure directory exists during early boot
            await fs.mkdir(this.policiesDir, { recursive: true });

            const files = await fs.readdir(this.policiesDir);
            for (const file of files) {
                if (file.endsWith('.json')) {
                    try {
                        const content = await fs.readFile(path.join(this.policiesDir, file), 'utf-8');
                        const policy: KernelPolicy = JSON.parse(content);
                        if (policy.id && policy.cryptographic_signature) {
                            this.cachedPolicies.set(policy.id, policy);
                        }
                    } catch (e) {
                        console.warn(`[KernelLoader] Failed to parse policy file: ${file}`, e);
                    }
                }
            }
            return this.cachedPolicies.size;
        } catch (error) {
            console.error("[KernelLoader] Failed to read kernel policies directory:", error);
            return 0;
        }
    }

    /**
     * Verify if an action explicitly violates a permanent Rust kernel constraint.
     */
    public isActionAllowed(domain: string, action: string): boolean {
        // Fall open if no explicit kernel policy forbids it (relies on Philosophy/Daemon safety logic)
        // If a policy EXISTS and sets is_allowed = false, it is a hard block.
        for (const policy of this.cachedPolicies.values()) {
            if (policy.domain === domain && policy.action === action) {
                if (!policy.is_allowed) return false;
            }
        }
        return true;
    }
}
