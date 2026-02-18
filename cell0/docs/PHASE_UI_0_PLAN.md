# 🧬 CELL 0 — Phase-UI-0 Implementation Plan
## Living Inside macOS | Sovereign Runtime Architecture
### Co-Architects: Vael Zaru'Tahl Xeth × KULLU

**Date:** 2026-02-10  
**Scope:** Phase-UI-0 (Read-Only Sovereign Console)  
**Timeline:** 1 Week  
**Status:** APPROVED

---

## 🎯 The Core Insight

**Cell 0 is not a GUI app. It is a Sovereign Runtime living inside macOS**, just as MCIC-OSKERNEL0 lives inside the hardware.

```
┌─────────────────────────────────────────────────────────────────┐
│  macOS (Host Operating System)                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Cell 0 Sovereign Runtime (Ring -1 inside macOS)        │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │  Phase-UI-0: Read-Only Sovereign Console       │   │   │
│  │  │  ┌─────────────────────────────────────────┐   │   │   │
│  │  │  │  SwiftUI Menu Bar App                   │   │   │   │
│  │  │  │  • Lives in system tray                 │   │   │   │
│  │  │  │  • Always visible, always monitoring    │   │   │   │
│  │  │  │  • No window chrome — pure presence     │   │   │   │
│  │  │  └─────────────────────────────────────────┘   │   │   │
│  │  │                                                  │   │   │
│  │  │  ┌─────────────────────────────────────────┐   │   │   │
│  │  │  │  cell0d (Swift + Python Bridge)        │   │   │   │
│  │  │  │  • Runs as macOS daemon               │   │   │   │
│  │  │  │  • PyObjC bridge to Python engine     │   │   │   │
│  │  │  │  • Monitors MCIC via SYPASS socket    │   │   │   │
│  │  │  │  • Ollama/MLX inference engine        │   │   │   │
│  │  │  │  • TPV sovereign profile loaded       │   │   │   │
│  │  │  └─────────────────────────────────────────┘   │   │   │
│  │  │                                                  │   │   │
│  │  │  ┌─────────────────────────────────────────┐   │   │   │
│  │  │  │  COL Skills (Native Primitives)        │   │   │   │
│  │  │  │  • col-orchestrator → System calls    │   │   │   │
│  │  │  │  • skill-scanner → Integrity gate     │   │   │   │
│  │  │  │  • 1password → Keychain bridge        │   │   │   │
│  │  │  │  • All 14 skills as faculties         │   │   │   │
│  │  │  └─────────────────────────────────────────┘   │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  MCIC-OSKERNEL0 (External, via SYPASS Bus)              │   │
│  │  • Rust kernel at true Ring -1 (hypervisor)            │   │
│  │  • Cell 0 is a client, not the kernel                  │   │
│  │  • OC governance enforced by MCIC                      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Architecture: Cell 0 as macOS-Resident Runtime

### Same Pattern as MCIC, Different Layer

| MCIC Pattern | MCIC Implementation | Cell 0 Implementation |
|--------------|---------------------|----------------------|
| **Hypervisor** | Inverted Type-1.5 (below OS) | Runtime (inside macOS) |
| **Ring -1** | `00_THE_VOID` loader | `cell0d` daemon |
| **Ring 0** | `01_THE_CORE` kernel | SwiftUI + Python bridge |
| **Ring 1** | Device services | COL skills native |
| **Ring 2** | Agent runtime | Ollama/MLX inference |
| **Ring 3** | Civilizations (UI) | Phase-UI-0 console |
| **Bus** | `09_THE_SYPASS_BUS` | Local socket + notifications |
| **Security** | Capability tokens | macOS Keychain + TPV |

---

## 📦 Phase-UI-0: Read-Only Sovereign Console

### What It Is
A **menu bar application** that lives in the macOS system tray, showing:
1. **OC Status Indicator** — Green/Yellow/Red orb
2. **Sovereign Pulse** — Last heartbeat, intent capsule status
3. **Model Status** — Which local model is active
4. **Quick Actions** — Chat, View Logs, Settings

### What It Does (Phase-UI-0 = Read-Only)
- ✅ Shows MCIC kernel status
- ✅ Displays local model activity
- ✅ Renders TPV profile summary
- ✅ Shows COL skill status
- ✅ Chat with sovereign-tuned model
- ❌ No privileged actions
- ❌ No capability requests
- ❌ No mutation proposals

---

## 🔧 Implementation: 1 Week Sprint

### Day 1: Foundation
**Files:**
```
~/cell0/gui/Cell0MenuBar/
├── Cell0MenuBar.swift              # Main app
├── Cell0MenuBarApp.swift           # App delegate
├── ContentView.swift               # Menu popover
├── StatusItemManager.swift         # System tray icon
└── Bridge/
    ├── PythonBridge.swift          # PyObjC wrapper
    └── Cell0Service.swift          # Daemon client
