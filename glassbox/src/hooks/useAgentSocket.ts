import { useState, useEffect, useCallback } from 'react';

export interface AgentMessage {
    id: string;
    timestamp: number;
    source: string;
    agent: 'operator' | 'strategist' | 'toolsmith' | 'meta' | 'system';
    content: string;
    metadata?: Record<string, any>;
}

export function useAgentSocket(url: string = 'ws://localhost:18789') {
    const [messages, setMessages] = useState<AgentMessage[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [socket, setSocket] = useState<WebSocket | null>(null);

    useEffect(() => {
        const ws = new WebSocket(url);

        ws.onopen = () => {
            setIsConnected(true);
            // Send handshake exactly as expected by the Cell 0 Gateway
            ws.send(JSON.stringify({
                type: 'handshake',
                channel: 'glassbox',
                version: '1.3.6'
            }));
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'agent_thought' || data.type === 'message') {
                    setMessages((prev: AgentMessage[]) => [...prev, {
                        id: Math.random().toString(36).substring(7),
                        timestamp: Date.now(),
                        source: data.source || 'core',
                        agent: data.agent || 'system',
                        content: data.content || data.payload || '',
                        metadata: data.metadata
                    }]);
                }
            } catch (err) {
                console.error('Failed to parse socket message', err);
            }
        };

        ws.onclose = () => {
            setIsConnected(false);
        };

        setSocket(ws);

        return () => {
            ws.close();
        };
    }, [url]);

    const sendCommand = useCallback((command: string) => {
        if (socket && isConnected) {
            socket.send(JSON.stringify({
                type: 'command',
                payload: command,
                channel: 'glassbox'
            }));
        }
    }, [socket, isConnected]);

    return { messages, isConnected, sendCommand };
}
