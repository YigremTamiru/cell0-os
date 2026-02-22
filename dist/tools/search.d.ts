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
export declare class SearchTool {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Executes a basic web search utilizing the intelligent provider failover
     * logic configured in the Python backend (Brave -> Google -> Bing).
     */
    query(text: string, numResults?: number): Promise<SearchResult[]>;
}
//# sourceMappingURL=search.d.ts.map