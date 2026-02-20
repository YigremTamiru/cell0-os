/**
 * Cell 0 OS — Search Tool
 *
 * Wraps the base search providers (cell0/engine/search/providers.py).
 * Delivers basic multi-engine query capabilities to Node agents.
 * Connects to Python bridge for execution.
 */

import { PythonBridge } from "../agents/python-bridge.js";

export interface SearchResult {
    title: string;
    url: string;
    snippet: string;
    source: string;
    rank: number;
    timestamp?: string;
    metadata?: Record<string, any>;
}

export class SearchTool {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Executes a basic web search utilizing the intelligent provider failover
     * logic configured in the Python backend (Brave -> Google -> Bing).
     */
    async query(text: string, numResults: number = 10): Promise<SearchResult[]> {
        if (!this.bridge.isReady()) {
            throw new Error("Python backend is not ready to perform searches.");
        }

        try {
            const response = await this.bridge.post<any>("/api/tools/search/query", {
                query: text,
                num_results: numResults
            });
            return response.results || [];
        } catch (error) {
            console.error(`[SearchTool] Query failed for '${text}':`, error);
            return [];
        }
    }
}
