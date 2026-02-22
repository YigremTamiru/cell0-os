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
export declare class MonitoringService {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Polls the python endpoint for the latest system and AI telemetry.
     */
    fetchTelemetry(): Promise<CombinedTelemetry | null>;
    /**
     * Captures a structured application log into the unified logging sink.
     */
    recordLog(level: "INFO" | "WARN" | "ERROR", message: string, component: string): Promise<void>;
}
//# sourceMappingURL=monitoring.d.ts.map