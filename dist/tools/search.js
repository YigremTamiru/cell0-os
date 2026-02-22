/**
 * Cell 0 OS — Search Tool
 *
 * Wraps the base search providers (cell0/engine/search/providers.py).
 * Delivers basic multi-engine query capabilities to Node agents.
 * Connects to Python bridge for execution.
 */
export class SearchTool {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Executes a basic web search utilizing the intelligent provider failover
     * logic configured in the Python backend (Brave -> Google -> Bing).
     */
    async query(text, numResults = 10) {
        if (!this.bridge.isReady()) {
            throw new Error("Python backend is not ready to perform searches.");
        }
        try {
            const response = await this.bridge.post("/api/tools/search/query", {
                query: text,
                num_results: numResults
            });
            return response.results || [];
        }
        catch (error) {
            console.error(`[SearchTool] Query failed for '${text}':`, error);
            return [];
        }
    }
}
//# sourceMappingURL=search.js.map