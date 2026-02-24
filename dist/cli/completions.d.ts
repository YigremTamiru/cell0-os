/**
 * Cell 0 OS — Shell Completions
 *
 * Generates and installs zsh and bash completion scripts for the cell0 CLI.
 * Completions are placed in ~/.cell0/completions/ and sourced from shell rc files.
 */
export declare function generateZshCompletion(): string;
export declare function generateBashCompletion(): string;
export declare function installCompletions(): Promise<void>;
export declare function uninstallCompletions(): Promise<void>;
//# sourceMappingURL=completions.d.ts.map