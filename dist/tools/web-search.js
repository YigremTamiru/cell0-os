/**
 * Cell 0 OS — Enhanced Web Search Tool
 *
 * Wraps cell0/engine/tools/web_search_enhanced.py to give agents
 * deep retrieval capabilities including caching, deduplication,
 * web crawling, and categorization (web, news, academic, image).
 */
export class EnhancedWebSearchTool {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Dispatches a highly configurable search payload to the Python engine.
     */
    async search(request) {
        if (!this.bridge.isReady()) {
            throw new Error("Python backend is not ready to perform enhanced searches.");
        }
        try {
            // Defaulting optional parameters to map to Python's expected `SearchRequest` dataclass
            const payload = {
                query: request.query,
                search_type: request.searchType || "web",
                num_results: request.numResults || 10,
                providers: request.providers || null,
                use_cache: request.useCache !== false,
                enable_ranking: request.enableRanking !== false,
                enable_filtering: request.enableFiltering !== false,
                freshness: request.freshness || null,
                country: request.country || null,
                language: request.language || null,
                since: request.since || null,
                until: request.until || null,
                exclude_domains: request.excludeDomains || null,
                include_domains: request.includeDomains || null,
            };
            const response = await this.bridge.post("/api/tools/search/enhanced", payload);
            return response;
        }
        catch (error) {
            console.error("[EnhancedWebSearchTool] Search failed:", error);
            return null;
        }
    }
}
//# sourceMappingURL=web-search.js.map