/**
 * Cell 0 OS — Cron Automation Tool
 *
 * Reads job definitions from ~/.cell0/runtime/cron/
 * and triggers automated agent execution.
 * Allows agents to schedule future tasks for themselves.
 */
import fs from "node:fs/promises";
import path from "node:path";
import { CELL0_PATHS } from "../config/config.js";
export class CronManager {
    runtime;
    timer = null;
    jobs = new Map();
    constructor(runtime) {
        this.runtime = runtime;
    }
    /**
     * Starts the cron scheduler
     */
    async start(pollIntervalMs = 60000) {
        if (this.timer)
            return;
        await this.syncJobs();
        this.timer = setInterval(() => {
            this.tick();
        }, pollIntervalMs);
        console.log("[CronManager] Started automated task scheduler");
    }
    /**
     * Stops the cron scheduler
     */
    stop() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
            console.log("[CronManager] Stopped automated task scheduler");
        }
    }
    /**
     * Allows an agent to schedule a new automated job
     */
    async scheduleJob(job) {
        const id = crypto.randomUUID();
        const fullJob = { ...job, id };
        const jobPath = path.join(CELL0_PATHS.runtime.cron, `${id}.job`);
        await fs.mkdir(CELL0_PATHS.runtime.cron, { recursive: true });
        await fs.writeFile(jobPath, JSON.stringify(fullJob, null, 2), "utf-8");
        this.jobs.set(id, fullJob);
        return id;
    }
    /**
     * Removes a scheduled job
     */
    async unscheduleJob(id) {
        const jobPath = path.join(CELL0_PATHS.runtime.cron, `${id}.job`);
        try {
            await fs.unlink(jobPath);
            this.jobs.delete(id);
            return true;
        }
        catch (error) {
            return false;
        }
    }
    /**
     * Reads the cron directory and loads all .job files into memory
     */
    async syncJobs() {
        try {
            await fs.mkdir(CELL0_PATHS.runtime.cron, { recursive: true });
            const files = await fs.readdir(CELL0_PATHS.runtime.cron);
            for (const file of files) {
                if (file.endsWith(".job")) {
                    const content = await fs.readFile(path.join(CELL0_PATHS.runtime.cron, file), "utf-8");
                    try {
                        const job = JSON.parse(content);
                        this.jobs.set(job.id, job);
                    }
                    catch (e) {
                        console.error(`[CronManager] Failed to parse job file ${file}`);
                    }
                }
            }
        }
        catch (error) {
            console.error("[CronManager] Failed to sync jobs:", error);
        }
    }
    /**
     * Evaluates all jobs and executes them if their schedule criteria is met.
     * (Provides simplified evaluation for the architectural mockup)
     */
    async tick() {
        // In a full production environment, this would parse standard UNIX cron syntax.
        // For this OS architecture stage, we abstract schedule evaluation.
        const now = Date.now();
        for (const [id, job] of this.jobs.entries()) {
            // Simplified trigger mechanism: Execute every tick if schedule is "frequent"
            const shouldRun = job.schedule.includes("minute") || job.schedule === "* * * * *";
            if (shouldRun) {
                console.log(`[CronManager] Triggering scheduled job: ${job.intent}`);
                const request = {
                    taskId: `cron-${id}-${now}`,
                    intent: job.intent,
                    input: job.input,
                    context: {
                        sessionId: "system-cron",
                        domain: job.context.domain,
                        specialist: job.context.specialist,
                        channelId: "cron",
                        channelSource: "system",
                    }
                };
                // Execute natively in the background without awaiting
                this.runtime.executeTask(request).catch(console.error);
                // Update last run time
                job.lastRun = now;
                const jobPath = path.join(CELL0_PATHS.runtime.cron, `${id}.job`);
                fs.writeFile(jobPath, JSON.stringify(job, null, 2), "utf-8").catch(console.error);
            }
        }
    }
}
//# sourceMappingURL=cron.js.map