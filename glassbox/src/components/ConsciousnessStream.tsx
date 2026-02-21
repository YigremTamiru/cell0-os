import { useRef, useEffect } from 'react';
import { AgentMessage } from '../hooks/useAgentSocket';
import { Network, Cpu, Wrench, Shield } from 'lucide-react';

interface Props {
    messages: AgentMessage[];
}

export function ConsciousnessStream({ messages }: Props) {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const getAgentIcon = (agent: string) => {
        switch (agent) {
            case 'strategist': return <Network className="w-4 h-4 text-purple-400" />;
            case 'operator': return <Cpu className="w-4 h-4 text-emerald-400" />;
            case 'toolsmith': return <Wrench className="w-4 h-4 text-amber-400" />;
            case 'meta': return <Shield className="w-4 h-4 text-red-500" />;
            default: return <Cpu className="w-4 h-4 text-blue-400" />;
        }
    };

    const getAgentColor = (agent: string) => {
        switch (agent) {
            case 'strategist': return 'var(--agent-strategist)';
            case 'operator': return 'var(--agent-operator)';
            case 'toolsmith': return 'var(--agent-toolsmith)';
            case 'meta': return 'var(--agent-meta)';
            default: return 'var(--os-text)';
        }
    };

    return (
        <div className="glass-panel w-full h-full flex flex-col overflow-hidden relative">
            <div className="px-6 py-4 border-b border-[rgba(255,255,255,0.05)] flex items-center justify-between z-10 bg-[rgba(10,15,30,0.5)]">
                <h2 className="text-lg font-medium tracking-wide flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-blue-500 animate-glow"></div>
                    Consciousness Stream
                </h2>
                <span className="text-xs text-gray-400 uppercase tracking-widest">Live Routing</span>
            </div>

            <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4 z-10 scroll-smooth">
                {messages.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-gray-500 text-sm italic">
                        Awaiting neural activity from Cell 0 Core...
                    </div>
                ) : (
                    messages.map((msg) => (
                        <div key={msg.id} className="stream-message p-4 rounded-lg bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] backdrop-blur-sm transition-all hover:bg-[rgba(255,255,255,0.04)]">
                            <div className="flex items-center gap-2 mb-2">
                                {getAgentIcon(msg.agent)}
                                <span className="text-sm font-semibold uppercase tracking-wider" style={{ color: getAgentColor(msg.agent) }}>
                                    {msg.agent}
                                </span>
                                <span className="text-xs text-gray-500 ml-auto">
                                    {new Date(msg.timestamp).toLocaleTimeString()}
                                </span>
                            </div>
                            <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap font-mono">
                                {msg.content}
                            </p>
                            {msg.metadata && msg.metadata.action && (
                                <div className="mt-3 text-xs px-2 py-1 bg-[rgba(0,0,0,0.3)] rounded text-blue-300 inline-block border border-[rgba(96,165,250,0.2)]">
                                    ⚡ {msg.metadata.action}
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
