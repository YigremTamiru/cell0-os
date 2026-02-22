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
export declare class COLBridge {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Submits a complex reasoning operation to the Python Cognitive Operating Layer.
     */
    submitOperation(operation: CognitiveOperation): Promise<CognitiveResult>;
    /**
     * Retrieves the active state of the Python Orchestrator engine.
     */
    getOrchestratorState(): Promise<{
        state: string;
        active_tasks: number;
    }>;
}
//# sourceMappingURL=bridge.d.ts.map