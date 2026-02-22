/**
 * ConsensusProtocol
 *
 * Wraps `swarm/consensus.py`.
 * Provides the Node.js API with visibility into the decentralized decision-making
 * trees used by active agent swarms to arbitrate truth or select action branches.
 */
export class ConsensusProtocol {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Fetches the current polling state of an ongoing decentralized agent election.
     */
    async getElectionState(proposalId) {
        if (!this.bridge.isReady())
            return null;
        try {
            return await this.bridge.get(`/api/swarm/consensus/state?id=${proposalId}`);
        }
        catch {
            return null;
        }
    }
}
//# sourceMappingURL=consensus.js.map