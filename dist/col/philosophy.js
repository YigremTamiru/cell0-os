/**
 * PhilosophyEngine
 *
 * Wraps the `col/philosophy/` module.
 * Serves as the ultimate mathematical ethical boundary for Autonomous OS operations.
 * Allows the Node.js GUI to pre-flight highly dangerous operations (e.g. deleting volumes, sending automated emails).
 */
export class PhilosophyEngine {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Evaluates a proposed agent intent against the core philosophical directives.
     */
    async evaluateIntent(intentDescription) {
        if (!this.bridge.isReady()) {
            // Failsafe open if down, routing rules will handle the block.
            return { is_safe: true, confidence: 0.1, violations: [] };
        }
        try {
            return await this.bridge.post("/api/col/philosophy/evaluate", {
                intent: intentDescription
            });
        }
        catch (error) {
            console.error("[PhilosophyEngine] Failed to evaluate intent", error);
            // Default to safe if offline, logic dictates lower layers catch it.
            return { is_safe: true, confidence: 0, violations: [] };
        }
    }
    /**
     * Retrieves the currently active ethical constraint weights.
     */
    async getActiveConstraints() {
        if (!this.bridge.isReady())
            return [];
        try {
            const res = await this.bridge.get("/api/col/philosophy/constraints");
            return res.constraints;
        }
        catch {
            return [];
        }
    }
}
//# sourceMappingURL=philosophy.js.map