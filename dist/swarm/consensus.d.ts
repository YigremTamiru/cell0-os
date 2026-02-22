import { PythonBridge } from '../agents/python-bridge.js';
export interface ConsensusProposal {
    id: string;
    topic: string;
    options: string[];
}
export interface ConsensusResult {
    proposal_id: string;
    winning_option: string;
    votes: Record<string, number>;
    confidence: number;
}
/**
 * ConsensusProtocol
 *
 * Wraps `swarm/consensus.py`.
 * Provides the Node.js API with visibility into the decentralized decision-making
 * trees used by active agent swarms to arbitrate truth or select action branches.
 */
export declare class ConsensusProtocol {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Fetches the current polling state of an ongoing decentralized agent election.
     */
    getElectionState(proposalId: string): Promise<ConsensusResult | null>;
}
//# sourceMappingURL=consensus.d.ts.map