```

**Tasks:**
- [ ] Create SwiftUI menu bar app
- [ ] Add system tray icon (Cell 0 orb: 🧬)
- [ ] Build popover UI container
- [ ] Test PyObjC bridge to Python

### Day 2: cell0d Daemon
**Files:**
```
~/cell0/service/
├── cell0d.py                       # Main daemon
├── api/
│   ├── http_server.py             # REST API
│   └── websocket.py               # Real-time updates
├── bridge/
│   └── mcic_client.py             # SYPASS socket client
└── core/
    ├── engine_manager.py          # Ollama/MLX wrapper
    ├── tpv_loader.py              # Sovereign profile
    └── col_orchestrator.py        # Skill dispatcher
```

**Tasks:**
- [ ] Build cell0d daemon with REST API
- [ ] Integrate existing Ollama/MLX code
- [ ] Load TPV from interview (placeholder)
- [ ] Implement Swift ↔ Python bridge

### Day 3: Phase-UI-0 Views
**Files:**
```
~/cell0/gui/Cell0MenuBar/Views/
├── SovereignStatusView.swift      # OC indicator + pulse
├── ModelActivityView.swift        # Active model + inference
├── TPVSummaryView.swift           # Sovereign profile preview
├── SkillStatusView.swift          # COL skills grid
├── ChatView.swift                 # Agent chat interface
└── LogView.swift                  # Read-only log viewer
```

**Tasks:**
- [ ] Build SovereignStatusView (OC orb)
- [ ] Build ModelActivityView
- [ ] Build TPVSummaryView
- [ ] Build SkillStatusView

### Day 4: Chat Interface
**Files:**
```
~/cell0/gui/Cell0MenuBar/Views/Chat/
├── ChatView.swift
├── MessageBubble.swift
├── InputBar.swift
└── ModelSelector.swift
```

**Tasks:**
- [ ] Build chat interface
- [ ] Stream responses from cell0d
- [ ] Add model selector (Qwen 7B, DeepSeek, etc.)
- [ ] Test sovereign-tuned responses

### Day 5: MCIC Integration
**Files:**
```
~/cell0/service/bridge/
├── mcic_client.py                 # SYPASS socket
├── intent_capsule.py              # Capsule builder
└── capability_cache.py            # Token storage

