/**
 * Cell 0 OS — Model/Auth Provider Registry
 *
 * All 22+ OpenClaw providers + Cell 0 unique providers (Ollama).
 * Mirrors OpenClaw's commands/auth-choice-options.ts pattern.
 */
export type AuthChoice = "openai-codex" | "openai-api-key" | "token" | "apiKey" | "chutes" | "vllm" | "minimax-portal" | "minimax-api" | "minimax-api-key-cn" | "minimax-api-lightning" | "moonshot-api-key" | "moonshot-api-key-cn" | "kimi-code-api-key" | "gemini-api-key" | "google-antigravity" | "google-gemini-cli" | "xai-api-key" | "openrouter-api-key" | "qwen-portal" | "zai-coding-global" | "zai-coding-cn" | "zai-global" | "zai-cn" | "qianfan-api-key" | "github-copilot" | "copilot-proxy" | "ai-gateway-api-key" | "opencode-zen" | "xiaomi-api-key" | "synthetic-api-key" | "together-api-key" | "huggingface-api-key" | "venice-api-key" | "litellm-api-key" | "cloudflare-ai-gateway-api-key" | "ollama" | "custom-api-key" | "skip";
export interface AuthChoiceOption {
    value: AuthChoice;
    label: string;
    hint?: string;
}
export interface AuthChoiceGroup {
    value: string;
    label: string;
    hint?: string;
    options: AuthChoiceOption[];
}
export declare function buildProviderGroups(includeSkip: boolean): {
    groups: AuthChoiceGroup[];
    skipOption?: AuthChoiceOption;
};
export declare function getProviderLabel(value: string): string;
export declare function getDefaultModelForProvider(provider: string): string;
export declare function requiresApiKey(choice: AuthChoice): boolean;
export declare function getApiKeyPrompt(choice: AuthChoice): {
    message: string;
    placeholder: string;
};
//# sourceMappingURL=providers.d.ts.map