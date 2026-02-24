/**
 * Cell 0 OS — Daemon Service Controller
 *
 * Wraps launchctl (macOS) and systemctl (Linux) for
 * cell0 daemon start|stop|restart|status|install|uninstall
 */
export type ServiceStatus = {
    installed: boolean;
    running: boolean;
    pid?: number;
    label?: string;
    platform: string;
    detail?: string;
};
export declare function getServiceStatus(): ServiceStatus;
export declare function startService(): void;
export declare function stopService(): void;
export declare function restartService(): void;
export declare function uninstallService(): void;
//# sourceMappingURL=daemon-ctl.d.ts.map