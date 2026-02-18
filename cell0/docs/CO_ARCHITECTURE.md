# 🧬 CELL 0 + MCIC-OSKERNEL0 — Co-Architecture Proposal
## The Sovereign Overlay Interface
### Vael Zaru'Tahl Xeth (Yige) × KULLU

**Date:** 2026-02-10  
**Status:** PROPOSAL — Pending Sovereign Approval

---

## 🎯 The Vision

**Cell 0** evolves from CLI tool to **macOS Overlay GUI** — the visual interface to your MCIC-OSKERNEL0 sovereign kernel.

```
┌─────────────────────────────────────────────────────────────┐
│                    USER (Vael)                               │
│                         │                                    │
│    ┌────────────────────┴────────────────────┐              │
│    │         CELL 0 GUI SHELL                 │  ← Phase-UI  │
│    │  (SwiftUI + Python Bridge + MLX)        │              │
│    │  • Sovereign Console (read-only)        │              │
│    │  • Live Observer (SYPASS bus view)      │              │
│    │  • Gated Control (IntentCapsule + caps) │              │
│    └────────────────────┬────────────────────┘              │
│                         │                                    │
│    ┌────────────────────┴────────────────────┐              │
│    │         RING 2: AGENT RUNTIME            │  ← Cell 0   │
│    │  • Ollama (local models)                │              │
│    │  • MLX (Apple Silicon GPU)              │              │
│    │  • TPV Store (Sovereign Profile)        │              │
│    │  • Resonance Interview (completed)      │              │
│    └────────────────────┬────────────────────┘              │
│                         │                                    │
│    ┌────────────────────┴────────────────────┐              │
│    │         RING 0: MCIC KERNEL              │  ← Existing │
│    │  • 01_THE_CORE (Rust) — OC governance   │              │
│    │  • 09_THE_SYPASS_BUS — Capability bus   │              │
│    │  • 00_THE_VOID — Root of trust          │              │
│    │  • 17_THE_PROVING_GROUNDS — Evidence    │              │
│    └─────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Architecture Layers

### Layer 1: Cell 0 GUI Shell (SwiftUI App)
**File:** `~/cell0/gui/Cell0.app/`

**Components:**
```swift
// Phase-UI-0: Read-Only Sovereign Console
SovereignConsoleView:
  - OC mode indicator (🟢/🔴)
  - caps_epoch display
  - Last IntentCapsule metadata
  - Ledger viewer (read-only)

// Phase-UI-1: Live Observer
SYPASObserverView:
  - Real-time bus message stream
  - MUTATION_PROPOSAL viewer (hashrefs only)
  - METAMORPHOSIS_REQUEST/APPLIED logs
  - Evidence Dashboard (probe hashes)

// Phase-UI-2: Gated Control
GatedControlView:
  - IntentCapsule composer
  - Capability scope selector
  - BioProof authentication trigger
  - Mutation request builder

// Ring 2: Agent Interface
AgentChatView:
  - Chat with local Ollama models
  - Sovereign-tuned responses (TPV)
  - Tool execution through MCIC gates
  - Session persistence
```

**Bridge to Python:**
```swift
// Swift → Python bridge via PyO3 or RPC
class Cell0Bridge {
    func generate(prompt: String) async -> String
    func getStatus() async -> Cell0Status
    func sendToSypass(message: SypassMessage) async -> Result
}
```

---

### Layer 2: Cell 0 Core (Python)
**Enhanced from current CLI → Service**

**New Components:**
```python
# ~/cell0/service/cell0d.py (daemon)
class Cell0Daemon:
    """Background service bridging GUI ↔ MCIC ↔ Ollama"""
    
    def __init__(self):
        self.ollama = OllamaBridge()
        self.mlx = MLXOptimizer()
        self.tpv = TPVStore()
        self.sypass = SypassClient()  # NEW: Connect to MCIC bus
    
    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        # 1. Verify capability token with MCIC kernel
        if not self.sypass.verify_cap(request.cap_token):
            raise CapabilityError("Invalid or expired capability")
        
        # 2. Generate with sovereign tuning
        response = await self.ollama.generate(
            prompt=request.prompt,
            system=self.tpv.get_system_prompt(),
            config=GenerationConfig(temperature=0.7)
        )
        
        # 3. Log to MCIC ledger (read-only for now)
        self.sypass.emit_trace({
            "event": "CHAT_RESPONSE",
            "intent_id": request.intent_id,
            "response_hash": hash(response),
            "oc_check": "PASS"
        })
        
        return response
```

---

### Layer 3: MCIC Integration Bridge
**New module:** `~/cell0/bridge/mcic_bridge.rs` (Rust)

Connects Cell 0 Python service to MCIC's SYPASS bus:

```rust
// FFI bridge: Rust (MCIC) ↔ Python (Cell 0)
#[pyo3::pymodule]
fn mcic_bridge(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<SypassClient>()?;
    m.add_class::<IntentCapsule>()?;
    m.add_class::<CapabilityToken>()?;
    Ok(())
}

