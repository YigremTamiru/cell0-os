/**
 * Cell 0 OS — Canvas UI Tool
 *
 * Wraps the Python GUI canvas server (cell0/gui/canvas_server.py)
 * Allows agents to dynamically push React/HTML components to the Nerve Portal.
 */

import { PythonBridge } from "../agents/python-bridge.js";

export interface CanvasComponent {
    id: string;
    type: "react" | "html" | "markdown" | "mermaid";
    content: string;
    props?: Record<string, unknown>;
    styles?: Record<string, string>;
    children?: CanvasComponent[];
}

export interface CanvasState {
    components: CanvasComponent[];
    theme: "dark" | "light";
    layout: string;
    lastUpdated: string;
}

export class CanvasTool {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Renders a new component or overwrites the entire canvas.
     */
    async renderComponent(component: CanvasComponent, append: boolean = false): Promise<boolean> {
        if (!this.bridge.isReady()) throw new Error("Python backend is not ready to render canvas.");

        try {
            const response = await this.bridge.post<any>("/api/tools/canvas/render", {
                component,
                append,
            });
            return response.success ?? true;
        } catch (error) {
            console.error("[CanvasTool] renderComponent failed:", error);
            return false;
        }
    }

    /**
     * Updates an existing component on the canvas by its ID.
     */
    async updateCanvas(componentId: string, partialUpdate: Partial<CanvasComponent>): Promise<boolean> {
        if (!this.bridge.isReady()) return false;

        try {
            const response = await this.bridge.post<any>("/api/tools/canvas/update", {
                componentId,
                update: partialUpdate,
            });
            return response.success ?? true;
        } catch (error) {
            console.error("[CanvasTool] updateCanvas failed:", error);
            return false;
        }
    }

    /**
     * Retrieves the current state of the GUI canvas.
     */
    async getCanvasState(): Promise<CanvasState | null> {
        if (!this.bridge.isReady()) return null;

        try {
            const response = await this.bridge.post<CanvasState>("/api/tools/canvas/state", {});
            return response;
        } catch (error) {
            console.error("[CanvasTool] getCanvasState failed:", error);
            return null;
        }
    }
}
