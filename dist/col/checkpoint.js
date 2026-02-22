/**
 * CheckpointManager
 *
 * Wraps `col/checkpoint.py`.
 * Distinct from `BackupManager` (which zips whole directories). CheckpointManager
 * serializes isolated segments of the active LLM context and Memory cache trees,
 * allowing individual agents to "hibernate" and cleanly resume multi-day calculations.
 */
export class CheckpointManager {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Issue a command to snapshot an agent's active reasoning state.
     */
    async createCheckpoint(agentId, metadata = {}) {
        if (!this.bridge.isReady())
            return null;
        try {
            return await this.bridge.post("/api/col/checkpoint/create", {
                agent_id: agentId,
                metadata
            });
        }
        catch (error) {
            console.error("[CheckpointManager] Failed to create state checkpoint", error);
            return null;
        }
    }
    /**
     * List all highly-serialized hibernation states, grouped by agent.
     */
    async listCheckpoints(agentId) {
        if (!this.bridge.isReady())
            return [];
        try {
            const url = agentId ? `/api/col/checkpoint/list?agent=${agentId}` : "/api/col/checkpoint/list";
            const res = await this.bridge.get(url);
            return res.checkpoints;
        }
        catch {
            return [];
        }
    }
    /**
     * Resurrect an agent strictly from the mathematical hash representing its exact memory layout.
     */
    async restore(checkpointId) {
        if (!this.bridge.isReady())
            return false;
        try {
            const res = await this.bridge.post("/api/col/checkpoint/restore", {
                id: checkpointId
            });
            return res.success;
        }
        catch {
            return false;
        }
    }
}
//# sourceMappingURL=checkpoint.js.map