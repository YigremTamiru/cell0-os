/**
 * COLBridge
 *
 * Provides native IPC to `col/orchestrator.py`.
 * This acts as the high-level thought-dispatch pipeline for complex AI reasoning requests,
 * distinct from the raw API REST bindings in PythonBridge.
 */
export class COLBridge {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Submits a complex reasoning operation to the Python Cognitive Operating Layer.
     */
    async submitOperation(operation) {
        if (!this.bridge.isReady()) {
            return {
                id: operation.id,
                success: false,
                error: "Python bridge is not connected.",
                execution_time_ms: 0
            };
        }
        try {
            const start = Date.now();
            const result = await this.bridge.post("/api/col/execute", operation);
            return {
                id: operation.id,
                success: true,
                data: result,
                execution_time_ms: Date.now() - start
            };
        }
        catch (error) {
            return {
                id: operation.id,
                success: false,
                error: error.message || "Unknown COL Exception",
                execution_time_ms: 0
            };
        }
    }
    /**
     * Retrieves the active state of the Python Orchestrator engine.
     */
    async getOrchestratorState() {
        if (!this.bridge.isReady())
            return { state: "offline", active_tasks: 0 };
        try {
            return await this.bridge.get("/api/col/state");
        }
        catch {
            return { state: "degraded", active_tasks: 0 };
        }
    }
}
//# sourceMappingURL=bridge.js.map