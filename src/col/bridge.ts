import { PythonBridge } from '../agents/python-bridge.js';

/**
 * Interface representing a complex cognitive operation dispatched to the Python COL Orchestrator.
 */
export interface CognitiveOperation {
    id: string;
    type: string;
    payload: any;
    priority?: number;
    require_checkpoint?: boolean;
}

export interface CognitiveResult {
    id: string;
    success: boolean;
    data?: any;
    error?: string;
    execution_time_ms: number;
}

/**
 * COLBridge
 * 
 * Provides native IPC to `col/orchestrator.py`.
 * This acts as the high-level thought-dispatch pipeline for complex AI reasoning requests,
 * distinct from the raw API REST bindings in PythonBridge.
 */
export class COLBridge {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Submits a complex reasoning operation to the Python Cognitive Operating Layer.
     */
    public async submitOperation(operation: CognitiveOperation): Promise<CognitiveResult> {
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
            const result = await this.bridge.post<any>("/api/col/execute", operation);
            return {
                id: operation.id,
                success: true,
                data: result,
                execution_time_ms: Date.now() - start
            };
        } catch (error: any) {
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
    public async getOrchestratorState(): Promise<{ state: string, active_tasks: number }> {
        if (!this.bridge.isReady()) return { state: "offline", active_tasks: 0 };
        try {
            return await this.bridge.get<{ state: string, active_tasks: number }>("/api/col/state");
        } catch {
            return { state: "degraded", active_tasks: 0 };
        }
    }
}
