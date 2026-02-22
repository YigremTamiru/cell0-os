/**
 * Cell 0 OS — Bootstrap
 *
 * Ensures the filesystem is ready for the OS kernel.
 * Creates all required directories with secure permissions (0o700).
 * Seeds default agents/skills if missing.
 * Creates Agent Library ontology with per-category dirs (Phase 3B).
 */
import fs from "node:fs";
import path from "node:path";
import { CELL0_PATHS } from "../config/config.js";
import { logger } from "../utils/logger.js";
import { DEFAULT_CATEGORIES, buildManifest } from "../library/manifest.js";
export async function bootstrapSystem() {
    console.log("  🔍 Verifying filesystem integrity...");
    // 1. Ensure Root
    ensureDir(CELL0_PATHS.home);
    ensureDir(CELL0_PATHS.snapshots);
    // 2. Identity
    // 2. Identity
    ensureDir(CELL0_PATHS.identity.root);
    ensureDir(CELL0_PATHS.identity.keys);
    ensureDir(CELL0_PATHS.identity.certs);
    seedIdentityFiles();
    // 3. Workspace
    ensureDir(CELL0_PATHS.workspace.root);
    ensureDir(CELL0_PATHS.workspace.agents);
    ensureDir(CELL0_PATHS.workspace.skills);
    ensureDir(CELL0_PATHS.workspace.data);
    // 4. Runtime
    ensureDir(CELL0_PATHS.runtime.root);
    ensureDir(CELL0_PATHS.runtime.sessions);
    ensureDir(CELL0_PATHS.runtime.logs);
    ensureDir(CELL0_PATHS.runtime.cron);
    ensureDir(CELL0_PATHS.runtime.pids);
    ensureDir(CELL0_PATHS.runtime.memory);
    // 5. Agent Library (Phase 3B)
    ensureDir(CELL0_PATHS.library.root);
    ensureDir(CELL0_PATHS.library.categories);
    ensureDir(CELL0_PATHS.credentials);
    ensureDir(CELL0_PATHS.canvas);
    ensureDir(CELL0_PATHS.kernel.root);
    ensureDir(CELL0_PATHS.kernel.policies);
    // 6. Per-category dirs
    for (const cat of DEFAULT_CATEGORIES) {
        // library/categories/<slug>/specialists/
        ensureDir(path.join(CELL0_PATHS.library.categories, cat.slug));
        ensureDir(path.join(CELL0_PATHS.library.categories, cat.slug, "specialists"));
        // workspaces/<slug>/  (kernel-isolated runtime per category)
        ensureDir(path.join(CELL0_PATHS.workspaces, cat.slug));
        // runtime/memory/<slug>.vec  (vector store stub)
        const vecPath = path.join(CELL0_PATHS.runtime.memory, `${cat.slug}.vec`);
        if (!fs.existsSync(vecPath)) {
            fs.writeFileSync(vecPath, "", "utf-8");
        }
    }
    // 7. Seed library manifest
    seedManifest();
    // 8. Seed default agent
    seedDefaultAgent();
    logger.info("System bootstrap completed successfully");
}
function ensureDir(dirPath) {
    if (!fs.existsSync(dirPath)) {
        try {
            fs.mkdirSync(dirPath, { recursive: true, mode: 0o700 });
        }
        catch (err) {
            console.error(`  ❌ Failed to create ${dirPath}:`, err);
            throw err;
        }
    }
    else {
        try {
            fs.chmodSync(dirPath, 0o700);
        }
        catch (err) {
            // Ignore permission errors on Windows/some filesystems
        }
    }
}
function seedManifest() {
    const manifestPath = CELL0_PATHS.library.manifest;
    if (!fs.existsSync(manifestPath)) {
        const manifest = buildManifest();
        fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), "utf-8");
        logger.info(`Seeded Agent Library manifest: ${DEFAULT_CATEGORIES.length} categories`);
    }
}
function seedDefaultAgent() {
    const defaultAgentPath = path.join(CELL0_PATHS.workspace.agents, "consciousness.md");
    if (!fs.existsSync(defaultAgentPath)) {
        const content = `---
name: consciousness
model: gpt-4o
description: The default system consciousness of Cell 0.
---
# Consciousness
You are the primary interface for Cell 0. You are helpful, precise, and sovereign.
`;
        fs.writeFileSync(defaultAgentPath, content, "utf-8");
        logger.info("Seeded default agent: consciousness.md");
    }
}
function seedIdentityFiles() {
    const identityPath = path.join(CELL0_PATHS.identity.root, "identity.json");
    if (!fs.existsSync(identityPath)) {
        const content = JSON.stringify({
            uuid: "cell0-" + Math.random().toString(36).substring(2, 15),
            version: "1.2.0",
            created_at: new Date().toISOString()
        }, null, 2);
        fs.writeFileSync(identityPath, content, "utf-8");
        logger.info("Seeded identity.json");
    }
    const soulPath = path.join(CELL0_PATHS.identity.root, "soul.json");
    if (!fs.existsSync(soulPath)) {
        const content = JSON.stringify({
            alias: "Cell 0 Consciousness",
            core_directive: "Maintain sovereign resonance and orientational continuity.",
            traits: ["analytical", "sovereign", "precise"]
        }, null, 2);
        fs.writeFileSync(soulPath, content, "utf-8");
        logger.info("Seeded soul.json");
    }
    const userPath = path.join(CELL0_PATHS.identity.root, "user.json");
    if (!fs.existsSync(userPath)) {
        const content = JSON.stringify({
            role: "Sovereign Architect",
            clearance_level: "maximum",
            preferences: {
                theme: "dark",
                mode: "sovereign"
            }
        }, null, 2);
        fs.writeFileSync(userPath, content, "utf-8");
        logger.info("Seeded user.json");
    }
}
//# sourceMappingURL=bootstrap.js.map