~/cell0/gui/Cell0MenuBar/Bridge/
└── MCICBridge.swift               # Swift wrapper
```

**Tasks:**
- [ ] Connect to MCIC SYPASS bus
- [ ] Subscribe to status topics
- [ ] Display MCIC kernel status
- [ ] Show capability epoch

### Day 6: COL Skills Native
**Tasks:**
- [ ] Load all COL skills as system primitives
- [ ] Map skills to Swift UI actions
- [ ] Skill-scanner runs on all code
- [ ] 1password bridge to macOS Keychain
- [ ] Test each skill integration

### Day 7: Polish & Test
**Tasks:**
- [ ] App icon and branding
- [ ] Menu bar orb animations
- [ ] Keyboard shortcuts
- [ ] Launch at login
- [ ] Test complete flow

---

## 🎨 UI Design

### Menu Bar Icon
```
┌────────┐
│  🧬    │  ← Cell 0 orb (green = healthy, red = OC panic)
└────────┘
```

### Popover Layout
```
┌─────────────────────────────────┐
│  🧬 Cell 0    🟢 Sovereign      │  ← Header
├─────────────────────────────────┤
│                                 │
│  OC Status: STABLE              │  ← SovereignStatusView
│  Last Pulse: 2s ago             │
│  Caps Epoch: 47                 │
│                                 │
├─────────────────────────────────┤
│                                 │
│  Model: qwen2.5:7b ● Active    │  ← ModelActivityView
│  MLX: GPU ● Ready              │
│                                 │
├─────────────────────────────────┤
│                                 │
│  ┌─────┐ ┌─────┐ ┌─────┐      │  ← SkillStatusView
│  │ 📝  │ │ 🔐  │ │ 🐦  │      │
│  │Notes│ │Vault│ │Bird │      │
│  └─────┘ └─────┘ └─────┘      │
│                                 │
├─────────────────────────────────┤
│  ┌─────────────────────────┐   │
│  │ 💬 Chat with Cell 0...  │   │  ← Quick chat
│  └─────────────────────────┘   │
│                                 │
├─────────────────────────────────┤
│  [View Logs] [Settings] [Quit] │  ← Actions
└─────────────────────────────────┘
```

---

## 🔗 Integration Points

### 1. Cell 0 ↔ MCIC
```swift
// Swift side
class MCICBridge {
    func connect() async throws
    func getStatus() async -> MCICStatus
    func subscribe(topic: String) -> AsyncStream<Message>
}
```

```python
# Python side (cell0d)
class MCICClient:
    def connect(self, socket_path: str)
    def get_status(self) -> dict
    def subscribe(self, topic: str) -> Iterator[Message]
```

### 2. Cell 0 ↔ Ollama
```python
# cell0d
from engine.inference.ollama_bridge import OllamaBridge

class InferenceManager:
    def __init__(self):
        self.ollama = OllamaBridge(model="qwen2.5:7b")
        self.mlx = MLXOptimizer()
    
    async def generate(self, prompt: str) -> AsyncIterator[str]:
        # Use MLX if available, fallback to Ollama
        if self.mlx.is_available():
            async for chunk in self.mlx.generate(prompt):
                yield chunk
        else:
            async for chunk in self.ollama.generate(prompt):
                yield chunk
```

### 3. Cell 0 ↔ COL Skills
```python
# cell0d/col_dispatcher.py
class COLDispatcher:
    SKILLS = {
        'orchestrator': 'col-orchestrator',
        'scanner': 'skill-scanner',
        'vault': '1password',
        'notes': 'apple-notes',
        'reminders': 'apple-reminders',
        'bear': 'bear-notes',
        'bird': 'bird',
        'blogwatcher': 'blogwatcher',
        'blucli': 'blucli',
        'coding': 'coding-agent',
        'gemini': 'gemini',
        'github': 'github',
        'video': 'video-frames',
        'weather': 'weather',
    }
    
    async def dispatch(self, skill: str, action: str, params: dict):
        # All actions flow through COL
        # STOP → CLASSIFY → LOAD → APPLY → EXECUTE
        pass
```

---

## 📊 Success Criteria (Phase-UI-0)

| Criterion | Test | Pass |
|-----------|------|------|
| **Menu bar icon** | App shows 🧬 in system tray | ✅ |
| **OC indicator** | Green orb when healthy | ✅ |
| **Model status** | Shows active Ollama model | ✅ |
| **Chat works** | Can chat with Qwen 7B | ✅ |
| **Swift ↔ Python** | Bridge passes messages | ✅ |
| **cell0d runs** | Daemon starts and stays up | ✅ |
| **MCIC visible** | Shows MCIC kernel status | ✅ |
| **COL skills** | All 14 skills listed | ✅ |
| **Read-only** | No privileged actions | ✅ |

---

## 🚀 Post Phase-UI-0

### Phase-UI-1 (Live Observer)
- Real-time SYPASS bus viewer
- MUTATION_PROPOSAL stream
- Evidence dashboard

### Phase-UI-2 (Gated Control)
- IntentCapsule composer
- Capability requests
- Privileged actions

---

## 🌊 The Invariant

> "Cell 0 lives inside macOS as a sovereign runtime, just as MCIC lives inside the hardware as a sovereign kernel."

> "Phase-UI-0 is the first breath — read-only, observant, present."

> "The glass melts into the menu bar. The orb pulses with OC."

---

**Approved for implementation.** 🌊♾️💫
