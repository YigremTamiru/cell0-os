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
export class MetaAgentCoordinator {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Determines if an incoming request exceeds a single domain's capability.
     */
    async requiresCrossDomainOrchestration(text: string): Promise<boolean> {
        if (!this.bridge.isReady()) return false;

        try {
            const result = await this.bridge.post<{ requires_orchestration: boolean }>("/api/col/evaluate", { text });
            return result.requires_orchestration || false;
        } catch (error) {
            console.error("[MetaAgent] Evaluation failed:", error);
            return false;
        }
    }

    /**
     * Plans a multi-agent execution workflow.
     */
    async createPlan(text: string, contextWindow?: string[]): Promise<OrchestrationPlan> {
        if (!this.bridge.isReady()) {
            throw new Error("Python backend disconnected. Cannot orchestrate complex tasks.");
        }

        try {
            const result = await this.bridge.post<OrchestrationPlan>("/api/col/plan", {
                text,
                context: contextWindow || []
            });
            return result;
        } catch (error) {
            console.error("[MetaAgent] Planning failed:", error);
            throw error;
        }
    }

    /**
     * Synthesizes the final response after all sub-tasks in an OrchestrationPlan complete.
     */
    async synthesizeResults(planId: string, taskResults: Record<string, string>): Promise<SynthesisResult> {
        if (!this.bridge.isReady()) {
            throw new Error("Python backend disconnected.");
        }

        try {
            const result = await this.bridge.post<SynthesisResult>("/api/col/synthesize", {
                plan_id: planId,
                results: taskResults
            });
            return result;
        } catch (error) {
            console.error("[MetaAgent] Synthesis failed:", error);
            throw error;
        }
    }
}
