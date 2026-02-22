/**
 * Cell 0 OS — TUI Onboarding Wizard
 *
 * Full interactive setup wizard matching OpenClaw's onboarding flow.
 * Uses @clack/prompts for beautiful TUI elements.
 *
 * Flow:
 * 1. Banner → 2. Security warning → 3. QuickStart/Manual →
 * 4. Model provider → 5. API key → 6. Workspace → 7. Gateway config →
 * 8. Daemon install → 9. Health check → 10. Portal URL
 */
export declare function runOnboardingWizard(opts: {
    installDaemon?: boolean;
    flow?: string;
    skipChannels?: boolean;
    skipHealth?: boolean;
    acceptRisk?: boolean;
}): Promise<void>;
//# sourceMappingURL=wizard.d.ts.map