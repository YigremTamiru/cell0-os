/**
 * Cell 0 OS — Goal Tracking System (Layer 3: The Brain)
 *
 * Autonomous goal-setting, tracking, and self-directed improvement.
 * Goals persist to ~/.cell0/runtime/goals.json across restarts.
 *
 * Part of the recursive self-improvement loop:
 *   OBSERVE → REFLECT → GOAL-SET → ACT → EVALUATE
 */
export type GoalStatus = "pending" | "in-progress" | "completed" | "blocked" | "abandoned";
export type GoalDomain = "self-improvement" | "knowledge-acquisition" | "capability-expansion" | "resource-acquisition" | "user-satisfaction" | "system-health" | "healthcare" | "finance" | "defense" | "social" | "creative" | "scientific" | "education" | "transport" | "energy" | "manufacturing" | "legal";
export interface Goal {
    id: string;
    title: string;
    description: string;
    domain: GoalDomain;
    priority: "critical" | "high" | "medium" | "low";
    status: GoalStatus;
    sourceType: "user-assigned" | "self-generated" | "system";
    metrics: {
        successCount: number;
        failureCount: number;
        lastAttemptAt?: string;
        completedAt?: string;
    };
    subGoals?: string[];
    parentGoalId?: string;
    blockedBy?: string[];
    tags: string[];
    createdAt: string;
    updatedAt: string;
    reflection?: string;
}
export interface GoalSummary {
    total: number;
    byStatus: Record<GoalStatus, number>;
    byDomain: Partial<Record<GoalDomain, number>>;
    selfGenerated: number;
    completionRate: number;
}
export declare class GoalManager {
    private goals;
    constructor();
    private load;
    private save;
    createGoal(params: Omit<Goal, "id" | "createdAt" | "updatedAt" | "metrics">): Goal;
    updateGoal(id: string, updates: Partial<Goal>): Goal | null;
    completeGoal(id: string, reflection?: string): Goal | null;
    failGoal(id: string, reflection?: string): Goal | null;
    getGoal(id: string): Goal | undefined;
    getActiveGoals(): Goal[];
    getGoalsByDomain(domain: GoalDomain): Goal[];
    getSummary(): GoalSummary;
    seedSystemGoals(): void;
    all(): Goal[];
}
//# sourceMappingURL=goals.d.ts.map