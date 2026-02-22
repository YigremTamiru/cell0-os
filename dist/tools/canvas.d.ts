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
export declare class CanvasTool {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Renders a new component or overwrites the entire canvas.
     */
    renderComponent(component: CanvasComponent, append?: boolean): Promise<boolean>;
    /**
     * Updates an existing component on the canvas by its ID.
     */
    updateCanvas(componentId: string, partialUpdate: Partial<CanvasComponent>): Promise<boolean>;
    /**
     * Retrieves the current state of the GUI canvas.
     */
    getCanvasState(): Promise<CanvasState | null>;
}
//# sourceMappingURL=canvas.d.ts.map