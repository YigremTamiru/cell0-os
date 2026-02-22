/**
 * ContinuityManager
 *
 * Wraps `col/continuity/`.
 * Handles the slow stream of implicit human interactions (UI clicks, command frequency) and
 * pushes them back into the deep memory cache. Allows the OS to naturally evolve over months
 * of uptime by silently learning the user's habits.
 */
export class ContinuityManager {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Pushes a minor UI interaction into the slow-burn continuity pipeline.
     */
    async logInteraction(interaction) {
        if (!this.bridge.isReady())
            return false;
        try {
            await this.bridge.post("/api/col/continuity/log", interaction);
            return true;
        }
        catch {
            return false;
        }
    }
    /**
     * Retrieves the AI's current understanding of the user's implicit preferences.
     */
    async getEvolutionReport(userId) {
        if (!this.bridge.isReady())
            return null;
        try {
            return await this.bridge.get(`/api/col/continuity/report?user=${userId}`);
        }
        catch {
            return null;
        }
    }
}
//# sourceMappingURL=continuity.js.map