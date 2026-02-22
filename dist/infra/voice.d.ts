/**
 * Cell 0 OS — Voice Infrastructure
 *
 * Wraps cell0/engine/voice/ and cell0/service/voice_gateway.py
 * Exposes push-to-talk bidirectional audio stream handling to the Node UI.
 */
import { PythonBridge } from "../agents/python-bridge.js";
export interface VoiceStreamSegment {
    audioDataId: string;
    isFinal: boolean;
    transcript?: string;
}
export declare class VoiceService {
    private bridge;
    constructor(bridge: PythonBridge);
    /**
     * Initializes a voice session to the Python backend to prepare VAD/STT engines.
     */
    initializeSession(sessionId: string): Promise<boolean>;
    /**
     * Pushes an audio chunk to the backend for streaming transcription/processing.
     * Expects Base64-encoded PCM audio.
     */
    pushAudioChunk(sessionId: string, audioBase64: string): Promise<VoiceStreamSegment | null>;
    /**
     * Requests text-to-speech synthesized audio from the Python TTS engine.
     */
    synthesizeSpeech(text: string, voiceId?: string): Promise<string | null>;
}
//# sourceMappingURL=voice.d.ts.map