/**
 * DiscoveryService
 *
 * Wraps `swarm/discovery.py`.
 * Exposes the decentralized node broadcasting mechanism to Node.js, allowing
 * the UI to show the user other foreign instances of Cell 0 OS connected over the Mesh/Tailscale VPN.
 */
export class DiscoveryService {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Issues an active ping across the authorized subnet to detect floating GPU clusters or peer nodes.
     */
    async pingSubnet() {
        if (!this.bridge.isReady())
            return [];
        try {
            const res = await this.bridge.get("/api/swarm/discovery/ping");
            return res.nodes;
        }
        catch {
            return [];
        }
    }
}
//# sourceMappingURL=discovery.js.map