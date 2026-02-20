/**
 * Cell 0 OS — Model/Auth Provider Registry
 *
 * All 22+ OpenClaw providers + Cell 0 unique providers (Ollama).
 * Mirrors OpenClaw's commands/auth-choice-options.ts pattern.
 */

// ─── Types ────────────────────────────────────────────────────────────────

export type AuthChoice =
    | "openai-codex"
    | "openai-api-key"
    | "token"
    | "apiKey"
    | "chutes"
    | "vllm"
    | "minimax-portal"
    | "minimax-api"
    | "minimax-api-key-cn"
    | "minimax-api-lightning"
    | "moonshot-api-key"
    | "moonshot-api-key-cn"
    | "kimi-code-api-key"
    | "gemini-api-key"
    | "google-antigravity"
    | "google-gemini-cli"
    | "xai-api-key"
    | "openrouter-api-key"
    | "qwen-portal"
    | "zai-coding-global"
    | "zai-coding-cn"
    | "zai-global"
    | "zai-cn"
    | "qianfan-api-key"
    | "github-copilot"
    | "copilot-proxy"
    | "ai-gateway-api-key"
    | "opencode-zen"
    | "xiaomi-api-key"
    | "synthetic-api-key"
    | "together-api-key"
    | "huggingface-api-key"
    | "venice-api-key"
    | "litellm-api-key"
    | "cloudflare-ai-gateway-api-key"
    | "ollama"
    | "custom-api-key"
    | "skip";

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

// ─── Provider Groups ──────────────────────────────────────────────────────

interface ProviderGroupDef {
    value: string;
    label: string;
    hint?: string;
    choices: AuthChoice[];
}

const PROVIDER_GROUP_DEFS: ProviderGroupDef[] = [
    {
        value: "openai",
        label: "OpenAI",
        hint: "Codex OAuth + API key",
        choices: ["openai-codex", "openai-api-key"],
    },
    {
        value: "anthropic",
        label: "Anthropic",
        hint: "Setup-token + API key",
        choices: ["token", "apiKey"],
    },
    {
        value: "minimax",
        label: "MiniMax",
        hint: "M2.5 (recommended)",
        choices: ["minimax-portal", "minimax-api", "minimax-api-key-cn", "minimax-api-lightning"],
    },
    {
        value: "moonshot",
        label: "Moonshot AI (Kimi K2.5)",
        hint: "Kimi K2.5 + Kimi Coding",
        choices: ["moonshot-api-key", "moonshot-api-key-cn", "kimi-code-api-key"],
    },
    {
        value: "google",
        label: "Google",
        hint: "Gemini API key + OAuth",
        choices: ["gemini-api-key", "google-antigravity", "google-gemini-cli"],
    },
    {
        value: "xai",
        label: "xAI (Grok)",
        hint: "API key",
        choices: ["xai-api-key"],
    },
    {
        value: "openrouter",
        label: "OpenRouter",
        hint: "API key",
        choices: ["openrouter-api-key"],
    },
    {
        value: "qwen",
        label: "Qwen",
        hint: "OAuth",
        choices: ["qwen-portal"],
    },
    {
        value: "zai",
        label: "Z.AI (GLM 4.7)",
        hint: "GLM Coding Plan / Global / CN",
        choices: ["zai-coding-global", "zai-coding-cn", "zai-global", "zai-cn"],
    },
    {
        value: "qianfan",
        label: "Qianfan",
        hint: "API key",
        choices: ["qianfan-api-key"],
    },
    {
        value: "copilot",
        label: "Copilot",
        hint: "GitHub + local proxy",
        choices: ["github-copilot", "copilot-proxy"],
    },
    {
        value: "ai-gateway",
        label: "Vercel AI Gateway",
        hint: "API key",
        choices: ["ai-gateway-api-key"],
    },
    {
        value: "opencode-zen",
        label: "OpenCode Zen",
        hint: "API key",
        choices: ["opencode-zen"],
    },
    {
        value: "xiaomi",
        label: "Xiaomi",
        hint: "API key",
        choices: ["xiaomi-api-key"],
    },
    {
        value: "synthetic",
        label: "Synthetic",
        hint: "Anthropic-compatible (multi-model)",
        choices: ["synthetic-api-key"],
    },
    {
        value: "together",
        label: "Together AI",
        hint: "API key",
        choices: ["together-api-key"],
    },
    {
        value: "huggingface",
        label: "Hugging Face",
        hint: "Inference API (HF token)",
        choices: ["huggingface-api-key"],
    },
    {
        value: "venice",
        label: "Venice AI",
        hint: "Privacy-focused (uncensored models)",
        choices: ["venice-api-key"],
    },
    {
        value: "litellm",
        label: "LiteLLM",
        hint: "Unified LLM gateway (100+ providers)",
        choices: ["litellm-api-key"],
    },
    {
        value: "cloudflare-ai-gateway",
        label: "Cloudflare AI Gateway",
        hint: "Account ID + Gateway ID + API key",
        choices: ["cloudflare-ai-gateway-api-key"],
    },
    // Cell 0 unique providers
    {
        value: "ollama",
        label: "Ollama (Local)",
        hint: "No auth — uses local Ollama + MLX bridge",
        choices: ["ollama"],
    },
    {
        value: "vllm",
        label: "vLLM",
        hint: "Local/self-hosted OpenAI-compatible",
        choices: ["vllm"],
    },
    {
        value: "custom",
        label: "Custom Provider",
        hint: "Any OpenAI or Anthropic compatible endpoint",
        choices: ["custom-api-key"],
    },
];

