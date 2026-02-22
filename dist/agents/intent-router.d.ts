import { PythonBridge } from "./python-bridge.js";
export interface IntentScore {
    category: string;
    specialist?: string;
    confidence: number;
    intent_tag: string;
}
/**
 * IntentRouter
 *
 * Maps to `col/classifier.py`.
 * Uses "Recognition Seed scoring" to analyze incoming natural language
 * and route it to the correct Agent Library Specialist.
 *
 * Example: "Book a flight to Paris" ->
 *   category: 'travel', specialist: 'flight-oracle', confidence: 0.95
 */
export declare class IntentRouter {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Scores the raw text input to determine the most relevant cognitive domain
     * and specific agent persona needed for fulfillment.
     */
    scoreIntent(text: string, contextWindow?: string[]): Promise<IntentScore>;
    /**
     * Fallback heuristic scoring if the python daemon is disconnected or fails.
     */
    private fallbackHeuristicScore;
}
//# sourceMappingURL=intent-router.d.ts.map