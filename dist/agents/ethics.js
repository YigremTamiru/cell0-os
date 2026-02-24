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
// ─── Core Ethics Rules ─────────────────────────────────────────────────────
const RULES = [
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
    evaluate(actionType, action, context = {}) {
        const checks = RULES.map((rule) => {
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
        const verdict = criticalFail ? "rejected" : warningFail ? "flagged" : "approved";
        const decision = {
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
    isApproved(decision) {
        return decision.verdict === "approved" || decision.verdict === "flagged";
    }
    log(decision) {
        try {
            const dir = path.dirname(ETHICS_LOG);
            if (!fs.existsSync(dir))
                fs.mkdirSync(dir, { recursive: true });
            fs.appendFileSync(ETHICS_LOG, JSON.stringify(decision) + "\n");
        }
        catch { /* non-fatal */ }
    }
    getRecentDecisions(limit = 50) {
        if (!fs.existsSync(ETHICS_LOG))
            return [];
        try {
            return fs
                .readFileSync(ETHICS_LOG, "utf-8")
                .trim()
                .split("\n")
                .filter(Boolean)
                .slice(-limit)
                .map((l) => JSON.parse(l));
        }
        catch {
            return [];
        }
    }
}
//# sourceMappingURL=ethics.js.map