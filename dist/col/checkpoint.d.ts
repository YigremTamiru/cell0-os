import { PythonBridge } from '../agents/python-bridge.js';
export interface CheckpointRecord {
    id: string;
    agent_id: string;
    state_hash: string;
    timestamp: string;
    metadata: any;
}
/**
 * CheckpointManager
 *
 * Wraps `col/checkpoint.py`.
 * Distinct from `BackupManager` (which zips whole directories). CheckpointManager
 * serializes isolated segments of the active LLM context and Memory cache trees,
 * allowing individual agents to "hibernate" and cleanly resume multi-day calculations.
 */
export declare class CheckpointManager {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Issue a command to snapshot an agent's active reasoning state.
     */
    createCheckpoint(agentId: string, metadata?: any): Promise<CheckpointRecord | null>;
    /**
     * List all highly-serialized hibernation states, grouped by agent.
     */
    listCheckpoints(agentId?: string): Promise<CheckpointRecord[]>;
    /**
     * Resurrect an agent strictly from the mathematical hash representing its exact memory layout.
     */
    restore(checkpointId: string): Promise<boolean>;
}
//# sourceMappingURL=checkpoint.d.ts.map