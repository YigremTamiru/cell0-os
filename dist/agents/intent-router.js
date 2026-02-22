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
export class IntentRouter {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Scores the raw text input to determine the most relevant cognitive domain
     * and specific agent persona needed for fulfillment.
     */
    async scoreIntent(text, contextWindow) {
        if (!this.bridge.isReady()) {
            console.warn("[IntentRouter] Python backend not ready, falling back to heuristics");
            return this.fallbackHeuristicScore(text);
        }
        try {
            // Note: Currently hypothetical API endpoint mapping to the Python `col/classifier.py`
            const result = await this.bridge.post("/api/col/classify", {
                text,
                context: contextWindow || []
            });
            return {
                category: result.category || "other",
                specialist: result.specialist,
                confidence: result.confidence || 0.5,
                intent_tag: result.intent_tag || "unknown"
            };
        }
        catch (error) {
            console.error("[IntentRouter] Intent classification failed:", error);
            return this.fallbackHeuristicScore(text);
        }
    }
    /**
     * Fallback heuristic scoring if the python daemon is disconnected or fails.
     */
    fallbackHeuristicScore(text) {
        const lower = text.toLowerCase();
        let category = "other";
        let confidence = 0.5;
        let intent_tag = "fallback_heuristic";
        if (lower.includes("book") || lower.includes("flight") || lower.includes("hotel")) {
            category = "travel";
            confidence = 0.7;
        }
        else if (lower.includes("buy") || lower.includes("stock") || lower.includes("market") || lower.includes("pay")) {
            category = "finance";
            confidence = 0.7;
        }
        else if (lower.includes("hello") || lower.includes("hi") || lower.includes("ping")) {
            category = "social";
            confidence = 0.8;
            intent_tag = "greeting";
        }
        else if (lower.includes("remind") || lower.includes("schedule") || lower.includes("task")) {
            category = "productivity";
            confidence = 0.7;
        }
        return { category, confidence, intent_tag };
    }
}
//# sourceMappingURL=intent-router.js.map