// ─── Option Labels ────────────────────────────────────────────────────────

const AUTH_CHOICE_OPTIONS: AuthChoiceOption[] = [
    { value: "openai-codex", label: "OpenAI Codex (ChatGPT OAuth)" },
    { value: "openai-api-key", label: "OpenAI API key" },
    { value: "token", label: "Anthropic token (paste setup-token)", hint: 'run `claude setup-token`' },
    { value: "apiKey", label: "Anthropic API key" },
    { value: "chutes", label: "Chutes (OAuth)" },
    { value: "vllm", label: "vLLM (custom URL + model)", hint: "Local/self-hosted OpenAI-compatible" },
    { value: "minimax-portal", label: "MiniMax OAuth" },
    { value: "minimax-api", label: "MiniMax M2.5" },
    { value: "minimax-api-key-cn", label: "MiniMax M2.5 (CN)", hint: "China endpoint" },
    { value: "minimax-api-lightning", label: "MiniMax M2.5 Lightning", hint: "Faster" },
    { value: "moonshot-api-key", label: "Kimi API key (.ai)" },
    { value: "moonshot-api-key-cn", label: "Kimi API key (.cn)" },
    { value: "kimi-code-api-key", label: "Kimi Code API key (subscription)" },
    { value: "gemini-api-key", label: "Google Gemini API key" },
    { value: "google-antigravity", label: "Google Antigravity OAuth", hint: "Bundled auth plugin" },
    { value: "google-gemini-cli", label: "Google Gemini CLI OAuth" },
    { value: "xai-api-key", label: "xAI (Grok) API key" },
    { value: "openrouter-api-key", label: "OpenRouter API key" },
    { value: "qwen-portal", label: "Qwen OAuth" },
    { value: "zai-coding-global", label: "Coding-Plan-Global", hint: "GLM Coding Plan Global (api.z.ai)" },
    { value: "zai-coding-cn", label: "Coding-Plan-CN", hint: "GLM Coding Plan CN (open.bigmodel.cn)" },
    { value: "zai-global", label: "Global", hint: "Z.AI Global (api.z.ai)" },
    { value: "zai-cn", label: "CN", hint: "Z.AI CN (open.bigmodel.cn)" },
    { value: "qianfan-api-key", label: "Qianfan API key" },
    { value: "github-copilot", label: "GitHub Copilot (GitHub device login)", hint: "Uses GitHub device flow" },
    { value: "copilot-proxy", label: "Copilot Proxy (local)", hint: "Local proxy for VS Code Copilot" },
    { value: "ai-gateway-api-key", label: "Vercel AI Gateway API key" },
    { value: "opencode-zen", label: "OpenCode Zen (multi-model proxy)", hint: "Claude, GPT, Gemini" },
    { value: "xiaomi-api-key", label: "Xiaomi API key" },
    { value: "synthetic-api-key", label: "Synthetic API key" },
    { value: "together-api-key", label: "Together AI API key", hint: "Llama, DeepSeek, Qwen" },
    { value: "huggingface-api-key", label: "Hugging Face API key (HF token)", hint: "Inference Providers" },
    { value: "venice-api-key", label: "Venice AI API key", hint: "Privacy-focused inference" },
    { value: "litellm-api-key", label: "LiteLLM API key", hint: "Unified gateway for 100+ providers" },
    { value: "cloudflare-ai-gateway-api-key", label: "Cloudflare AI Gateway", hint: "Account + Gateway + API key" },
    { value: "ollama", label: "Ollama (local models)", hint: "No auth — uses local Ollama instance" },
    { value: "custom-api-key", label: "Custom Provider" },
    { value: "skip", label: "Skip for now" },
];

