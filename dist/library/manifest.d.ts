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
export interface Specialist {
    /** Display name (e.g. "WhatsApp Mind") */
    name: string;
    /** URL-safe slug (e.g. "whatsapp") */
    slug: string;
    /** Tools this specialist can invoke */
    tools: string[];
    /** Memory scope — which vector store to read/write */
    memoryScope: string;
    /** Optional binding to a ChannelsConfig key (e.g. "whatsapp", "signal") */
    channelBinding?: string;
    /** Brief description of what this specialist does */
    description: string;
}
export interface Category {
    /** Display name (e.g. "Social") */
    name: string;
    /** URL-safe slug (e.g. "social") */
    slug: string;
    /** Icon identifier for the UI */
    icon: string;
    /** Glow color (hex) for the category folder */
    color: string;
    /** Routing keywords that trigger this category */
    routingKeywords: string[];
    /** Whether this category is dynamic (e.g. Suggestions, Recently Active) */
    dynamic: boolean;
    /** The specialist agents in this domain */
    specialists: Specialist[];
}
export interface LibraryManifest {
    version: string;
    generatedAt: string;
    theme: {
        glow: string;
        dark: boolean;
    };
    categories: Category[];
}
export declare const DEFAULT_CATEGORIES: Category[];
export declare function buildManifest(): LibraryManifest;
/**
 * Get total specialist count across all categories
 */
export declare function getSpecialistCount(): number;
/**
 * Find the category that best matches a set of keywords
 */
export declare function matchCategory(keywords: string[]): Category | undefined;
//# sourceMappingURL=manifest.d.ts.map