/**
 * Agent Library Manifest — Cell 0 OS
 *
 * Defines the 12 Agent Library categories and their specialist agents.
 * This is the living ontology that replaces the old "app" paradigm.
 * Each category is a sovereign domain with its own workspace, memory,
 * credential vault, and kernel isolation boundary.
 *
 * The manifest is consumed by:
 *   - src/init/bootstrap.ts  → creates ~/.cell0/library/categories/<slug>/
 *   - src/portal/portal.ts   → renders the Agent Library tab
 *   - src/gateway/router.ts  → routes messages by category (Phase 4)
 */
// ─── Default Categories ──────────────────────────────────────────────────────
export const DEFAULT_CATEGORIES = [
    // ── Suggestions (AI-curated, dynamic) ─────────────────────────────────
    {
        name: "Suggestions",
        slug: "suggestions",
        icon: "sparkles",
        color: "#FFAA00",
        routingKeywords: ["now", "today", "asap", "urgent", "important"],
        dynamic: true,
        specialists: [
            { name: "Daily Oracle", slug: "daily-oracle", tools: ["calendar-read", "weather", "news"], memoryScope: "suggestions", description: "Proactive daily briefing and priority surfacing" },
            { name: "Urgent Priority", slug: "urgent-priority", tools: ["notification", "calendar-read"], memoryScope: "suggestions", description: "Routes urgent tasks to the correct specialist" },
            { name: "Cross-Domain Weaver", slug: "cross-domain-weaver", tools: ["meta-routing"], memoryScope: "suggestions", description: "Synthesizes insights across all domains" },
            { name: "Serendipity Scout", slug: "serendipity-scout", tools: ["web-search", "recommendation"], memoryScope: "suggestions", description: "Discovers unexpected opportunities and connections" },
        ],
    },
    // ── Recently Active (dynamic) ─────────────────────────────────────────
    {
        name: "Recently Active",
        slug: "recently-active",
        icon: "clock",
        color: "#FF8800",
        routingKeywords: [],
        dynamic: true,
        specialists: [
            { name: "Last-Used Weaver", slug: "last-used-weaver", tools: ["session-restore", "context-replay"], memoryScope: "recently-active", description: "Auto-resumes context from the last active specialist" },
        ],
    },
    // ── Social ────────────────────────────────────────────────────────────
    {
        name: "Social",
        slug: "social",
        icon: "people",
        color: "#00FFAA",
        routingKeywords: ["dm", "story", "reel", "thread", "post", "reply", "mention", "chat", "message", "group"],
        dynamic: false,
        specialists: [
            { name: "WhatsApp Mind", slug: "whatsapp", tools: ["baileys", "media-ocr"], memoryScope: "social", channelBinding: "whatsapp", description: "Chat, media, status, calls, groups via WhatsApp" },
            { name: "Signal Privacy Sentinel", slug: "signal", tools: ["signal-cli", "crypto"], memoryScope: "social", channelBinding: "signal", description: "End-to-end encrypted messaging via Signal" },
            { name: "Telegram Group Nexus", slug: "telegram", tools: ["telethon", "bot-api"], memoryScope: "social", channelBinding: "telegram", description: "Group management, bots, channels via Telegram" },
            { name: "Instagram Content Oracle", slug: "instagram", tools: ["instagram-api", "image-gen"], memoryScope: "social", description: "Content creation, stories, reels, engagement" },
            { name: "X Thread Weaver", slug: "x-twitter", tools: ["twitter-api", "thread-gen"], memoryScope: "social", description: "Thread composition, engagement, trend analysis" },
            { name: "Discord Nexus", slug: "discord", tools: ["discord-js", "bot-commands"], memoryScope: "social", channelBinding: "discord", description: "Server management, bots, voice channels" },
            { name: "Facebook Keeper", slug: "facebook", tools: ["graph-api"], memoryScope: "social", description: "Page management, groups, marketplace" },
            { name: "LinkedIn Network Guardian", slug: "linkedin", tools: ["linkedin-api"], memoryScope: "social", description: "Professional networking, content, job tracking" },
            { name: "TikTok Trend Pulse", slug: "tiktok", tools: ["tiktok-api", "video-gen"], memoryScope: "social", description: "Short-form video creation and trend analysis" },
            { name: "Matrix Nexus", slug: "matrix", tools: ["matrix-sdk"], memoryScope: "social", channelBinding: "matrix", description: "Decentralized messaging via Matrix protocol" },
        ],
    },
    // ── Productivity ──────────────────────────────────────────────────────
    {
        name: "Productivity",
        slug: "productivity",
        icon: "briefcase",
        color: "#4488FF",
        routingKeywords: ["schedule", "todo", "meeting", "remind", "project", "task", "email", "note", "deadline", "calendar"],
        dynamic: false,
        specialists: [
            { name: "Calendar Sovereign", slug: "calendar", tools: ["calendar-api", "scheduling"], memoryScope: "productivity", description: "Natural-language scheduling and event management" },
            { name: "Task Oracle", slug: "tasks", tools: ["todoist", "kanban"], memoryScope: "productivity", description: "Task management, priorities, Kanban boards" },
            { name: "Email Guardian", slug: "email", tools: ["imap", "smtp", "summarize"], memoryScope: "productivity", description: "Inbox zero automation, email drafting, summarization" },
            { name: "Notes Weaver", slug: "notes", tools: ["apple-notes", "markdown"], memoryScope: "productivity", description: "Note creation, linking, and synthesis" },
            { name: "Project Nexus", slug: "project", tools: ["github", "jira", "linear"], memoryScope: "productivity", description: "Project tracking, issue management, code review" },
            { name: "Focus Keeper", slug: "focus", tools: ["pomodoro", "block-distractions"], memoryScope: "productivity", description: "Pomodoro timer, focus mode, distraction blocking" },
            { name: "Slack Guardian", slug: "slack", tools: ["slack-bolt"], memoryScope: "productivity", channelBinding: "slack", description: "Workspace messaging, channels, integrations" },
            { name: "Google Chat", slug: "google-chat", tools: ["google-chat-api"], memoryScope: "productivity", channelBinding: "googlechat", description: "Google Workspace chat and collaboration" },
            { name: "MS Teams Guardian", slug: "msteams", tools: ["teams-api"], memoryScope: "productivity", channelBinding: "msteams", description: "Microsoft Teams messaging and meetings" },
        ],
    },
    // ── Utilities ─────────────────────────────────────────────────────────
    {
        name: "Utilities",
        slug: "utilities",
        icon: "tools",
        color: "#FF4488",
        routingKeywords: ["calculate", "convert", "time", "battery", "settings", "find file", "system"],
        dynamic: false,
        specialists: [
            { name: "Calculator Oracle", slug: "calculator", tools: ["math-engine", "unit-convert"], memoryScope: "utilities", description: "Calculations, unit conversion, formulas" },
            { name: "Clock & Time Weaver", slug: "clock", tools: ["world-clock", "timer"], memoryScope: "utilities", description: "World clock, timezone sync, timers, alarms" },
            { name: "Settings Guardian", slug: "settings", tools: ["system-prefs"], memoryScope: "utilities", description: "System settings and configuration management" },
            { name: "File Finder", slug: "file-finder", tools: ["file-search", "spotlight"], memoryScope: "utilities", description: "Fast file search across devices and cloud" },
            { name: "System Monitor", slug: "system-monitor", tools: ["top", "disk-usage", "network"], memoryScope: "utilities", description: "CPU, memory, disk, network monitoring" },
            { name: "Battery Oracle", slug: "battery", tools: ["power-stats"], memoryScope: "utilities", description: "Battery health, optimization, power management" },
        ],
    },
    // ── Travel ────────────────────────────────────────────────────────────
    {
        name: "Travel",
        slug: "travel",
        icon: "airplane",
        color: "#00AAFF",
        routingKeywords: ["flight", "hotel", "book", "trip", "travel", "airport", "visa", "map", "navigate", "itinerary"],
        dynamic: false,
        specialists: [
            { name: "Flight Oracle", slug: "flight", tools: ["flight-search", "price-alert"], memoryScope: "travel", description: "Flight search, price tracking, booking assistance" },
            { name: "Hotel Nexus", slug: "hotel", tools: ["hotel-search", "reviews"], memoryScope: "travel", description: "Hotel search, comparison, and booking" },
            { name: "Map Navigator", slug: "map", tools: ["maps-api", "traffic"], memoryScope: "travel", description: "Route optimization, traffic, directions" },
            { name: "Itinerary Weaver", slug: "itinerary", tools: ["planner", "calendar-api"], memoryScope: "travel", description: "Trip planning, packing lists, document prep" },
            { name: "Currency Guardian", slug: "currency", tools: ["forex-api"], memoryScope: "travel", description: "Real-time currency conversion and alerts" },
            { name: "Visa Sentinel", slug: "visa", tools: ["visa-db", "form-fill"], memoryScope: "travel", description: "Visa requirements, document auto-fill" },
        ],
    },
    // ── Finance ───────────────────────────────────────────────────────────
    {
        name: "Finance",
        slug: "finance",
        icon: "dollar",
        color: "#FFDD00",
        routingKeywords: ["pay", "buy", "balance", "invest", "receipt", "money", "expense", "budget", "invoice", "tax", "crypto", "stock"],
        dynamic: false,
        specialists: [
            { name: "Bank Vault", slug: "bank", tools: ["plaid", "bank-api"], memoryScope: "finance", description: "Bank balance sync, transaction history" },
            { name: "Expense Tracker", slug: "expense", tools: ["receipt-ocr", "categorize"], memoryScope: "finance", description: "Receipt OCR, expense categorization, reports" },
            { name: "Market Oracle", slug: "market", tools: ["stock-api", "charts"], memoryScope: "finance", description: "Stock market data, price alerts, analysis" },
            { name: "Crypto Sentinel", slug: "crypto", tools: ["crypto-api", "wallet"], memoryScope: "finance", description: "Crypto portfolio tracking, alerts, DeFi" },
            { name: "Invoice Weaver", slug: "invoice", tools: ["invoice-gen", "pdf"], memoryScope: "finance", description: "Invoice generation, tracking, payment reminders" },
            { name: "Tax Guardian", slug: "tax", tools: ["tax-calc", "form-fill"], memoryScope: "finance", description: "Tax estimation, form auto-fill, deductions" },
            { name: "Budget Oracle", slug: "budget", tools: ["budget-planner"], memoryScope: "finance", description: "Budget creation, tracking, financial goals" },
        ],
    },
    // ── Creativity ────────────────────────────────────────────────────────
    {
        name: "Creativity",
        slug: "creativity",
        icon: "palette",
        color: "#AA00FF",
        routingKeywords: ["generate image", "edit video", "write story", "make music", "design", "create", "draw", "compose", "paint"],
        dynamic: false,
        specialists: [
            { name: "Image Muse", slug: "image", tools: ["image-gen", "image-edit"], memoryScope: "creativity", description: "AI image generation, editing, style transfer" },
            { name: "Video Editor", slug: "video", tools: ["video-edit", "ffmpeg"], memoryScope: "creativity", description: "Video editing, timeline, effects, export" },
            { name: "Music Composer", slug: "music", tools: ["music-gen", "midi"], memoryScope: "creativity", description: "Melody generation, arrangement, mixing" },
            { name: "Writing Sovereign", slug: "writing", tools: ["long-form", "grammar"], memoryScope: "creativity", description: "Long-form writing, editing, style adaptation" },
            { name: "Design Nexus", slug: "design", tools: ["canvas", "figma-api"], memoryScope: "creativity", description: "UI/UX design, prototyping, asset creation" },
            { name: "3D Modeler", slug: "3d-modeler", tools: ["blender-api", "mesh"], memoryScope: "creativity", description: "3D modeling, rendering, animation" },
        ],
    },
    // ── Information & Reading ─────────────────────────────────────────────
    {
        name: "Information & Reading",
        slug: "information-reading",
        icon: "book",
        color: "#44FFAA",
        routingKeywords: ["search", "summarize", "explain", "what is", "research", "read", "article", "pdf", "wikipedia"],
        dynamic: false,
        specialists: [
            { name: "Search Oracle", slug: "search", tools: ["web-search", "vector-search"], memoryScope: "information-reading", description: "Deep web + local vector search" },
            { name: "Wikipedia Weaver", slug: "wikipedia", tools: ["wikipedia-api"], memoryScope: "information-reading", description: "Wikipedia lookup, cross-referencing" },
            { name: "PDF Analyst", slug: "pdf", tools: ["pdf-extract", "table-parse"], memoryScope: "information-reading", description: "PDF text/table extraction and analysis" },
            { name: "Book Summarizer", slug: "book", tools: ["summarize", "chunk"], memoryScope: "information-reading", description: "Book and article summarization" },
            { name: "News Pulse", slug: "news", tools: ["rss", "news-api"], memoryScope: "information-reading", description: "Real-time news aggregation and analysis" },
            { name: "Research Nexus", slug: "research", tools: ["scholar", "arxiv"], memoryScope: "information-reading", description: "Academic paper search and synthesis" },
        ],
    },
    // ── Entertainment ─────────────────────────────────────────────────────
    {
        name: "Entertainment",
        slug: "entertainment",
        icon: "play",
        color: "#FF44AA",
        routingKeywords: ["play", "watch", "listen", "game", "meme", "movie", "show", "music", "stream", "youtube"],
        dynamic: false,
        specialists: [
            { name: "YouTube Oracle", slug: "youtube", tools: ["youtube-api", "transcript"], memoryScope: "entertainment", description: "Video search, transcripts, recommendations" },
            { name: "Netflix Guardian", slug: "netflix", tools: ["streaming-api"], memoryScope: "entertainment", description: "Streaming recommendations, watchlists" },
            { name: "Music Stream Weaver", slug: "music-stream", tools: ["spotify-api", "playlist"], memoryScope: "entertainment", description: "Playlist generation, music discovery" },
            { name: "Gaming Nexus", slug: "gaming", tools: ["game-tracker"], memoryScope: "entertainment", description: "Game tracking, stats, recommendations" },
            { name: "Meme Generator", slug: "meme", tools: ["image-gen", "meme-template"], memoryScope: "entertainment", description: "Meme creation and template library" },
            { name: "Story Teller", slug: "story", tools: ["narrative-gen"], memoryScope: "entertainment", description: "Interactive storytelling, fiction generation" },
        ],
    },
    // ── Other ─────────────────────────────────────────────────────────────
    {
        name: "Other",
        slug: "other",
        icon: "dots",
        color: "#888888",
        routingKeywords: [],
        dynamic: true,
        specialists: [
            { name: "Catch-All Weaver", slug: "catch-all", tools: ["general"], memoryScope: "other", description: "Handles unrecognized intents, spawns new specialists" },
            { name: "Legacy App Bridge", slug: "legacy-bridge", tools: ["app-launcher"], memoryScope: "other", description: "Bridges to traditional applications" },
            { name: "Custom Domain Spawner", slug: "custom-spawner", tools: ["specialist-factory"], memoryScope: "other", description: "On-demand specialist creation for new domains" },
        ],
    },
    // ── Hidden ────────────────────────────────────────────────────────────
    {
        name: "Hidden",
        slug: "hidden",
        icon: "lock",
        color: "#222222",
        routingKeywords: [],
        dynamic: false,
        specialists: [
            { name: "Privacy Vault", slug: "privacy-vault", tools: ["encryption", "secure-store"], memoryScope: "hidden", description: "Encrypted storage, secret projects" },
            { name: "Kernel Debug", slug: "kernel-debug", tools: ["bpftool", "strace"], memoryScope: "hidden", description: "Kernel debugging, eBPF inspection, system diagnostics" },
        ],
    },
];
// ─── Manifest Builder ────────────────────────────────────────────────────────
export function buildManifest() {
    return {
        version: "2026.2.19",
        generatedAt: new Date().toISOString(),
        theme: { glow: "#FF7700", dark: true },
        categories: DEFAULT_CATEGORIES,
    };
}
/**
 * Get total specialist count across all categories
 */
export function getSpecialistCount() {
    return DEFAULT_CATEGORIES.reduce((sum, cat) => sum + cat.specialists.length, 0);
}
/**
 * Find the category that best matches a set of keywords
 */
export function matchCategory(keywords) {
    const lower = keywords.map(k => k.toLowerCase());
    let bestMatch;
    let bestScore = 0;
    for (const cat of DEFAULT_CATEGORIES) {
        if (cat.dynamic && cat.routingKeywords.length === 0)
            continue;
        const score = cat.routingKeywords.filter(rk => lower.some(k => k.includes(rk) || rk.includes(k))).length;
        if (score > bestScore) {
            bestScore = score;
            bestMatch = cat;
        }
    }
    return bestMatch;
}
//# sourceMappingURL=manifest.js.map