/**
 * Cell 0 OS — Cron Automation Tool
 *
 * Reads job definitions from ~/.cell0/runtime/cron/
 * and triggers automated agent execution.
 * Allows agents to schedule future tasks for themselves.
 */
import { AgentRuntime } from "../agents/runtime.js";
export interface CronJob {
    id: string;
    schedule: string;
    intent: string;
    input: string;
    context: {
        domain: string;
        specialist?: string;
    };
    lastRun?: number;
}
export declare class CronManager {
    private runtime;
    private timer;
    private jobs;
    constructor(runtime: AgentRuntime);
    /**
     * Starts the cron scheduler
     */
    start(pollIntervalMs?: number): Promise<void>;
    /**
     * Stops the cron scheduler
     */
    stop(): void;
    /**
     * Allows an agent to schedule a new automated job
     */
    scheduleJob(job: Omit<CronJob, "id">): Promise<string>;
    /**
     * Removes a scheduled job
     */
    unscheduleJob(id: string): Promise<boolean>;
    /**
     * Reads the cron directory and loads all .job files into memory
     */
    private syncJobs;
    /**
     * Evaluates all jobs and executes them if their schedule criteria is met.
     * (Provides simplified evaluation for the architectural mockup)
     */
    private tick;
}
//# sourceMappingURL=cron.d.ts.map