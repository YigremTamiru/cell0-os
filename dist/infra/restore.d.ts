/**
 * Cell 0 OS — Restore Infrastructure
 *
 * Wraps cell0/scripts/restore.py
 * Counterpart to backup.ts. Rollbacks filesystem states.
 */
export declare class RestoreManager {
    private projectRoot;
    constructor(projectRoot?: string);
    /**
     * Rolls back the OS to a specific snapshot archive.
     * WARNING: Destructive to current uncommitted state tracking.
     */
    restoreSnapshot(archivePath: string): Promise<boolean>;
}
//# sourceMappingURL=restore.d.ts.map