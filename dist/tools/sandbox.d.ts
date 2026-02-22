/**
 * Cell 0 OS — Sandbox Execution Tool
 *
 * Wraps the Python backend's highly secure Execution Sandbox (cell0/engine/security/sandbox.py).
 * Exposes a Node.js interface for agents to execute bash/python code
 * with strict resource limits, docker isolation, or sub-processes.
 */
import { PythonBridge } from "../agents/python-bridge.js";
export interface SandboxConfig {
    timeout?: number;
    memoryLimit?: string;
    cpuLimit?: string;
    network?: boolean;
    cwd?: string;
    sandboxType?: "auto" | "subprocess" | "docker" | "restricted_python";
}
export interface SandboxResult {
    exitCode: number;
    stdout: string;
    stderr: string;
    executionTimeMs: number;
    timeout: boolean;
    error?: string;
}
export declare class SandboxTool {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Executes a command securely via the Python Sandbox engine.
     *
     * @param command The command to execute (e.g. "ls -la" or ["ls", "-la"])
     * @param config Sandbox restrictions (timeout, network config, etc)
     */
    execute(command: string | string[], config?: SandboxConfig): Promise<SandboxResult>;
}
//# sourceMappingURL=sandbox.d.ts.map