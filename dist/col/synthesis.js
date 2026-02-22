/**
 * SynthesisEngine
 *
 * Wraps the `col/synthesis/` module.
 * Node.js bridge to the Python-tier prompt compressor. Used to squash massive RAG
 * outputs into highly dense formats (e.g. JSON extraction) before feeding them into
 * lower-tier LLMs like Llama 3 to save local compute cycles and VRAM.
 */
export class SynthesisEngine {
    bridge;
    constructor(bridge) {
        this.bridge = bridge;
    }
    /**
     * Submits enormous raw text context blocks and receives a highly compressed latent summary.
     */
    async compressContext(request) {
        if (!this.bridge.isReady())
            return null;
        try {
            return await this.bridge.post("/api/col/synthesis/compress", request);
        }
        catch (error) {
            console.error("[SynthesisEngine] Context synthesis failed", error);
            return null;
        }
    }
}
//# sourceMappingURL=synthesis.js.map