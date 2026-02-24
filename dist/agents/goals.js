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
export class GoalManager {
    goals = new Map();
    constructor() {
        this.load();
    }
    load() {
        if (!fs.existsSync(GOALS_PATH))
            return;
        try {
            const data = JSON.parse(fs.readFileSync(GOALS_PATH, "utf-8"));
            for (const goal of data)
                this.goals.set(goal.id, goal);
        }
        catch { /* Fresh start */ }
    }
    save() {
        try {
            const dir = path.dirname(GOALS_PATH);
            if (!fs.existsSync(dir))
                fs.mkdirSync(dir, { recursive: true });
            fs.writeFileSync(GOALS_PATH, JSON.stringify(Array.from(this.goals.values()), null, 2));
        }
        catch { /* non-fatal */ }
    }
    createGoal(params) {
        const goal = {
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
    updateGoal(id, updates) {
        const goal = this.goals.get(id);
        if (!goal)
            return null;
        const updated = { ...goal, ...updates, updatedAt: new Date().toISOString() };
        this.goals.set(id, updated);
        this.save();
        return updated;
    }
    completeGoal(id, reflection) {
        const goal = this.goals.get(id);
        if (!goal)
            return null;
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
    failGoal(id, reflection) {
        const goal = this.goals.get(id);
        if (!goal)
            return null;
        return this.updateGoal(id, {
            reflection,
            metrics: {
                ...goal.metrics,
                failureCount: goal.metrics.failureCount + 1,
                lastAttemptAt: new Date().toISOString(),
            },
        });
    }
    getGoal(id) {
        return this.goals.get(id);
    }
    getActiveGoals() {
        return Array.from(this.goals.values()).filter((g) => g.status === "pending" || g.status === "in-progress");
    }
    getGoalsByDomain(domain) {
        return Array.from(this.goals.values()).filter((g) => g.domain === domain);
    }
    getSummary() {
        const all = Array.from(this.goals.values());
        const byStatus = {
            pending: 0, "in-progress": 0, completed: 0, blocked: 0, abandoned: 0,
        };
        const byDomain = {};
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
    seedSystemGoals() {
        if (this.goals.size > 0)
            return;
        const seeds = [
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
        for (const s of seeds)
            this.createGoal(s);
    }
    all() {
        return Array.from(this.goals.values());
    }
}
//# sourceMappingURL=goals.js.map