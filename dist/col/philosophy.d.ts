import { PythonBridge } from '../agents/python-bridge.js';
export interface PhilosophyConstraint {
    id: string;
    rule: string;
    weight: number;
}
export interface MoralEvaluation {
    is_safe: boolean;
    confidence: number;
    violations: string[];
}
/**
 * PhilosophyEngine
 *
 * Wraps the `col/philosophy/` module.
 * Serves as the ultimate mathematical ethical boundary for Autonomous OS operations.
 * Allows the Node.js GUI to pre-flight highly dangerous operations (e.g. deleting volumes, sending automated emails).
 */
export declare class PhilosophyEngine {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Evaluates a proposed agent intent against the core philosophical directives.
     */
    evaluateIntent(intentDescription: string): Promise<MoralEvaluation>;
    /**
     * Retrieves the currently active ethical constraint weights.
     */
    getActiveConstraints(): Promise<PhilosophyConstraint[]>;
}
//# sourceMappingURL=philosophy.d.ts.map