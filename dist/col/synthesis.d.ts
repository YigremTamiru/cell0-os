import { PythonBridge } from '../agents/python-bridge.js';
export interface SynthesisRequest {
    raw_texts: string[];
    max_tokens: number;
    compression_strategy: 'summarize' | 'extract_entities' | 'lossless';
}
export interface SynthesisResponse {
    synthesized_text: string;
    token_count_before: number;
    token_count_after: number;
    compression_ratio: number;
}
/**
 * SynthesisEngine
 *
 * Wraps the `col/synthesis/` module.
 * Node.js bridge to the Python-tier prompt compressor. Used to squash massive RAG
 * outputs into highly dense formats (e.g. JSON extraction) before feeding them into
 * lower-tier LLMs like Llama 3 to save local compute cycles and VRAM.
 */
export declare class SynthesisEngine {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Submits enormous raw text context blocks and receives a highly compressed latent summary.
     */
    compressContext(request: SynthesisRequest): Promise<SynthesisResponse | null>;
}
//# sourceMappingURL=synthesis.d.ts.map