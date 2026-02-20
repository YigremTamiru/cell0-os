import { PythonBridge } from '../agents/python-bridge.js';

export interface TokenBudget {
    category: string;
    total_allowed: number;
    used: number;
    remaining: number;
}

export interface TokenTransaction {
    id: string;
    amount: number;
    type: string;
    timestamp: string;
}

/**
 * TokenEconomy
 * 
 * Wraps `col/token_economy.py`.
 * Implements mathematical API quota enforcement across distinct agent specialist categories.
 * Node.js exposes this data to the Nerve Portal Monitor Tab so the user can easily
 * track context window waste and optimize agent routing.
 */
export class TokenEconomy {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Retrieve global token budgets aggregated across all categories.
     */
    public async getBudgets(): Promise<TokenBudget[]> {
        if (!this.bridge.isReady()) return [];
        try {
            const res = await this.bridge.get<{ budgets: TokenBudget[] }>("/api/col/tokens/budgets");
            return res.budgets;
        } catch {
            return [];
        }
    }

    /**
     * Debits an arbitrary cost vector against a category.
     * Often called automatically by backend logic, but exposed here if Node tools initiate heavy I/O.
     */
    public async charge(category: string, amount: number, type: string = 'internal_request'): Promise<boolean> {
        if (!this.bridge.isReady()) return true; // Fail open if bridge drops.
        try {
            const res = await this.bridge.post<{ success: boolean }>("/api/col/tokens/charge", {
                category,
                amount,
                type
            });
            return res.success;
        } catch {
            return true;
        }
    }
}
