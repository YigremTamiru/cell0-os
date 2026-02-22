/**
 * Cell 0 OS — Terminal Theme
 *
 * Chalk-based colored output matching OpenClaw's terminal/theme.ts
 * Provides consistent styling across CLI, wizard, and banner.
 */
export declare function isRich(): boolean;
export declare const theme: {
    readonly heading: (text: string) => string;
    readonly accent: (text: string) => string;
    readonly accentBright: (text: string) => string;
    readonly accentDim: (text: string) => string;
    readonly info: (text: string) => string;
    readonly success: (text: string) => string;
    readonly warning: (text: string) => string;
    readonly error: (text: string) => string;
    readonly muted: (text: string) => string;
    readonly dim: (text: string) => string;
    readonly bold: (text: string) => string;
    readonly command: (text: string) => string;
    readonly url: (text: string) => string;
    readonly key: (text: string) => string;
    readonly value: (text: string) => string;
    readonly version: (text: string) => string;
    readonly label: (text: string) => string;
};
export declare function formatCheck(ok: boolean, message: string): string;
export declare function formatBullet(message: string): string;
export declare function formatHeader(title: string): string;
//# sourceMappingURL=theme.d.ts.map