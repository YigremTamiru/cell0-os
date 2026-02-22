/**
 * Cell 0 OS — Daemon Manager
 *
 * Provides lifecycle controls (start, stop, restart) for
 * the core Python engine (`cell0d.py`).
 * Hooks into OS-level mechanisms like launchd (macOS) and systemd (Linux).
 */
export declare class DaemonManager {
    private projectRoot;
    private daemonProcess;
    private pythonExecutable;
    private daemonScriptPath;
    constructor(projectRoot?: string);
    /**
     * Starts the python daemon process in the background.
     */
    start(port?: number): Promise<boolean>;
    /**
     * Stops the running python daemon.
     */
    stop(): Promise<boolean>;
    /**
     * Installs the daemon to the host OS init system (launchd/systemd).
     */
    installService(): Promise<boolean>;
    private installLaunchd;
    private installSystemd;
}
//# sourceMappingURL=daemon.d.ts.map