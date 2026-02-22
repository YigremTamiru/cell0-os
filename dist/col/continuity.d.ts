import { PythonBridge } from '../agents/python-bridge.js';
export interface EphemeralInteraction {
    user_id: string;
    action: string;
    context: string;
    timestamp: string;
}
export interface ContinuityReport {
    user_id: string;
    learned_preferences: string[];
    evolution_stage: number;
    last_integration: string;
}
/**
 * ContinuityManager
 *
 * Wraps `col/continuity/`.
 * Handles the slow stream of implicit human interactions (UI clicks, command frequency) and
 * pushes them back into the deep memory cache. Allows the OS to naturally evolve over months
 * of uptime by silently learning the user's habits.
 */
export declare class ContinuityManager {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Pushes a minor UI interaction into the slow-burn continuity pipeline.
     */
    logInteraction(interaction: EphemeralInteraction): Promise<boolean>;
    /**
     * Retrieves the AI's current understanding of the user's implicit preferences.
     */
    getEvolutionReport(userId: string): Promise<ContinuityReport | null>;
}
//# sourceMappingURL=continuity.d.ts.map