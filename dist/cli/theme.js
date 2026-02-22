/**
 * Cell 0 OS — Terminal Theme
 *
 * Chalk-based colored output matching OpenClaw's terminal/theme.ts
 * Provides consistent styling across CLI, wizard, and banner.
 */
import chalk from "chalk";
// ─── Rich TTY Detection ───────────────────────────────────────────────────
export function isRich() {
    if (!process.stdout.isTTY)
        return false;
    if (process.env.NO_COLOR)
        return false;
    if (process.env.TERM === "dumb")
        return false;
    return true;
}
// ─── Theme Colors ─────────────────────────────────────────────────────────
export const theme = {
    // Brand colors — Cell 0 uses emerald/cyan tones
    heading: (text) => chalk.bold.hex("#00E5A0")(text),
    accent: (text) => chalk.hex("#00E5A0")(text),
    accentBright: (text) => chalk.bold.hex("#00FFB3")(text),
    accentDim: (text) => chalk.hex("#008F65")(text),
    // Status
    info: (text) => chalk.hex("#5EEAD4")(text),
    success: (text) => chalk.green(text),
    warning: (text) => chalk.yellow(text),
    error: (text) => chalk.red(text),
    // Text
    muted: (text) => chalk.gray(text),
    dim: (text) => chalk.dim(text),
    bold: (text) => chalk.bold(text),
    // Semantic
    command: (text) => chalk.cyan.bold(text),
    url: (text) => chalk.underline.cyan(text),
    key: (text) => chalk.yellow(text),
    value: (text) => chalk.white(text),
    version: (text) => chalk.hex("#5EEAD4")(text),
    label: (text) => chalk.hex("#00E5A0").bold(text),
};
// ─── Formatting Helpers ───────────────────────────────────────────────────
export function formatCheck(ok, message) {
    return ok
        ? `  ${chalk.green("✅")} ${message}`
        : `  ${chalk.red("❌")} ${message}`;
}
export function formatBullet(message) {
    return `  ${theme.accent("→")} ${message}`;
}
export function formatHeader(title) {
    return `\n${theme.heading(title)}\n`;
}
//# sourceMappingURL=theme.js.map