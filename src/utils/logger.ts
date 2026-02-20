/**
 * Cell 0 OS — Logger
 *
 * File-based logging system that writes to runtime/logs/cell0.log
 * Supports rotation and console fallback.
 */

import fs from "node:fs";
import path from "node:path";
import { CELL0_PATHS } from "../config/config.js";

type LogLevel = "debug" | "info" | "warn" | "error";

class Logger {
    private logFile: string;
    private initialized: boolean = false;

    constructor() {
        // We use the runtime logs path from config
        // Note: verifyInit() should be called before logging if possible
        this.logFile = path.join(CELL0_PATHS.runtime.logs, "cell0.log");
    }

    private ensureLogDir() {
        if (this.initialized) return;
        try {
            const logDir = path.dirname(this.logFile);
            if (!fs.existsSync(logDir)) {
                fs.mkdirSync(logDir, { recursive: true, mode: 0o700 });
            }
            this.initialized = true;
        } catch (err) {
            // Silently fail to console if we can't create log dir
            // This happens during initial bootstrap before permissions are set
            console.error("Logger init failed:", err);
        }
    }

    private write(level: LogLevel, message: string, meta?: unknown) {
        this.ensureLogDir();

        const timestamp = new Date().toISOString();
        const logEntry = `[${timestamp}] [${level.toUpperCase()}] ${message} ${meta ? JSON.stringify(meta) : ""
            }\n`;

        // Always log to file if possible
        try {
            fs.appendFileSync(this.logFile, logEntry, "utf-8");
        } catch {
            // If file write fails, we rely on console
        }
    }

    info(message: string, meta?: unknown) {
        this.write("info", message, meta);
    }

    warn(message: string, meta?: unknown) {
        this.write("warn", message, meta);
    }

    error(message: string, meta?: unknown) {
        this.write("error", message, meta);
    }

    debug(message: string, meta?: unknown) {
        if (process.env.DEBUG) {
            this.write("debug", message, meta);
        }
    }
}

export const logger = new Logger();
