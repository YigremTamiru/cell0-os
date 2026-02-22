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
export declare class SwarmCoordinator {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Instantiates a dynamic multi-agent collective to tackle a massive long-term objective.
     */
    spawnSwarm(config: SwarmConfig): Promise<string | null>;
    /**
     * Checks the live status and intermediate output yield of an active swarm collective.
     */
    getStatus(swarmId: string): Promise<SwarmStatus | null>;
    /**
     * Dissolves a swarm architecture and halts all subordinate workers.
     */
    dissolve(swarmId: string): Promise<boolean>;
}
//# sourceMappingURL=coordinator.d.ts.map