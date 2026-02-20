/**
 * Cell 0 OS — Monitoring & Telemetry
 *
 * Wraps cell0/engine/monitoring/*
 * Subscribes to backend metrics (CPU, Memory, Request Rates, AI Latency)
 * and exposes them natively to the Node.js visualization dashboard.
 */

import { PythonBridge } from "../agents/python-bridge.js";

export interface SystemMetrics {
    cpu_percent: number;
    memory_mb: number;
    active_threads: number;
    is_healthy: boolean;
}

export interface AgentMetrics {
    total_requests: number;
    average_latency_ms: number;
    error_rate: number;
}

export interface CombinedTelemetry {
    system: SystemMetrics;
    agent: AgentMetrics;
    timestamp: string;
}

export class MonitoringService {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Polls the python endpoint for the latest system and AI telemetry.
     */
    async fetchTelemetry(): Promise<CombinedTelemetry | null> {
        if (!this.bridge.isReady()) {
            return null;
        }

        try {
            const res = await this.bridge.post<CombinedTelemetry>("/api/monitoring/telemetry", {});
            return res;
        } catch (error) {
            console.error("[MonitoringService] Failed to fetch telemetry:", error);
            return null;
        }
    }

    /**
     * Captures a structured application log into the unified logging sink.
     */
    async recordLog(level: "INFO" | "WARN" | "ERROR", message: string, component: string): Promise<void> {
        if (!this.bridge.isReady()) return;

        try {
            await this.bridge.post("/api/monitoring/log", { level, message, component });
        } catch (error) {
            // Silently fail logging to avoid cyclical failure states
        }
    }
}
