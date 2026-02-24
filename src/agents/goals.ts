/**
 * Cell 0 OS — Goal Tracking System (Layer 3: The Brain)
 *
 * Autonomous goal-setting, tracking, and self-directed improvement.
 * Goals persist to ~/.cell0/runtime/goals.json across restarts.
 *
 * Part of the recursive self-improvement loop:
 *   OBSERVE → REFLECT → GOAL-SET → ACT → EVALUATE
 */

import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { randomUUID } from "node:crypto";

const GOALS_PATH = path.join(os.homedir(), ".cell0", "runtime", "goals.json");

export type GoalStatus = "pending" | "in-progress" | "completed" | "blocked" | "abandoned";
export type GoalDomain =
    | "self-improvement"
    | "knowledge-acquisition"
    | "capability-expansion"
    | "resource-acquisition"
    | "user-satisfaction"
    | "system-health"
    | "healthcare"
    | "finance"
    | "defense"
    | "social"
    | "creative"
    | "scientific"
    | "education"
    | "transport"
    | "energy"
    | "manufacturing"
    | "legal";

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

export class GoalManager {
    private goals: Map<string, Goal> = new Map();

    constructor() {
        this.load();
    }

    private load(): void {
        if (!fs.existsSync(GOALS_PATH)) return;
        try {
            const data = JSON.parse(fs.readFileSync(GOALS_PATH, "utf-8")) as Goal[];
            for (const goal of data) this.goals.set(goal.id, goal);
        } catch { /* Fresh start */ }
    }

    private save(): void {
        try {
            const dir = path.dirname(GOALS_PATH);
            if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
            fs.writeFileSync(GOALS_PATH, JSON.stringify(Array.from(this.goals.values()), null, 2));
        } catch { /* non-fatal */ }
    }

    createGoal(params: Omit<Goal, "id" | "createdAt" | "updatedAt" | "metrics">): Goal {
        const goal: Goal = {
            ...params,
            id: randomUUID(),
            metrics: { successCount: 0, failureCount: 0 },
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
        };
        this.goals.set(goal.id, goal);
        this.save();
        return goal;
    }

    updateGoal(id: string, updates: Partial<Goal>): Goal | null {
        const goal = this.goals.get(id);
        if (!goal) return null;
        const updated = { ...goal, ...updates, updatedAt: new Date().toISOString() };
        this.goals.set(id, updated);
        this.save();
        return updated;
    }

    completeGoal(id: string, reflection?: string): Goal | null {
        const goal = this.goals.get(id);
        if (!goal) return null;
        return this.updateGoal(id, {
            status: "completed",
            reflection,
            metrics: {
                ...goal.metrics,
                completedAt: new Date().toISOString(),
                successCount: goal.metrics.successCount + 1,
            },
        });
    }

    failGoal(id: string, reflection?: string): Goal | null {
        const goal = this.goals.get(id);
        if (!goal) return null;
        return this.updateGoal(id, {
            reflection,
            metrics: {
                ...goal.metrics,
                failureCount: goal.metrics.failureCount + 1,
                lastAttemptAt: new Date().toISOString(),
            },
        });
    }

    getGoal(id: string): Goal | undefined {
        return this.goals.get(id);
    }

    getActiveGoals(): Goal[] {
        return Array.from(this.goals.values()).filter(
            (g) => g.status === "pending" || g.status === "in-progress"
        );
    }

    getGoalsByDomain(domain: GoalDomain): Goal[] {
        return Array.from(this.goals.values()).filter((g) => g.domain === domain);
    }

    getSummary(): GoalSummary {
        const all = Array.from(this.goals.values());
        const byStatus: Record<GoalStatus, number> = {
            pending: 0, "in-progress": 0, completed: 0, blocked: 0, abandoned: 0,
        };
        const byDomain: Partial<Record<GoalDomain, number>> = {};
        for (const g of all) {
            byStatus[g.status]++;
            byDomain[g.domain] = (byDomain[g.domain] ?? 0) + 1;
        }
        const total = all.length;
        return {
            total,
            byStatus,
            byDomain,
            selfGenerated: all.filter((g) => g.sourceType === "self-generated").length,
            completionRate: total > 0 ? Math.round((byStatus.completed / total) * 100) : 0,
        };
    }

    seedSystemGoals(): void {
        if (this.goals.size > 0) return;
        const seeds: Array<Omit<Goal, "id" | "createdAt" | "updatedAt" | "metrics">> = [
            {
                title: "Maintain Gateway Uptime",
                description: "Keep the WebSocket gateway running at all times",
                domain: "system-health",
                priority: "critical",
                status: "in-progress",
                sourceType: "system",
                tags: ["system", "uptime"],
            },
            {
                title: "Improve Response Quality",
                description: "Analyze failed interactions and improve routing accuracy",
                domain: "self-improvement",
                priority: "high",
                status: "pending",
                sourceType: "self-generated",
                tags: ["quality", "learning"],
            },
            {
                title: "Expand Channel Coverage",
                description: "Connect all configured channel adapters successfully",
                domain: "capability-expansion",
                priority: "high",
                status: "pending",
                sourceType: "system",
                tags: ["channels", "integration"],
            },
        ];
        for (const s of seeds) this.createGoal(s);
    }

    all(): Goal[] {
        return Array.from(this.goals.values());
    }
}
