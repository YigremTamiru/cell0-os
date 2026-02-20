import { PythonBridge } from '../agents/python-bridge.js';

export interface SwarmConfig {
    id: string;
    agent_types: string[];
    max_nodes: number;
    objective: string;
}

export interface SwarmStatus {
    id: string;
    active_nodes: number;
    state: "initializing" | "running" | "converged" | "failed";
    yield?: any;
}

/**
 * SwarmCoordinator
 * 
 * Wraps `swarm/coordinator.py`.
 * Interfaces the gateway to the Swarm Intelligence engine. Allows Node.js clients
 * to dispatch highly complex objectives (e.g., "Research and write a 100-page book on Quantum Physics")
 * which the python backend will handle by dynamically spawning dozens of ephemeral agent workers.
 */
export class SwarmCoordinator {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Instantiates a dynamic multi-agent collective to tackle a massive long-term objective.
     */
    public async spawnSwarm(config: SwarmConfig): Promise<string | null> {
        if (!this.bridge.isReady()) return null;
        try {
            const res = await this.bridge.post<{ swarm_id: string }>("/api/swarm/spawn", config);
            return res.swarm_id;
        } catch (error) {
            console.error("[SwarmCoordinator] Failed to spawn collective", error);
            return null;
        }
    }

    /**
     * Checks the live status and intermediate output yield of an active swarm collective.
     */
    public async getStatus(swarmId: string): Promise<SwarmStatus | null> {
        if (!this.bridge.isReady()) return null;
        try {
            return await this.bridge.get<SwarmStatus>(`/api/swarm/status?id=${swarmId}`);
        } catch {
            return null;
        }
    }

    /**
     * Dissolves a swarm architecture and halts all subordinate workers.
     */
    public async dissolve(swarmId: string): Promise<boolean> {
        if (!this.bridge.isReady()) return false;
        try {
            await this.bridge.post("/api/swarm/dissolve", { id: swarmId });
            return true;
        } catch {
            return false;
        }
    }
}
