/**
 * Cell 0 OS — Workspace File System Tool
 *
 * Provides agents with secure, isolated filesystem access
 * restricted to their specific category workspace.
 * Prevents path traversal outside of ~/.cell0/workspaces/<slug>/
 */

import fs from "node:fs/promises";
import path from "node:path";
import { CELL0_PATHS } from "../config/config.js";

export class WorkspaceTool {
    private readonly slug: string;
    private readonly rootDir: string;

    constructor(categorySlug: string) {
        this.slug = categorySlug;
        // Resolve absolute path to the agent's isolated workspace
        this.rootDir = path.resolve(path.join(CELL0_PATHS.workspaces, categorySlug));
    }

    /**
     * Resolves a path while strictly enforcing jail bounds.
     * Prevents '../' attacks from leaving the root workspace.
     */
    private resolveSecurePath(relativePath: string): string {
        // Resolve the full path
        const absolutePath = path.resolve(this.rootDir, relativePath);

        // Ensure it starts with the root directory to prevent directory traversal
        if (!absolutePath.startsWith(this.rootDir)) {
            throw new Error(`Security Exception: Path traversal denied. Access to '${relativePath}' is outside the isolated '${this.slug}' workspace.`);
        }

        return absolutePath;
    }

    /**
     * Ensures the workspace directory exists.
     */
    async ensureWorkspace(): Promise<void> {
        await fs.mkdir(this.rootDir, { recursive: true });
    }

    /**
     * Reads a file from the workspace.
     */
    async readFile(filePath: string): Promise<string> {
        const securePath = this.resolveSecurePath(filePath);
        try {
            return await fs.readFile(securePath, "utf-8");
        } catch (error: any) {
            if (error.code === 'ENOENT') {
                throw new Error(`File not found: ${filePath}`);
            }
            throw error;
        }
    }

    /**
     * Writes to a file in the workspace, creating parent directories if needed.
     */
    async writeFile(filePath: string, content: string): Promise<void> {
        const securePath = this.resolveSecurePath(filePath);
        // Ensure parent directory exists
        await fs.mkdir(path.dirname(securePath), { recursive: true });
        await fs.writeFile(securePath, content, "utf-8");
    }

    /**
     * Lists contents of a directory in the workspace.
     */
    async listDir(dirPath: string = "."): Promise<string[]> {
        const securePath = this.resolveSecurePath(dirPath);
        try {
            const entries = await fs.readdir(securePath, { withFileTypes: true });
            return entries.map(entry => {
                return entry.isDirectory() ? `${entry.name}/` : entry.name;
            });
        } catch (error: any) {
            if (error.code === 'ENOENT') {
                throw new Error(`Directory not found: ${dirPath}`);
            }
            throw error;
        }
    }

    /**
     * Deletes a file or directory in the workspace.
     */
    async deleteFile(filePath: string): Promise<void> {
        const securePath = this.resolveSecurePath(filePath);
        try {
            const stat = await fs.stat(securePath);
            if (stat.isDirectory()) {
                await fs.rm(securePath, { recursive: true, force: true });
            } else {
                await fs.unlink(securePath);
            }
        } catch (error: any) {
            if (error.code === 'ENOENT') {
                throw new Error(`Path not found: ${filePath}`);
            }
            throw error;
        }
    }
}
