/**
 * Cell 0 OS — Restore Infrastructure
 *
 * Wraps cell0/scripts/restore.py
 * Counterpart to backup.ts. Rollbacks filesystem states.
 */

import fs from "node:fs";
import path from "node:path";
import { exec, spawn } from "node:child_process";
import { promisify } from "node:util";
import { CELL0_PATHS, CELL0_PROJECT_ROOT } from "../config/config.js";

const execAsync = promisify(exec);

export class RestoreManager {
    constructor(private projectRoot: string = CELL0_PROJECT_ROOT) {
    }

    /**
     * Rolls back the OS to a specific snapshot archive.
     * WARNING: Destructive to current uncommitted state tracking.
     */
    async restoreSnapshot(archivePath: string): Promise<boolean> {
        return new Promise((resolve, reject) => {
            const pythonExecutable = "python3";
            const scriptPath = path.join(this.projectRoot, "cell0", "scripts", "restore.py");

            const restoreProcess = spawn(pythonExecutable, [
                scriptPath,
                "--source", archivePath
            ]);

            let errString = "";
            restoreProcess.stderr.on("data", (data) => errString += data.toString());

            restoreProcess.on("close", (code) => {
                if (code === 0) {
                    console.log(`[RestoreManager] System successfully rolled back to ${archivePath}.`);
                    resolve(true);
                } else {
                    console.error("[RestoreManager] Restore error:", errString);
                    reject(new Error(`Restore script failed with code ${code}`));
                }
            });
        });
    }
}
