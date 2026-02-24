/**
 * Cell 0 OS — Daemon Service Controller
 *
 * Wraps launchctl (macOS) and systemctl (Linux) for
 * cell0 daemon start|stop|restart|status|install|uninstall
 */

import { execSync, execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

const PLIST_LABEL = "io.cell0.gateway";
const PLIST_PATH = path.join(os.homedir(), "Library", "LaunchAgents", "io.cell0.gateway.plist");
const SYSTEMD_UNIT = "cell0-gateway.service";

export type ServiceStatus = {
    installed: boolean;
    running: boolean;
    pid?: number;
    label?: string;
    platform: string;
    detail?: string;
};

function run(cmd: string): string {
    try {
        return execSync(cmd, { encoding: "utf-8", stdio: ["ignore", "pipe", "ignore"] }).trim();
    } catch {
        return "";
    }
}

// ─── macOS launchctl ───────────────────────────────────────────────────────

function launchctlStatus(): ServiceStatus {
    const installed = fs.existsSync(PLIST_PATH);
    const list = run(`launchctl list ${PLIST_LABEL}`);
    const running = list.includes("PID") || /^\d/.test(list.split("\n")[0] ?? "");
    const pidMatch = list.match(/"PID"\s*=\s*(\d+)/);
    const pid = pidMatch ? parseInt(pidMatch[1], 10) : undefined;
    return { installed, running, pid, label: PLIST_LABEL, platform: "darwin", detail: list || undefined };
}

function launchctlStart(): void {
    if (!fs.existsSync(PLIST_PATH)) {
        throw new Error(`Plist not found: ${PLIST_PATH}\nRun: cell0 daemon install`);
    }
    execSync(`launchctl load "${PLIST_PATH}"`, { stdio: "inherit" });
}

function launchctlStop(): void {
    if (!fs.existsSync(PLIST_PATH)) return;
    try { execSync(`launchctl unload "${PLIST_PATH}"`, { stdio: "inherit" }); } catch { /* already unloaded */ }
}

function launchctlRestart(): void {
    launchctlStop();
    setTimeout(() => launchctlStart(), 500);
}

function launchctlUninstall(): void {
    launchctlStop();
    if (fs.existsSync(PLIST_PATH)) {
        fs.unlinkSync(PLIST_PATH);
        console.log(`Removed: ${PLIST_PATH}`);
    }
}

// ─── Linux systemctl ───────────────────────────────────────────────────────

function systemctlStatus(): ServiceStatus {
    const installed = run(`systemctl --user list-unit-files ${SYSTEMD_UNIT}`).includes(SYSTEMD_UNIT);
    const active = run(`systemctl --user is-active ${SYSTEMD_UNIT}`) === "active";
    const pidLine = run(`systemctl --user show ${SYSTEMD_UNIT} --property=MainPID`);
    const pidMatch = pidLine.match(/MainPID=(\d+)/);
    const pid = pidMatch && parseInt(pidMatch[1], 10) > 0 ? parseInt(pidMatch[1], 10) : undefined;
    return { installed, running: active, pid, label: SYSTEMD_UNIT, platform: "linux" };
}

function systemctlStart(): void {
    execSync(`systemctl --user start ${SYSTEMD_UNIT}`, { stdio: "inherit" });
}

function systemctlStop(): void {
    execSync(`systemctl --user stop ${SYSTEMD_UNIT}`, { stdio: "inherit" });
}

function systemctlRestart(): void {
    execSync(`systemctl --user restart ${SYSTEMD_UNIT}`, { stdio: "inherit" });
}

function systemctlUninstall(): void {
    try { execSync(`systemctl --user disable --now ${SYSTEMD_UNIT}`, { stdio: "inherit" }); } catch { /* ignore */ }
    const unitPath = path.join(os.homedir(), ".config", "systemd", "user", SYSTEMD_UNIT);
    if (fs.existsSync(unitPath)) {
        fs.unlinkSync(unitPath);
        execSync(`systemctl --user daemon-reload`, { stdio: "inherit" });
        console.log(`Removed: ${unitPath}`);
    }
}

// ─── Public API ────────────────────────────────────────────────────────────

export function getServiceStatus(): ServiceStatus {
    if (process.platform === "darwin") return launchctlStatus();
    if (process.platform === "linux") return systemctlStatus();
    return { installed: false, running: false, platform: process.platform, detail: "Unsupported platform" };
}

export function startService(): void {
    if (process.platform === "darwin") { launchctlStart(); return; }
    if (process.platform === "linux") { systemctlStart(); return; }
    throw new Error("Unsupported platform: " + process.platform);
}

export function stopService(): void {
    if (process.platform === "darwin") { launchctlStop(); return; }
    if (process.platform === "linux") { systemctlStop(); return; }
    throw new Error("Unsupported platform: " + process.platform);
}

export function restartService(): void {
    if (process.platform === "darwin") { launchctlRestart(); return; }
    if (process.platform === "linux") { systemctlRestart(); return; }
    throw new Error("Unsupported platform: " + process.platform);
}

export function uninstallService(): void {
    if (process.platform === "darwin") { launchctlUninstall(); return; }
    if (process.platform === "linux") { systemctlUninstall(); return; }
    throw new Error("Unsupported platform: " + process.platform);
}
