/**
 * Cell 0 OS — Ethics Consensus Component (Layer 3: The Brain)
 *
 * Implements the Ethics layer from the sovereign architecture:
 * Fairness, Transparency, Security checks on all autonomous AI actions.
 *
 * The ethics engine runs BEFORE any autonomous action is executed,
 * ensuring Cell 0 OS maintains sovereign alignment and user trust.
 */
export type EthicsVerdict = "approved" | "flagged" | "rejected";
export interface EthicsCheck {
    name: string;
    passed: boolean;
    severity: "info" | "warning" | "critical";
    reason?: string;
}
export interface EthicsDecision {
    timestamp: string;
    actionType: string;
    action: string;
    verdict: EthicsVerdict;
    checks: EthicsCheck[];
    overrideAllowed: boolean;
}
export declare class EthicsConsensus {
    evaluate(actionType: string, action: string, context?: Record<string, unknown>): EthicsDecision;
    isApproved(decision: EthicsDecision): boolean;
    private log;
    getRecentDecisions(limit?: number): EthicsDecision[];
}
//# sourceMappingURL=ethics.d.ts.map