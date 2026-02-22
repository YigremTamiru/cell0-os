/**
 * Cell 0 OS — Canvas UI Tool
 *
 * Wraps the Python GUI canvas server (cell0/gui/canvas_server.py)
 * Allows agents to dynamically push React/HTML components to the Nerve Portal.
 */
export class CanvasTool {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Renders a new component or overwrites the entire canvas.
     */
    async renderComponent(component, append = false) {
        if (!this.bridge.isReady())
            throw new Error("Python backend is not ready to render canvas.");
        try {
            const response = await this.bridge.post("/api/tools/canvas/render", {
                component,
                append,
            });
            return response.success ?? true;
        }
        catch (error) {
            console.error("[CanvasTool] renderComponent failed:", error);
            return false;
        }
    }
    /**
     * Updates an existing component on the canvas by its ID.
     */
    async updateCanvas(componentId, partialUpdate) {
        if (!this.bridge.isReady())
            return false;
        try {
            const response = await this.bridge.post("/api/tools/canvas/update", {
                componentId,
                update: partialUpdate,
            });
            return response.success ?? true;
        }
        catch (error) {
            console.error("[CanvasTool] updateCanvas failed:", error);
            return false;
        }
    }
    /**
     * Retrieves the current state of the GUI canvas.
     */
    async getCanvasState() {
        if (!this.bridge.isReady())
            return null;
        try {
            const response = await this.bridge.post("/api/tools/canvas/state", {});
            return response;
        }
        catch (error) {
            console.error("[CanvasTool] getCanvasState failed:", error);
            return null;
        }
    }
}
//# sourceMappingURL=canvas.js.map