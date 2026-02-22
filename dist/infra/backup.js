/**
 * Cell 0 OS — Backup Infrastructure
 *
 * Wraps cell0/scripts/backup.py
 * Allows agents/users to trigger immediate snapshotting of identities and states.
 */
import { spawn } from "node:child_process";
import path from "node:path";
import { CELL0_PATHS, CELL0_PROJECT_ROOT } from "../config/config.js";
export class BackupManager {
    projectRoot;
    constructor(projectRoot = CELL0_PROJECT_ROOT) {
        this.projectRoot = projectRoot;
    }
    /**
     * Triggers a fast .tar.gz snapshot of critical user volumes.
     * Maps securely back to the Python backend utilities.
     */
    async snapshot(compress = true) {
        return new Promise((resolve, reject) => {
            const pythonExecutable = "python3";
            const scriptPath = path.join(this.projectRoot, "cell0", "scripts", "backup.py");
            // Backup Python script is expected to output the destination filepath
            const backupProcess = spawn(pythonExecutable, [
                scriptPath,
                "--compress", compress.toString(),
                "--dest", CELL0_PATHS.snapshots
            ]);
            let output = "";
            let errString = "";
            backupProcess.stdout.on("data", (data) => output += data.toString());
            backupProcess.stderr.on("data", (data) => errString += data.toString());
            backupProcess.on("close", (code) => {
                if (code === 0) {
                    console.log("[BackupManager] Snapshot created successfully.");
                    // Extract the final file path or hash from the stdout. E.g "Snapshot: /path/to/snap.tar.gz"
                    const match = output.match(/Snapshot: (.+)/);
                    resolve(match ? match[1].trim() : "Snapshot Complete");
                }
                else {
                    console.error("[BackupManager] Snapshot error:", errString);
                    reject(new Error(`Backup script failed with code ${code}`));
                }
            });
        });
    }
}
//# sourceMappingURL=backup.js.map