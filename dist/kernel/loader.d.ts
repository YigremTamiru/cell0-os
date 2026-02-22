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
export declare class KernelLoader {
    private policiesDir;
    private cachedPolicies;
    constructor(cell0Home: string);
    /**
     * Loads and caches all pre-compiled Rust kernel cryptographic constraints.
     */
    initialize(): Promise<number>;
    /**
     * Verify if an action explicitly violates a permanent Rust kernel constraint.
     */
    isActionAllowed(domain: string, action: string): boolean;
}
//# sourceMappingURL=loader.d.ts.map