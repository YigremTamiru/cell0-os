import React, { useState } from 'react';
import { Terminal, Send, TerminalSquare } from 'lucide-react';

interface Props {
    isConnected: boolean;
    onSendCommand: (cmd: string) => void;
}

export function VoidScreen({ isConnected, onSendCommand }: Props) {
    const [input, setInput] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (input.trim() && isConnected) {
            onSendCommand(input.trim());
            setInput('');
        }
    };

    return (
        <div className="glass-panel w-full flex flex-col p-8 relative overflow-hidden group">
            {/* Decorative Neural Background Elements */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500 rounded-full mix-blend-screen filter blur-[100px] opacity-10 group-hover:opacity-20 transition-opacity duration-700"></div>
            <div className="absolute bottom-0 left-0 w-64 h-64 bg-purple-500 rounded-full mix-blend-screen filter blur-[100px] opacity-10 group-hover:opacity-20 transition-opacity duration-700"></div>

            <div className="flex items-center justify-between z-10 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-white tracking-widest uppercase flex items-center gap-3">
                        <TerminalSquare className="w-8 h-8 text-blue-400" />
                        Neural Glassbox
                    </h1>
                    <p className="text-sm font-mono text-blue-300 mt-2 opacity-80 uppercase tracking-widest">
                        Cognitive Interfacing Protocol v1.3.6
                    </p>
                </div>

                {/* Connection Status Indicator */}
                <div className="flex items-center gap-3 px-4 py-2 rounded-full border border-[rgba(255,255,255,0.05)] bg-[rgba(0,0,0,0.5)]">
                    <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></div>
                    <span className="text-xs font-mono font-semibold tracking-wider text-gray-300">
                        {isConnected ? 'NODE GATEWAY ONLINE (18789)' : 'OFFLINE'}
                    </span>
                </div>
            </div>

            <div className="flex-1 z-10 flex flex-col justify-end">
                <div className="mb-8">
                    <h3 className="text-lg text-white font-medium mb-3">System Ready</h3>
                    <p className="text-gray-400 font-mono text-sm max-w-2xl leading-relaxed">
                        The Cell 0 Architecture is standing by. All nodes are connected. You may route tasks via the input terminal below. The Swarm Coordinator will automatically assign agents.
                    </p>
                </div>

                {/* Input Terminal */}
                <form onSubmit={handleSubmit} className="relative group/form">
                    <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 to-purple-500 rounded-xl blur opacity-20 group-hover/form:opacity-40 transition duration-1000 group-hover/form:duration-200"></div>
                    <div className="relative flex items-center bg-[rgba(15,20,35,0.9)] rounded-xl border border-[rgba(255,255,255,0.1)] p-2">
                        <div className="pl-4 pr-3 text-blue-400">
                            <Terminal className="w-5 h-5" />
                        </div>
                        <input
                            type="text"
                            value={input}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setInput(e.target.value)}
                            placeholder="Initialize objective..."
                            className="flex-1 bg-transparent border-none outline-none text-white font-mono text-sm placeholder-gray-500 px-2 py-3"
                            disabled={!isConnected}
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || !isConnected}
                            className="px-6 py-3 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-mono text-sm tracking-wider uppercase transition-colors flex items-center gap-2"
                        >
                            Execute <Send className="w-4 h-4" />
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
