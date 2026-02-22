import { PythonBridge } from "./python-bridge.js";
export interface OrchestrationPlan {
    planId: string;
    description: string;
    subTasks: Array<{
        taskId: string;
        category: string;
        specialist: string;
        instruction: string;
    }>;
}
export interface SynthesisResult {
    orchestrationId: string;
    finalSummary: string;
    metadata: Record<string, unknown>;
}
/**
 * MetaAgentCoordinator
 *
 * Maps to `col/orchestrator.py`.
 * The highest-level cognitive agent in the Node boundary. When a task requires
 * crossing multiple domains (e.g., reading an email and then paying an invoice),
 * this coordinator builds a multi-step execution plan and delegates it down
 * to the Agent Mesh via the Python bridge.
 */
export declare class MetaAgentCoordinator {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Determines if an incoming request exceeds a single domain's capability.
     */
    requiresCrossDomainOrchestration(text: string): Promise<boolean>;
    /**
     * Plans a multi-agent execution workflow.
     */
    createPlan(text: string, contextWindow?: string[]): Promise<OrchestrationPlan>;
    /**
     * Synthesizes the final response after all sub-tasks in an OrchestrationPlan complete.
     */
    synthesizeResults(planId: string, taskResults: Record<string, string>): Promise<SynthesisResult>;
}
//# sourceMappingURL=meta-agent.d.ts.map