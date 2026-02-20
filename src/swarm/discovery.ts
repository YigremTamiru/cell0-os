import { PythonBridge } from '../agents/python-bridge.js';

export interface DiscoveredNode {
    id: string;
    ip_address: string;
    capabilities: string[];
    latency_ms: number;
    status: "active" | "dormant" | "unreachable";
}

/**
 * DiscoveryService
 * 
 * Wraps `swarm/discovery.py`.
 * Exposes the decentralized node broadcasting mechanism to Node.js, allowing
 * the UI to show the user other foreign instances of Cell 0 OS connected over the Mesh/Tailscale VPN.
 */
export class DiscoveryService {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Issues an active ping across the authorized subnet to detect floating GPU clusters or peer nodes.
     */
    public async pingSubnet(): Promise<DiscoveredNode[]> {
        if (!this.bridge.isReady()) return [];
        try {
            const res = await this.bridge.get<{ nodes: DiscoveredNode[] }>("/api/swarm/discovery/ping");
            return res.nodes;
        } catch {
            return [];
        }
    }
}
