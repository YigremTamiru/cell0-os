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
export declare class SkillLoader {
    private bridge;
    private skillPath;
    constructor(bridge: PythonBridge);
    /**
     * Rapidly enumerates all installed skills from the user workspace.
     */
    listLocalSkills(): Promise<SkillManifest[]>;
    /**
     * Validates and loads a skill into the Python runtime engine via IPC.
     */
    syncSkillToEngine(skillId: string): Promise<boolean>;
}
//# sourceMappingURL=skill-loader.d.ts.map