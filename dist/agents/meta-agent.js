/**
 * MetaAgentCoordinator
 *
 * Maps to `col/orchestrator.py`.
 * The highest-level cognitive agent in the Node boundary. When a task requires
 * crossing multiple domains (e.g., reading an email and then paying an invoice),
 * this coordinator builds a multi-step execution plan and delegates it down
 * to the Agent Mesh via the Python bridge.
 */
export class MetaAgentCoordinator {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Determines if an incoming request exceeds a single domain's capability.
     */
    async requiresCrossDomainOrchestration(text) {
        if (!this.bridge.isReady())
            return false;
        try {
            const result = await this.bridge.post("/api/col/evaluate", { text });
            return result.requires_orchestration || false;
        }
        catch (error) {
            console.error("[MetaAgent] Evaluation failed:", error);
            return false;
        }
    }
    /**
     * Plans a multi-agent execution workflow.
     */
    async createPlan(text, contextWindow) {
        if (!this.bridge.isReady()) {
            throw new Error("Python backend disconnected. Cannot orchestrate complex tasks.");
        }
        try {
            const result = await this.bridge.post("/api/col/plan", {
                text,
                context: contextWindow || []
            });
            return result;
        }
        catch (error) {
            console.error("[MetaAgent] Planning failed:", error);
            throw error;
        }
    }
    /**
     * Synthesizes the final response after all sub-tasks in an OrchestrationPlan complete.
     */
    async synthesizeResults(planId, taskResults) {
        if (!this.bridge.isReady()) {
            throw new Error("Python backend disconnected.");
        }
        try {
            const result = await this.bridge.post("/api/col/synthesize", {
                plan_id: planId,
                results: taskResults
            });
            return result;
        }
        catch (error) {
            console.error("[MetaAgent] Synthesis failed:", error);
            throw error;
        }
    }
}
//# sourceMappingURL=meta-agent.js.map