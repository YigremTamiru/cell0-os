/**
 * Cell 0 OS — Logger
 *
 * File-based logging system that writes to runtime/logs/cell0.log
 * Supports rotation and console fallback.
 */
declare class Logger {
    private logFile;
    private initialized;
    constructor();
    private ensureLogDir;
    private write;
    info(message: string, meta?: unknown): void;
    warn(message: string, meta?: unknown): void;
    error(message: string, meta?: unknown): void;
    debug(message: string, meta?: unknown): void;
}
export declare const logger: Logger;
export {};
//# sourceMappingURL=logger.d.ts.map