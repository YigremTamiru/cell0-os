/**
 * Cell 0 OS — Voice Infrastructure
 *
 * Wraps cell0/engine/voice/ and cell0/service/voice_gateway.py
 * Exposes push-to-talk bidirectional audio stream handling to the Node UI.
 */

import { PythonBridge } from "../agents/python-bridge.js";

export interface VoiceStreamSegment {
    audioDataId: string; // ID of the blob temporarily stored or cached
    isFinal: boolean;
    transcript?: string;
}

export class VoiceService {
    private bridge: PythonBridge;

    constructor(bridge: PythonBridge) {
        this.bridge = bridge;
    }

    /**
     * Initializes a voice session to the Python backend to prepare VAD/STT engines.
     */
    async initializeSession(sessionId: string): Promise<boolean> {
        if (!this.bridge.isReady()) return false;
        try {
            const res = await this.bridge.post<any>("/api/voice/init", { sessionId });
            return res.success ?? true;
        } catch {
            return false;
        }
    }

    /**
     * Pushes an audio chunk to the backend for streaming transcription/processing.
     * Expects Base64-encoded PCM audio.
     */
    async pushAudioChunk(sessionId: string, audioBase64: string): Promise<VoiceStreamSegment | null> {
        if (!this.bridge.isReady()) return null;
        try {
            const res = await this.bridge.post<VoiceStreamSegment>("/api/voice/process_chunk", {
                sessionId,
                chunk: audioBase64
            });
            return res;
        } catch (error) {
            console.error("[VoiceService] Failed to process audio chunk:", error);
            return null;
        }
    }

    /**
     * Requests text-to-speech synthesized audio from the Python TTS engine.
     */
    async synthesizeSpeech(text: string, voiceId?: string): Promise<string | null> {
        if (!this.bridge.isReady()) return null;
        try {
            const res = await this.bridge.post<{ audioBase64: string }>("/api/voice/synthesize", {
                text,
                voiceId
            });
            return res.audioBase64 || null;
        } catch (error) {
            console.error("[VoiceService] Failed to synthesize speech:", error);
            return null;
        }
    }
}
