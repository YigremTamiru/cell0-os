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
export class ContinuityManager {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Pushes a minor UI interaction into the slow-burn continuity pipeline.
     */
    public async logInteraction(interaction: EphemeralInteraction): Promise<boolean> {
        if (!this.bridge.isReady()) return false;
        try {
            await this.bridge.post("/api/col/continuity/log", interaction);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Retrieves the AI's current understanding of the user's implicit preferences.
     */
    public async getEvolutionReport(userId: string): Promise<ContinuityReport | null> {
        if (!this.bridge.isReady()) return null;
        try {
            return await this.bridge.get<ContinuityReport>(`/api/col/continuity/report?user=${userId}`);
        } catch {
            return null;
        }
    }
}
