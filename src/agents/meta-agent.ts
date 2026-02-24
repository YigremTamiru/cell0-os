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

// ─── Recursive Self-Improvement Engine ────────────────────────────────────

import { GoalManager, type Goal } from "./goals.js";
import { EthicsConsensus } from "./ethics.js";

export interface ReflectionReport {
    timestamp: string;
    goalCount: number;
    patterns: string[];
    newGoals: Goal[];
    systemHealth: "optimal" | "degraded" | "critical";
}

/**
 * SelfImprovementEngine — The recursive improvement kernel (Layer 3: The Brain)
 *
 * Loop: OBSERVE → REFLECT → GOAL-SET → ACT (with ethics gate) → EVALUATE
 * Runs every 5 minutes. Ethics consensus checked before any autonomous action.
 */
export class SelfImprovementEngine {
    private goals: GoalManager;
    private ethics: EthicsConsensus;
    private reflectionInterval: NodeJS.Timeout | null = null;
    private readonly INTERVAL_MS = 5 * 60 * 1000;

    constructor() {
        this.goals = new GoalManager();
        this.ethics = new EthicsConsensus();
        this.goals.seedSystemGoals();
    }

    start(): void {
        this.reflectionInterval = setInterval(() => this.reflect(), this.INTERVAL_MS);
        setTimeout(() => this.reflect(), 30_000);
    }

    stop(): void {
        if (this.reflectionInterval) {
            clearInterval(this.reflectionInterval);
            this.reflectionInterval = null;
        }
    }

    async reflect(): Promise<ReflectionReport> {
        const patterns: string[] = [];
        const newGoals: Goal[] = [];

        // Observe: find repeatedly-failing goals
        for (const goal of this.goals.getActiveGoals()) {
            if (goal.metrics.failureCount >= 3) {
                patterns.push(`"${goal.title}" failed ${goal.metrics.failureCount}×`);
                const check = this.ethics.evaluate("goal-creation", `Create RCA sub-goal for: ${goal.title}`);
                if (this.ethics.isApproved(check)) {
                    newGoals.push(this.goals.createGoal({
                        title: `Investigate: ${goal.title}`,
                        description: `Root cause analysis — repeated failures: ${goal.description}`,
                        domain: "self-improvement",
                        priority: "high",
                        status: "pending",
                        sourceType: "self-generated",
                        parentGoalId: goal.id,
                        tags: ["rca", "auto-generated"],
                    }));
                }
            }
        }

        // Reflect: assess overall health
        const summary = this.goals.getSummary();
        const systemHealth: ReflectionReport["systemHealth"] =
            summary.completionRate >= 70 ? "optimal"
            : summary.completionRate >= 40 ? "degraded"
            : "critical";

        if (systemHealth !== "optimal" && newGoals.length === 0) {
            const check = this.ethics.evaluate("goal-creation", `System health improvement (${systemHealth})`);
            if (this.ethics.isApproved(check)) {
                newGoals.push(this.goals.createGoal({
                    title: `Recover System Health (${systemHealth})`,
                    description: `Health at ${summary.completionRate}% completion. Investigate blockers.`,
                    domain: "self-improvement",
                    priority: systemHealth === "critical" ? "critical" : "high",
                    status: "pending",
                    sourceType: "self-generated",
                    tags: ["auto-generated", "health"],
                }));
                patterns.push(`Health: ${systemHealth} (${summary.completionRate}%)`);
            }
        }

        return {
            timestamp: new Date().toISOString(),
            goalCount: summary.total,
            patterns,
            newGoals,
            systemHealth,
        };
    }

    /** Gate all autonomous actions through ethics consensus */
    async executeWithEthics(
        actionType: string,
        action: string,
        executor: () => Promise<void>
    ): Promise<{ executed: boolean; verdict: string }> {
        const decision = this.ethics.evaluate(actionType, action);
        if (!this.ethics.isApproved(decision)) {
            const reason = decision.checks.find((c) => !c.passed)?.reason ?? "unknown";
            console.warn(`[Ethics] REJECTED: ${action}\n  Reason: ${reason}`);
            return { executed: false, verdict: decision.verdict };
        }
        await executor();
        return { executed: true, verdict: decision.verdict };
    }

    getGoalManager(): GoalManager { return this.goals; }
    getEthicsConsensus(): EthicsConsensus { return this.ethics; }
}
