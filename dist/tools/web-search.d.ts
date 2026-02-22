/**
 * Cell 0 OS — Enhanced Web Search Tool
 *
 * Wraps cell0/engine/tools/web_search_enhanced.py to give agents
 * deep retrieval capabilities including caching, deduplication,
 * web crawling, and categorization (web, news, academic, image).
 */
import { PythonBridge } from "../agents/python-bridge.js";
import { SearchResult } from "./search.js";
export type SearchType = "web" | "news" | "image" | "academic";
export interface EnhancedSearchRequest {
    query: string;
    searchType?: SearchType;
    numResults?: number;
    providers?: string[];
    useCache?: boolean;
    enableRanking?: boolean;
    enableFiltering?: boolean;
    freshness?: "pd" | "pw" | "pm" | "py";
    country?: string;
    language?: string;
    since?: string;
    until?: string;
    excludeDomains?: string[];
    includeDomains?: string[];
}
export interface EnhancedSearchResponse {
    query: string;
    searchType: SearchType;
    results: SearchResult[];
    totalResults: number;
    providersUsed: string[];
    cached: boolean;
    executionTimeMs: number;
    timestamp: string;
    metadata?: Record<string, any>;
}
export declare class EnhancedWebSearchTool {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Dispatches a highly configurable search payload to the Python engine.
     */
    search(request: EnhancedSearchRequest): Promise<EnhancedSearchResponse | null>;
}
//# sourceMappingURL=web-search.d.ts.map