/**
 * SwarmCoordinator
 *
 * Wraps `swarm/coordinator.py`.
 * Interfaces the gateway to the Swarm Intelligence engine. Allows Node.js clients
 * to dispatch highly complex objectives (e.g., "Research and write a 100-page book on Quantum Physics")
 * which the python backend will handle by dynamically spawning dozens of ephemeral agent workers.
 */
export class SwarmCoordinator {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Instantiates a dynamic multi-agent collective to tackle a massive long-term objective.
     */
    async spawnSwarm(config) {
        if (!this.bridge.isReady())
            return null;
        try {
            const res = await this.bridge.post("/api/swarm/spawn", config);
            return res.swarm_id;
        }
        catch (error) {
            console.error("[SwarmCoordinator] Failed to spawn collective", error);
            return null;
        }
    }
    /**
     * Checks the live status and intermediate output yield of an active swarm collective.
     */
    async getStatus(swarmId) {
        if (!this.bridge.isReady())
            return null;
        try {
            return await this.bridge.get(`/api/swarm/status?id=${swarmId}`);
        }
        catch {
            return null;
        }
    }
    /**
     * Dissolves a swarm architecture and halts all subordinate workers.
     */
    async dissolve(swarmId) {
        if (!this.bridge.isReady())
            return false;
        try {
            await this.bridge.post("/api/swarm/dissolve", { id: swarmId });
            return true;
        }
        catch {
            return false;
        }
    }
}
//# sourceMappingURL=coordinator.js.map