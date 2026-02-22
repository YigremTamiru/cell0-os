export interface MemoryEntry {
    id: string;
    text: string;
    timestamp: number;
    metadata?: Record<string, unknown>;
    embedding?: number[];
}
export interface SearchResult {
    entry: MemoryEntry;
    score: number;
}
/**
 * VectorMemory
 *
 * Provides Node.js managed file I/O for the category-specific vector stores
 * located at `~/.cell0/runtime/memory/<category>.vec`.
 * While Node manages the disk interactions, complex semantic search
 * and embedding generation will likely be deferred to the MLX-accelerated Python daemon.
 */
export declare class VectorMemory {
    private memoryPath;
    constructor();
    private getStorePath;
    /**
     * Creates an empty vector store file if it does not exist.
     */
    private ensureStoreExists;
    /**
     * Reads the entire vector store for a specific category into memory.
     */
    private readStore;
    /**
     * Adds a new episodic or semantic memory to a category.
     */
    addMemory(category: string, text: string, metadata?: Record<string, unknown>): Promise<string>;
    /**
     * Searches a category's memory bank using raw text matching (Abstracted semantic stub).
     */
    searchMemory(category: string, query: string, limit?: number): Promise<SearchResult[]>;
    /**
     * Prunes memories older than a specified duration.
     */
    pruneMemory(category: string, maxAgeMs?: number): Promise<number>;
}
//# sourceMappingURL=memory.d.ts.map