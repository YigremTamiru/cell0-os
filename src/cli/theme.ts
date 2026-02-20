/**
 * Cell 0 OS — Terminal Theme
 *
 * Chalk-based colored output matching OpenClaw's terminal/theme.ts
 * Provides consistent styling across CLI, wizard, and banner.
 */

import chalk from "chalk";

// ─── Rich TTY Detection ───────────────────────────────────────────────────

export function isRich(): boolean {
    if (!process.stdout.isTTY) return false;
    if (process.env.NO_COLOR) return false;
    if (process.env.TERM === "dumb") return false;
    return true;
}

// ─── Theme Colors ─────────────────────────────────────────────────────────

export const theme = {
    // Brand colors — Cell 0 uses emerald/cyan tones
    heading: (text: string) => chalk.bold.hex("#00E5A0")(text),
    accent: (text: string) => chalk.hex("#00E5A0")(text),
    accentBright: (text: string) => chalk.bold.hex("#00FFB3")(text),
    accentDim: (text: string) => chalk.hex("#008F65")(text),

    // Status
    info: (text: string) => chalk.hex("#5EEAD4")(text),
    success: (text: string) => chalk.green(text),
    warning: (text: string) => chalk.yellow(text),
    error: (text: string) => chalk.red(text),

    // Text
    muted: (text: string) => chalk.gray(text),
    dim: (text: string) => chalk.dim(text),
    bold: (text: string) => chalk.bold(text),

    // Semantic
    command: (text: string) => chalk.cyan.bold(text),
    url: (text: string) => chalk.underline.cyan(text),
    key: (text: string) => chalk.yellow(text),
    value: (text: string) => chalk.white(text),
    version: (text: string) => chalk.hex("#5EEAD4")(text),
    label: (text: string) => chalk.hex("#00E5A0").bold(text),
} as const;

// ─── Formatting Helpers ───────────────────────────────────────────────────

export function formatCheck(ok: boolean, message: string): string {
    return ok
        ? `  ${chalk.green("✅")} ${message}`
        : `  ${chalk.red("❌")} ${message}`;
}

export function formatBullet(message: string): string {
    return `  ${theme.accent("→")} ${message}`;
}

export function formatHeader(title: string): string {
    return `\n${theme.heading(title)}\n`;
}
