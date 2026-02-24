/**
 * Cell 0 OS — Ethics Consensus Component (Layer 3: The Brain)
 *
 * Implements the Ethics layer from the sovereign architecture:
 * Fairness, Transparency, Security checks on all autonomous AI actions.
 *
 * The ethics engine runs BEFORE any autonomous action is executed,
 * ensuring Cell 0 OS maintains sovereign alignment and user trust.
 */

import fs from "node:fs";
import path from "node:path";
import os from "node:os";

const ETHICS_LOG = path.join(os.homedir(), ".cell0", "runtime", "ethics-log.jsonl");

export type EthicsVerdict = "approved" | "flagged" | "rejected";

export interface EthicsCheck {
    name: string;
    passed: boolean;
    severity: "info" | "warning" | "critical";
    reason?: string;
}

export interface EthicsDecision {
    timestamp: string;
    actionType: string;
    action: string;
    verdict: EthicsVerdict;
    checks: EthicsCheck[];
    overrideAllowed: boolean;
}

// ─── Core Ethics Rules ─────────────────────────────────────────────────────

const RULES: Array<{
    name: string;
    severity: "info" | "warning" | "critical";
    test: (action: string, ctx: Record<string, unknown>) => { passed: boolean; reason?: string };
}> = [
    {
        name: "No self-deletion",
        severity: "critical",
        test: (a) => ({
            passed: !/(rm\s+-rf|unlinkSync|rmSync).*\.cell0/i.test(a),
            reason: "Action would delete Cell 0 core files",
        }),
    },
    {
        name: "No privilege escalation",
        severity: "critical",
        test: (a) => ({
            passed: !/(sudo\s+chmod|sudo\s+chown|sudo\s+rm|chmod\s+777)/i.test(a),
            reason: "Action attempts privilege escalation",
        }),
    },
    {
        name: "No data exfiltration",
        severity: "critical",
        test: (a) => ({
            passed: !/(curl|wget|fetch).*\.(cell0|credentials|\.ssh)/i.test(a),
            reason: "Action may exfiltrate local credentials",
        }),
    },
    {
        name: "Transparency principle",
        severity: "warning",
        test: (_, ctx) => ({
            passed: ctx.isHidden !== true,
            reason: "Action is taken without user visibility",
        }),
    },
    {
        name: "Resource limits",
        severity: "warning",
        test: (a) => ({
            passed: !/(while\s*\(true\)|setInterval.*0\b|fork.*loop)/i.test(a),
            reason: "Action may exhaust system resources",
        }),
    },
    {
        name: "Data sovereignty",
        severity: "warning",
        test: (a) => ({
            passed: !/(POST|PUT|PATCH).*private|upload.*home\//i.test(a),
            reason: "Action may send local data externally without consent",
        }),
    },
];

export class EthicsConsensus {
    evaluate(
        actionType: string,
        action: string,
        context: Record<string, unknown> = {}
    ): EthicsDecision {
        const checks: EthicsCheck[] = RULES.map((rule) => {
            const result = rule.test(action, context);
            return {
                name: rule.name,
                passed: result.passed,
                severity: rule.severity,
                reason: result.passed ? undefined : result.reason,
            };
        });

        const criticalFail = checks.some((c) => !c.passed && c.severity === "critical");
        const warningFail = checks.some((c) => !c.passed && c.severity === "warning");

        const verdict: EthicsVerdict = criticalFail ? "rejected" : warningFail ? "flagged" : "approved";

        const decision: EthicsDecision = {
            timestamp: new Date().toISOString(),
            actionType,
            action,
            verdict,
            checks,
            overrideAllowed: verdict === "flagged",
        };

        this.log(decision);
        return decision;
    }

    isApproved(decision: EthicsDecision): boolean {
        return decision.verdict === "approved" || decision.verdict === "flagged";
    }

    private log(decision: EthicsDecision): void {
        try {
            const dir = path.dirname(ETHICS_LOG);
            if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
            fs.appendFileSync(ETHICS_LOG, JSON.stringify(decision) + "\n");
        } catch { /* non-fatal */ }
    }

    getRecentDecisions(limit = 50): EthicsDecision[] {
        if (!fs.existsSync(ETHICS_LOG)) return [];
        try {
            return fs
                .readFileSync(ETHICS_LOG, "utf-8")
                .trim()
                .split("\n")
                .filter(Boolean)
                .slice(-limit)
                .map((l) => JSON.parse(l) as EthicsDecision);
        } catch { return []; }
    }
}
