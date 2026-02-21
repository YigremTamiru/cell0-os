import { useAgentSocket } from './hooks/useAgentSocket';
import { VoidScreen } from './components/VoidScreen';
import { ConsciousnessStream } from './components/ConsciousnessStream';
import { CalibrationPanel } from './components/CalibrationPanel';
import './index.css';

function App() {
  const { messages, isConnected, sendCommand } = useAgentSocket();

  return (
    <div className="w-full h-screen bg-[#030712] text-white p-6 flex flex-col relative overflow-hidden">
      {/* Dynamic Background Network Grid */}
      <div className="neural-grid"></div>

      {/* Main Glassbox Layout */}
      <div className="flex-1 grid grid-cols-12 gap-6 z-10 max-w-[1920px] mx-auto w-full">

        {/* Left Column: Input & Void Screen */}
        <div className="col-span-12 lg:col-span-3 flex flex-col h-full gap-6">
          <div className="h-2/3">
            <VoidScreen isConnected={isConnected} onSendCommand={sendCommand} />
          </div>
          <div className="h-1/3">
            <CalibrationPanel isConnected={isConnected} />
          </div>
        </div>

        {/* Right Column: Live Neural Consciousness */}
        <div className="col-span-12 lg:col-span-9 h-full">
          <ConsciousnessStream messages={messages} />
        </div>

      </div>
    </div>
  );
}

export default App;
