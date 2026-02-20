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
export class CheckpointManager {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Issue a command to snapshot an agent's active reasoning state.
     */
    public async createCheckpoint(agentId: string, metadata: any = {}): Promise<CheckpointRecord | null> {
        if (!this.bridge.isReady()) return null;
        try {
            return await this.bridge.post<CheckpointRecord>("/api/col/checkpoint/create", {
                agent_id: agentId,
                metadata
            });
        } catch (error) {
            console.error("[CheckpointManager] Failed to create state checkpoint", error);
            return null;
        }
    }

    /**
     * List all highly-serialized hibernation states, grouped by agent.
     */
    public async listCheckpoints(agentId?: string): Promise<CheckpointRecord[]> {
        if (!this.bridge.isReady()) return [];
        try {
            const url = agentId ? `/api/col/checkpoint/list?agent=${agentId}` : "/api/col/checkpoint/list";
            const res = await this.bridge.get<{ checkpoints: CheckpointRecord[] }>(url);
            return res.checkpoints;
        } catch {
            return [];
        }
    }

    /**
     * Resurrect an agent strictly from the mathematical hash representing its exact memory layout.
     */
    public async restore(checkpointId: string): Promise<boolean> {
        if (!this.bridge.isReady()) return false;
        try {
            const res = await this.bridge.post<{ success: boolean }>("/api/col/checkpoint/restore", {
                id: checkpointId
            });
            return res.success;
        } catch {
            return false;
        }
    }
}
