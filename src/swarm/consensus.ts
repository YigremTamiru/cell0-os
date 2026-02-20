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
export class ConsensusProtocol {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Fetches the current polling state of an ongoing decentralized agent election.
     */
    public async getElectionState(proposalId: string): Promise<ConsensusResult | null> {
        if (!this.bridge.isReady()) return null;
        try {
            return await this.bridge.get<ConsensusResult>(`/api/swarm/consensus/state?id=${proposalId}`);
        } catch {
            return null;
        }
    }
}