// ─── Build Functions ──────────────────────────────────────────────────────

const optionByValue = new Map<AuthChoice, AuthChoiceOption>(
    AUTH_CHOICE_OPTIONS.map((opt) => [opt.value, opt])
);

export function buildProviderGroups(includeSkip: boolean): {
    groups: AuthChoiceGroup[];
    skipOption?: AuthChoiceOption;
} {
    const groups: AuthChoiceGroup[] = PROVIDER_GROUP_DEFS.map((group) => ({
        value: group.value,
        label: group.label,
        hint: group.hint,
        options: group.choices
            .map((choice) => optionByValue.get(choice))
            .filter((opt): opt is AuthChoiceOption => Boolean(opt)),
    }));

    const skipOption = includeSkip
        ? { value: "skip" as AuthChoice, label: "Skip for now" }
        : undefined;

    return { groups, skipOption };
}

export function getProviderLabel(value: string): string {
    const group = PROVIDER_GROUP_DEFS.find((g) => g.value === value);
    return group?.label ?? value;
}

export function getDefaultModelForProvider(provider: string): string {
    const defaults: Record<string, string> = {
        openai: "openai/gpt-4o",
        anthropic: "anthropic/claude-opus-4-6",
        minimax: "minimax/m2.5",
        moonshot: "moonshot/kimi-k2.5",
        google: "google/gemini-2.5-pro",
        xai: "xai/grok-3",
        openrouter: "openrouter/auto",
        qwen: "qwen/qwen-max",
        zai: "zai/glm-4.7",
        copilot: "copilot/gpt-4o",
        ollama: "ollama/llama3.3",
        vllm: "vllm/custom",
        custom: "custom/custom",
    };
    return defaults[provider] ?? "anthropic/claude-opus-4-6";
}

export function requiresApiKey(choice: AuthChoice): boolean {
    const noKeyChoices: AuthChoice[] = [
        "openai-codex",
        "chutes",
        "minimax-portal",
        "google-antigravity",
        "google-gemini-cli",
        "github-copilot",
        "qwen-portal",
        "ollama",
        "skip",
    ];
    return !noKeyChoices.includes(choice);
}

export function getApiKeyPrompt(choice: AuthChoice): {
    message: string;
    placeholder: string;
} {
    const prompts: Partial<
        Record<AuthChoice, { message: string; placeholder: string }>
    > = {
        "openai-api-key": {
            message: "OpenAI API key",
            placeholder: "sk-...",
        },
        apiKey: {
            message: "Anthropic API key",
            placeholder: "sk-ant-...",
        },
        token: {
            message: "Anthropic setup token",
            placeholder: "Paste token from `claude setup-token`",
        },
        "moonshot-api-key": {
            message: "Kimi API key (.ai)",
            placeholder: "sk-...",
        },
        "moonshot-api-key-cn": {
            message: "Kimi API key (.cn)",
            placeholder: "sk-...",
        },
        "kimi-code-api-key": {
            message: "Kimi Code API key",
            placeholder: "sk-...",
        },
        "gemini-api-key": {
            message: "Google Gemini API key",
            placeholder: "AIza...",
        },
        "xai-api-key": {
            message: "xAI (Grok) API key",
            placeholder: "xai-...",
        },
        "openrouter-api-key": {
            message: "OpenRouter API key",
            placeholder: "sk-or-...",
        },
        "custom-api-key": {
            message: "API key for custom provider",
            placeholder: "Enter your API key",
        },
        vllm: {
            message: "vLLM server URL",
            placeholder: "http://localhost:8000",
        },
    };

    return (
        prompts[choice] ?? {
            message: "API key",
            placeholder: "Enter your API key",
        }
    );
}
