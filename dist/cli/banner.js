/**
 * Cell 0 OS — CLI Banner
 *
 * ASCII art banner + version line, matching OpenClaw's banner.ts pattern.
 * Displays themed Cell 0 branding on CLI startup.
 */
import { isRich, theme } from "./theme.js";
// ─── Taglines ─────────────────────────────────────────────────────────────
const TAGLINES = [
    "Your sovereign edge AI operating system.",
    "Intelligence at the edge. Privacy at the core.",
    "Decentralized intelligence, locally sovereign.",
    "Post-quantum secure. Locally autonomous.",
    "Where compute meets consciousness.",
    "The OS that thinks with you, not for you.",
    "Edge-native intelligence. No cloud required.",
    "Sovereign AI for sovereign minds.",
    "Your thoughts, your hardware, your rules.",
    "Intelligence that lives where you do.",
];
export function pickTagline() {
    return TAGLINES[Math.floor(Math.random() * TAGLINES.length)];
}
// ─── ASCII Art ────────────────────────────────────────────────────────────
const CELL0_ASCII = [
    "▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄",
    "██░▄▄▀██░▄▄▄██░████░████░████░▄▄▄░██░▄▄▄░█████",
    "██░████░▄▄▄██░████░████░████░███░█░█░▪▪▪░█████",
    "██░▀▀▄██░▀▀▀██░▀▀░█░▀▀░█░▀▀░█░▀▀▀░█▀▄▀█░▀▀▀██",
    "▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀",
    "               🧬 CELL 0 🧬                    ",
];
// ─── Banner Formatting ────────────────────────────────────────────────────
let bannerEmitted = false;
export function formatBannerLine(version) {
    const tagline = pickTagline();
    const title = "🧬 Cell 0 OS";
    const rich = isRich();
    if (rich) {
        return `${theme.heading(title)} ${theme.version(version)}\n   ${theme.accentDim(tagline)}`;
    }
    return `${title} ${version}\n   ${tagline}`;
}
export function formatBannerArt() {
    const rich = isRich();
    if (!rich) {
        return CELL0_ASCII.join("\n");
    }
    const colorChar = (ch) => {
        if (ch === "█")
            return theme.accentBright(ch);
        if (ch === "░")
            return theme.accentDim(ch);
        if (ch === "▀" || ch === "▄")
            return theme.accent(ch);
        return theme.muted(ch);
    };
    const colored = CELL0_ASCII.map((line) => {
        if (line.includes("CELL 0")) {
            return ("               " +
                theme.accent("🧬") +
                theme.info(" CELL 0 ") +
                theme.accent("🧬"));
        }
        return Array.from(line).map(colorChar).join("");
    });
    return colored.join("\n");
}
export function emitBanner(version) {
    if (bannerEmitted)
        return;
    if (!process.stdout.isTTY)
        return;
    const argv = process.argv;
    if (argv.some((a) => a === "--json" || a === "--version" || a === "-V"))
        return;
    const line = formatBannerLine(version);
    process.stdout.write(`\n${line}\n\n`);
    bannerEmitted = true;
}
export function emitBannerArt(version) {
    if (!process.stdout.isTTY)
        return;
    const art = formatBannerArt();
    const line = formatBannerLine(version);
    process.stdout.write(`\n${art}\n\n${line}\n\n`);
    bannerEmitted = true;
}
export function hasEmittedBanner() {
    return bannerEmitted;
}
//# sourceMappingURL=banner.js.map