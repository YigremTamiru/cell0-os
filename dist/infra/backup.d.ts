/**
 * Cell 0 OS — Backup Infrastructure
 *
 * Wraps cell0/scripts/backup.py
 * Allows agents/users to trigger immediate snapshotting of identities and states.
 */
export declare class BackupManager {
    private projectRoot;
    constructor(projectRoot?: string);
    /**
     * Triggers a fast .tar.gz snapshot of critical user volumes.
     * Maps securely back to the Python backend utilities.
     */
    snapshot(compress?: boolean): Promise<string>;
}
//# sourceMappingURL=backup.d.ts.map