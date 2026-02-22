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
export declare class TokenEconomy {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Retrieve global token budgets aggregated across all categories.
     */
    getBudgets(): Promise<TokenBudget[]>;
    /**
     * Debits an arbitrary cost vector against a category.
     * Often called automatically by backend logic, but exposed here if Node tools initiate heavy I/O.
     */
    charge(category: string, amount: number, type?: string): Promise<boolean>;
}
//# sourceMappingURL=token_economy.d.ts.map