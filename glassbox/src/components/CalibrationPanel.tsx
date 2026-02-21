import { Activity, Server, Zap, Shield, Database } from 'lucide-react';

interface Props {
    isConnected: boolean;
}

export function CalibrationPanel({ isConnected }: Props) {
    return (
        <div className="glass-panel w-full h-full flex flex-col overflow-hidden">
            <div className="px-6 py-4 border-b border-[rgba(255,255,255,0.05)] bg-[rgba(10,15,30,0.5)]">
                <h2 className="text-lg font-medium tracking-wide flex items-center gap-2">
                    <Activity className="w-5 h-5 text-purple-400" />
                    Runtime Calibration
                </h2>
            </div>

            <div className="p-6 space-y-6 flex-1 overflow-y-auto">

                {/* Metric Grid */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-lg p-4 flex flex-col gap-2">
                        <div className="flex items-center text-xs text-gray-400 font-mono uppercase tracking-wider gap-2">
                            <Server className="w-4 h-4 text-blue-400" /> Kernel Load
                        </div>
                        <div className="text-2xl font-light text-white tracking-widest">
                            {isConnected ? '12.4%' : '--%'}
                        </div>
                    </div>

                    <div className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-lg p-4 flex flex-col gap-2">
                        <div className="flex items-center text-xs text-gray-400 font-mono uppercase tracking-wider gap-2">
                            <Zap className="w-4 h-4 text-emerald-400" /> Neural Sync
                        </div>
                        <div className="text-2xl font-light text-white tracking-widest">
                            {isConnected ? '99.9%' : '--%'}
                        </div>
                    </div>

                    <div className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-lg p-4 flex flex-col gap-2">
                        <div className="flex items-center text-xs text-gray-400 font-mono uppercase tracking-wider gap-2">
                            <Database className="w-4 h-4 text-amber-400" /> Active Vectors
                        </div>
                        <div className="text-2xl font-light text-white tracking-widest">
                            {isConnected ? '1,43MB' : '0 MB'}
                        </div>
                    </div>

                    <div className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-lg p-4 flex flex-col gap-2">
                        <div className="flex items-center text-xs text-gray-400 font-mono uppercase tracking-wider gap-2">
                            <Shield className="w-4 h-4 text-red-400" /> Policies
                        </div>
                        <div className="text-lg font-light text-white tracking-widest">
                            STRICT
                        </div>
                    </div>
                </div>

                {/* Active Specialists */}
                <div className="mt-8">
                    <h3 className="text-sm font-semibold tracking-widest text-gray-400 uppercase mb-4 border-b border-[rgba(255,255,255,0.1)] pb-2">
                        Provisioned Specialists
                    </h3>
                    <div className="space-y-3">
                        {['Orchestrator', 'Web Researcher', 'Content Synthesizer', 'Code Architect'].map(agent => (
                            <div key={agent} className="flex items-center justify-between p-3 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.03)] filter hover:brightness-125 transition-all">
                                <span className="text-sm font-medium text-gray-300">{agent}</span>
                                <span className={`text-xs px-2 py-1 rounded bg-[rgba(0,0,0,0.5)] ${isConnected ? 'text-emerald-400' : 'text-gray-500'}`}>
                                    {isConnected ? 'IDLE' : 'OFFLINE'}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>

            </div>
        </div>
    );
}
