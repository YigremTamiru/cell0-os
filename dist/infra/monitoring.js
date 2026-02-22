/**
 * Cell 0 OS — Monitoring & Telemetry
 *
 * Wraps cell0/engine/monitoring/*
 * Subscribes to backend metrics (CPU, Memory, Request Rates, AI Latency)
 * and exposes them natively to the Node.js visualization dashboard.
 */
export class MonitoringService {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Polls the python endpoint for the latest system and AI telemetry.
     */
    async fetchTelemetry() {
        if (!this.bridge.isReady()) {
            return null;
        }
        try {
            const res = await this.bridge.post("/api/monitoring/telemetry", {});
            return res;
        }
        catch (error) {
            console.error("[MonitoringService] Failed to fetch telemetry:", error);
            return null;
        }
    }
    /**
     * Captures a structured application log into the unified logging sink.
     */
    async recordLog(level, message, component) {
        if (!this.bridge.isReady())
            return;
        try {
            await this.bridge.post("/api/monitoring/log", { level, message, component });
        }
        catch (error) {
            // Silently fail logging to avoid cyclical failure states
        }
    }
}
//# sourceMappingURL=monitoring.js.map