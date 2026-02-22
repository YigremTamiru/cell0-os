/**
 * TokenEconomy
 *
 * Wraps `col/token_economy.py`.
 * Implements mathematical API quota enforcement across distinct agent specialist categories.
 * Node.js exposes this data to the Nerve Portal Monitor Tab so the user can easily
 * track context window waste and optimize agent routing.
 */
export class TokenEconomy {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Retrieve global token budgets aggregated across all categories.
     */
    async getBudgets() {
        if (!this.bridge.isReady())
            return [];
        try {
            const res = await this.bridge.get("/api/col/tokens/budgets");
            return res.budgets;
        }
        catch {
            return [];
        }
    }
    /**
     * Debits an arbitrary cost vector against a category.
     * Often called automatically by backend logic, but exposed here if Node tools initiate heavy I/O.
     */
    async charge(category, amount, type = 'internal_request') {
        if (!this.bridge.isReady())
            return true; // Fail open if bridge drops.
        try {
            const res = await this.bridge.post("/api/col/tokens/charge", {
                category,
                amount,
                type
            });
            return res.success;
        }
        catch {
            return true;
        }
    }
}
//# sourceMappingURL=token_economy.js.map