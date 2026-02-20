import { appendFile, readFile, writeFile, stat } from "node:fs/promises";
import { join } from "node:path";
import { CELL0_PATHS } from "../config/config.js";
import { randomUUID } from "node:crypto";

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
export class VectorMemory {
    private memoryPath: string;

    constructor() {
        this.memoryPath = CELL0_PATHS.runtime.memory;
    }

    private getStorePath(category: string): string {
        return join(this.memoryPath, `${category}.vec`);
    }

    /**
     * Creates an empty vector store file if it does not exist.
     */
    private async ensureStoreExists(category: string): Promise<void> {
        const storePath = this.getStorePath(category);
        try {
            await stat(storePath);
        } catch {
            await writeFile(storePath, JSON.stringify([]), "utf8");
        }
    }

    /**
     * Reads the entire vector store for a specific category into memory.
     */
    private async readStore(category: string): Promise<MemoryEntry[]> {
        await this.ensureStoreExists(category);
        try {
            const raw = await readFile(this.getStorePath(category), "utf8");
            return JSON.parse(raw);
        } catch (error) {
            console.error(`[VectorMemory] Corrupt or missing store for ${category}:`, error);
            return [];
        }
    }

    /**
     * Adds a new episodic or semantic memory to a category.
     */
    async addMemory(category: string, text: string, metadata?: Record<string, unknown>): Promise<string> {
        const store = await this.readStore(category);

        const entry: MemoryEntry = {
            id: randomUUID(),
            text,
            timestamp: Date.now(),
            metadata
        };

        // Note: For actual embedding generation, this would call PythonBridge `/api/mlx/embed`
        // before writing to disk.

        store.push(entry);
        await writeFile(this.getStorePath(category), JSON.stringify(store, null, 2), "utf8");

        return entry.id;
    }

    /**
     * Searches a category's memory bank using raw text matching (Abstracted semantic stub).
     */
    async searchMemory(category: string, query: string, limit: number = 5): Promise<SearchResult[]> {
        const store = await this.readStore(category);

        // This is a naive substring stub. 
        // In a full implementation, the MLX Python daemon ranks the vector embeddings.
        const matches = store
            .map(entry => ({
                entry,
                score: entry.text.toLowerCase().includes(query.toLowerCase()) ? 1.0 : 0.0
            }))
            .filter(res => res.score > 0)
            .sort((a, b) => b.score - a.score)
            .slice(0, limit);

        return matches;
    }

    /**
     * Prunes memories older than a specified duration.
     */
    async pruneMemory(category: string, maxAgeMs: number = 30 * 24 * 60 * 60 * 1000 /* 30 days */): Promise<number> {
        const store = await this.readStore(category);
        const cutoff = Date.now() - maxAgeMs;

        const initialSize = store.length;
        const kept = store.filter(entry => entry.timestamp >= cutoff);

        if (kept.length < initialSize) {
            await writeFile(this.getStorePath(category), JSON.stringify(kept, null, 2), "utf8");
        }

        return initialSize - kept.length; // Returns number of purged entries
    }
}
