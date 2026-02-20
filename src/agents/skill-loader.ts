import { readdir, readFile, stat } from "node:fs/promises";
import { join } from "node:path";
import { CELL0_PATHS } from "../config/config.js";
import { PythonBridge } from "./python-bridge.js";

export interface SkillManifest {
    id: string;
    name: string;
    description: string;
    version: string;
    category?: string;
    fileContent: string;
}

/**
 * SkillLoader
 * 
 * Node.js wrapper for `cell0/engine/skills/skill_loader.py`.
 * Provides fast native filesystem enumeration of `~/.cell0/workspace/skills/`
 * for the UI, while delegating actual tool invocation to the Python core via the bridge.
 */
export class SkillLoader {
    private bridge: PythonBridge;
    private skillPath: string;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
        this.skillPath = CELL0_PATHS.workspace.skills;
    }

    /**
     * Rapidly enumerates all installed skills from the user workspace.
     */
    async listLocalSkills(): Promise<SkillManifest[]> {
        const skills: SkillManifest[] = [];

        try {
            const files = await readdir(this.skillPath);

            for (const file of files) {
                if (!file.endsWith(".md") && !file.endsWith(".py") && !file.endsWith(".ts")) continue;

                const filePath = join(this.skillPath, file);
                const fileStat = await stat(filePath);

                if (fileStat.isFile()) {
                    const content = await readFile(filePath, "utf8");
                    skills.push({
                        id: file.replace(/\.(md|py|ts)$/, ''),
                        name: file,
                        description: content.substring(0, 100).trim() + "...",
                        version: "1.0.0",
                        fileContent: content
                    });
                }
            }
        } catch (error) {
            console.error(`[SkillLoader] Failed to read skills dir ${this.skillPath}:`, error);
        }

        return skills;
    }

    /**
     * Validates and loads a skill into the Python runtime engine via IPC.
     */
    async syncSkillToEngine(skillId: string): Promise<boolean> {
        if (!this.bridge.isReady()) return false;

        try {
            // Note: Currently hypothetical API endpoint mapping to the Python `skill_loader.py`
            const response = await this.bridge.post<{ success: boolean; loaded: number }>("/api/skills/sync", {
                skill_id: skillId
            });
            return response.success;
        } catch (error) {
            console.error(`[SkillLoader] Failed to sync skill ${skillId} to engine:`, error);
            return false;
        }
    }
}
