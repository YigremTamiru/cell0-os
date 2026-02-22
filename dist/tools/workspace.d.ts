/**
 * Cell 0 OS — Workspace File System Tool
 *
 * Provides agents with secure, isolated filesystem access
 * restricted to their specific category workspace.
 * Prevents path traversal outside of ~/.cell0/workspaces/<slug>/
 */
export declare class WorkspaceTool {
    private readonly slug;
    private readonly rootDir;
    constructor(categorySlug: string);
    /**
     * Resolves a path while strictly enforcing jail bounds.
     * Prevents '../' attacks from leaving the root workspace.
     */
    private resolveSecurePath;
    /**
     * Ensures the workspace directory exists.
     */
    ensureWorkspace(): Promise<void>;
    /**
     * Reads a file from the workspace.
     */
    readFile(filePath: string): Promise<string>;
    /**
     * Writes to a file in the workspace, creating parent directories if needed.
     */
    writeFile(filePath: string, content: string): Promise<void>;
    /**
     * Lists contents of a directory in the workspace.
     */
    listDir(dirPath?: string): Promise<string[]>;
    /**
     * Deletes a file or directory in the workspace.
     */
    deleteFile(filePath: string): Promise<void>;
}
//# sourceMappingURL=workspace.d.ts.map