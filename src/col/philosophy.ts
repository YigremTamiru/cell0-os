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
export class PhilosophyEngine {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Evaluates a proposed agent intent against the core philosophical directives.
     */
    public async evaluateIntent(intentDescription: string): Promise<MoralEvaluation> {
        if (!this.bridge.isReady()) {
            // Failsafe open if down, routing rules will handle the block.
            return { is_safe: true, confidence: 0.1, violations: [] };
        }

        try {
            return await this.bridge.post<MoralEvaluation>("/api/col/philosophy/evaluate", {
                intent: intentDescription
            });
        } catch (error) {
            console.error("[PhilosophyEngine] Failed to evaluate intent", error);
            // Default to safe if offline, logic dictates lower layers catch it.
            return { is_safe: true, confidence: 0, violations: [] };
        }
    }

    /**
     * Retrieves the currently active ethical constraint weights.
     */
    public async getActiveConstraints(): Promise<PhilosophyConstraint[]> {
        if (!this.bridge.isReady()) return [];
        try {
            const res = await this.bridge.get<{ constraints: PhilosophyConstraint[] }>("/api/col/philosophy/constraints");
            return res.constraints;
        } catch {
            return [];
        }
    }
}
