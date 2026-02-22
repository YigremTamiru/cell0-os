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
export declare class DiscoveryService {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Issues an active ping across the authorized subnet to detect floating GPU clusters or peer nodes.
     */
    pingSubnet(): Promise<DiscoveredNode[]>;
}
//# sourceMappingURL=discovery.d.ts.map