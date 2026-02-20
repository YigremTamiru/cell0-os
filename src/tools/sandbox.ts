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

export class SandboxTool {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Executes a command securely via the Python Sandbox engine.
     * 
     * @param command The command to execute (e.g. "ls -la" or ["ls", "-la"])
     * @param config Sandbox restrictions (timeout, network config, etc)
     */
    async execute(
        command: string | string[],
        config: SandboxConfig = {}
    ): Promise<SandboxResult> {
        if (!this.bridge.isReady()) {
            throw new Error("Python backend is not ready to execute sandbox commands.");
        }

        const payload = {
            command: Array.isArray(command) ? command : command.split(" "),
            config: {
                timeout: config.timeout || 30,
                memory_limit: config.memoryLimit || "512m",
                cpu_limit: config.cpuLimit || "1.0",
                network: config.network !== undefined ? config.network : false,
                cwd: config.cwd || undefined,
            },
            sandbox_type: config.sandboxType || "auto",
        };

        try {
            // In architectural parity with Phase 5, we delegate this to the daemon
            const response = await this.bridge.post<any>("/api/tools/sandbox/execute", payload);

            return {
                exitCode: response.exit_code ?? -1,
                stdout: response.stdout ?? "",
                stderr: response.stderr ?? "",
                executionTimeMs: response.execution_time_ms ?? 0,
                timeout: response.timeout ?? false,
                error: response.error,
            };
        } catch (error: any) {
            console.error("[SandboxTool] Execution failed:", error);
            return {
                exitCode: -1,
                stdout: "",
                stderr: "",
                executionTimeMs: 0,
                timeout: false,
                error: error.message || "Unknown sandbox error",
            };
        }
    }
}