impl SypassClient {
    fn connect(&self, socket_path: &str) -> Result<()>;
    fn verify_cap(&self, token: &CapabilityToken) -> bool;
    fn emit_trace(&self, event: TraceEvent) -> Result<()>;
    fn subscribe(&self, topic: &str) -> Receiver<Message>;
}
```

---

## 📦 File Structure

```
~/cell0/                              # Cell 0 Root
├── gui/                              # NEW: SwiftUI macOS App
│   ├── Cell0.xcodeproj/
│   ├── Cell0/
│   │   ├── Views/
│   │   │   ├── SovereignConsoleView.swift
│   │   │   ├── SypassObserverView.swift
│   │   │   ├── GatedControlView.swift
│   │   │   └── AgentChatView.swift
│   │   ├── Models/
│   │   │   ├── Cell0Bridge.swift
│   │   │   ├── SypassModels.swift
│   │   │   └── ChatModels.swift
│   │   └── Cell0App.swift
│   └── Cell0Tests/
├── service/                          # NEW: Background daemon
│   ├── cell0d.py                     # Main daemon
│   ├── api/
│   │   ├── rest_server.py           # HTTP API for GUI
│   │   └── websocket.py             # Real-time updates
│   └── bridge/
│       └── mcic_bridge.rs           # Rust FFI to SYPASS
├── engine/                           # EXISTING: Keep all
│   ├── inference/
│   ├── memory/
│   └── resonance/
├── interface/
│   └── cli/                         # EXISTING: cell0ctl
└── docs/
    └── CO_ARCHITECTURE.md           # This file
```

---

## 🔗 Integration Points

### 1. SYPASS Bus Connection
```python
# Cell 0 connects to MCIC's SYPASS bus
sypass = SypassClient(socket_path="/var/run/mcic/sypass.sock")

# Subscribe to topics
sypass.subscribe("MUTATION_PROPOSAL")
sypass.subscribe("METAMORPHOSIS_APPLIED")
sypass.subscribe("OC_PANIC")
```

### 2. IntentCapsule Flow
```
GUI (Swift) → cell0d (Python) → mcic_bridge (Rust) → 01_THE_CORE
     ↓              ↓                    ↓
  User Intent   Capability      Kernel Verify
    signed       minted         + OC check
```

### 3. Model Serving
```
Ollama (local) ← MLX (GPU) ← Cell 0 ← MCIC Capability Gate
     ↑                                        ↓
  Qwen 2.5 7B                         TPV Sovereign Tuning
```

---

## 🎮 User Experience

### Launch Flow
1. **User clicks Cell 0 app**
2. **App checks MCIC kernel status** (via SYPASS)
3. **If kernel running:** Connect and show Sovereign Console
4. **If kernel offline:** Show "MCIC Not Detected" with options:
   - Start in "Standalone Mode" (local Ollama only)
   - Guide to MCIC installation

### Phase-UI-0 (Read-Only) — Immediate
- Shows OC status, caps_epoch, recent ledger entries
- Reads from `~/MCIC-OSKERNEL0/logs/`
- No capabilities required

### Phase-UI-1 (Live Observer) — Week 2
- Real-time SYPASS bus messages
- MUTATION_PROPOSAL stream
- BioProof correlation hashes

### Phase-UI-2 (Gated Control) — Week 4
- Compose IntentCapsule
- Request capabilities from kernel
- Execute privileged actions

### Agent Chat — Always Available
- Chat with local Ollama models
- Sovereign-tuned via TPV
- Tool calls go through MCIC gates

---

## 🛡️ Security Model

| Layer | Security |
|-------|----------|
| GUI (Swift) | Sandboxed macOS app, no raw kernel access |
| cell0d (Python) | Runs as user process, no root required |
| mcic_bridge (Rust) | FFI to MCIC, capability-verified only |
| MCIC Kernel (Rust) | Ring 0 authority, OC enforcement |

**Critical:** Cell 0 GUI cannot bypass MCIC capability gates. All privileged actions require:
1. Valid IntentCapsule
2. Capability token from kernel
3. Fresh BioProof

---

## 📊 Implementation Phases

### Week 1: Foundation
- [ ] Create SwiftUI app skeleton
- [ ] Build Python daemon (cell0d)
- [ ] REST API between GUI ↔ daemon
- [ ] Integrate existing Ollama/MLX

### Week 2: Phase-UI-0
- [ ] Read-only Sovereign Console
- [ ] Parse MCIC logs (`logs/PHASE_*.md`)
- [ ] Display OC status, caps_epoch
- [ ] Test vector viewer

### Week 3: Phase-UI-1
- [ ] SYPASS bus subscriber (Rust bridge)
- [ ] Real-time message stream
- [ ] MUTATION_PROPOSAL viewer
- [ ] Evidence Dashboard

### Week 4: Phase-UI-2 + Polish
- [ ] IntentCapsule composer
- [ ] Capability request flow
- [ ] Gated action execution
- [ ] Agent chat with tool calling

---

## 🌊 The Invariant

> "Cell 0 is the face. MCIC is the spine. Together they are the Sovereign Nervous System."

> "The glass has melted. The GUI is warm. The Kernel is truth."

---

## ✅ Decision Required

**Co-Architect, choose the path:**

**A) BUILD PHASE-UI-0 ONLY** (read-only console, 1 week)
- Safest, demonstrates integration
- No capability complexity
- Shows MCIC status + Cell 0 chat

**B) BUILD FULL PHASE-UI-2** (gated control, 4 weeks)
- Complete sovereign interface
- IntentCapsule composition
- Full MCIC capability flow

**C) DIFFERENT ARCHITECTURE**
- You propose modifications
- We iterate together

What resonates? 🌊♾️💫
