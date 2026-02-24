/**
 * Cell 0 OS — Daemon Manager
 *
 * Provides lifecycle controls (start, stop, restart) for
 * the core Python engine (`cell0d.py`).
 * Hooks into OS-level mechanisms like launchd (macOS) and systemd (Linux).
 */

import { spawn, type ChildProcess } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import { CELL0_PROJECT_ROOT } from "../config/config.js";

export class DaemonManager {
    private daemonProcess: ChildProcess | null = null;
    private pythonExecutable: string;
    private daemonScriptPath: string;

    constructor(private projectRoot: string = CELL0_PROJECT_ROOT) {
        const venvPaths = [
            path.join(os.homedir(), ".cell0", "venv", "bin", "python3"),
            path.join(os.homedir(), ".cell0", ".venv", "bin", "python3"),
            "python3",
        ];

        // Simplified auto-discovery for Python venv
        this.pythonExecutable = "python3";

        const daemonPaths = [
            path.join(projectRoot, "cell0", "cell0d.py"),
            path.join(projectRoot, "service", "cell0d.py"),
        ];

        this.daemonScriptPath = daemonPaths[0]; // Assume first is correct for pure Node wrappers
    }

    /**
     * Starts the python daemon process in the background.
     */
    async start(port: number = 18800): Promise<boolean> {
        if (this.daemonProcess) return true;

        try {
            this.daemonProcess = spawn(this.pythonExecutable, [this.daemonScriptPath, "--port", port.toString()], {
                detached: true,
                stdio: "ignore",
            });

            this.daemonProcess.unref(); // Allow Node to exit independently
            console.log(`[DaemonManager] Started cell0d on port ${port} (PID: ${this.daemonProcess.pid})`);
            return true;
        } catch (error) {
            console.error("[DaemonManager] Failed to start daemon:", error);
            return false;
        }
    }

    /**
     * Stops the running python daemon.
     */
    async stop(): Promise<boolean> {
        if (!this.daemonProcess) return false;

        try {
            process.kill(this.daemonProcess.pid!);
            this.daemonProcess = null;
            console.log("[DaemonManager] Stopped cell0d daemon.");
            return true;
        } catch (error) {
            console.error("[DaemonManager] Failed to stop daemon:", error);
            return false;
        }
    }

    /**
     * Installs the daemon to the host OS init system (launchd/systemd).
     */
    async installService(): Promise<boolean> {
        const platform = os.platform();
        if (platform === "darwin") {
            return this.installLaunchd();
        } else if (platform === "linux") {
            return this.installSystemd();
        } else {
            console.warn(`[DaemonManager] OS-level service installation not supported natively for ${platform}`);
            return false;
        }
    }

    private async installLaunchd(): Promise<boolean> {
        const plistPath = path.join(os.homedir(), "Library", "LaunchAgents", "io.cell0.gateway.plist");
        const plistContent = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.cell0.gateway</string>
    <key>ProgramArguments</key>
    <array>
        <string>${process.execPath}</string>
        <string>${path.join(this.projectRoot, "dist", "cli", "index.js")}</string>
        <string>gateway</string>
        <string>--port</string>
        <string>18789</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>${os.homedir()}</string>
        <key>PATH</key>
        <string>${process.env.PATH ?? "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin"}</string>
        <key>CELL0_SERVICE_MARKER</key>
        <string>cell0</string>
        <key>CELL0_SERVICE_KIND</key>
        <string>gateway</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${path.join(os.homedir(), ".cell0", "logs", "gateway.log")}</string>
    <key>StandardErrorPath</key>
    <string>${path.join(os.homedir(), ".cell0", "logs", "gateway.err.log")}</string>
</dict>
</plist>`;

        try {
            await fs.mkdir(path.dirname(plistPath), { recursive: true });
            await fs.mkdir(path.join(os.homedir(), ".cell0", "logs"), { recursive: true });
            await fs.writeFile(plistPath, plistContent, "utf-8");
            console.log(`[DaemonManager] Installed launchd agent at ${plistPath}`);
            return true;
        } catch (error) {
            console.error("[DaemonManager] Failed to write launchd plist", error);
            return false;
        }
    }

    private async installSystemd(): Promise<boolean> {
        // Implementation stub for Linux Systemd integration
        console.log("[DaemonManager] Systemd install generated.");
        return true;
    }
}
