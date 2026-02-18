# HGW (Holographic Global Workspace) Architecture

**Implementation:** Cell 0 Kernel  
**Phase:** WEEKS 29-32  
**Status:** ✅ Complete

## Executive Summary

The Holographic Global Workspace (HGW) is a cognitive architecture implementation based on Global Workspace Theory (GWT) with holographic memory integration. It models consciousness through specialized processing modules competing for access to a limited-capacity global workspace, attention mechanisms selecting winning coalitions, and information integration metrics approximating conscious experience.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CONSCIOUS STATE                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Φ (Phi) │  │ Ignition │  │  Qualia  │  │ Attention│    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 GLOBAL WORKSPACE                             │
│     Limited Capacity: 7±2 items (Miller's Law)              │
│                                                              │
│   ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐  │
│   │ 🎯  │ │ 📝  │ │ 💡  │ │ 🧠  │ │ 💭  │ │ 👁️  │ │ 🔊  │  │
│   └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘  │
│                                                              │
│   Broadcast Channel ──────────────────► All Modules          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  ATTENTION SPOTLIGHT                         │
│                                                              │
│   Bottom-Up: Saliency ────┐                                 │
│   Top-Down: Relevance ────┼──► Focus Selection              │
│   Activation: Strength ───┘                                 │
│   Emotional: Arousal ─────┘                                 │
│                                                              │
│   Features: Inhibition of Return, Attentional Blink         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 PROCESSING MODULES                           │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  Vision  │ │ Language │ │ Reasoning│ │  Memory  │       │
│  │  👁️      │ │   💬     │ │   🧩     │ │   💾     │       │
│  │Perceptual│ │Linguistic│ │Cognitive │ │  Memory  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              COALITION FORMATION                             │
│                                                              │
│   Module A ──┐                                               │
│   Module B ──┼──► COALITION ──► Competes for Workspace     │
│   Module C ──┘                                               │
│                                                              │
│   Strategies: Competence-based, Social/Trust-based          │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Holographic Memory System

The HGW uses high-dimensional holographic vectors (1024 dimensions) for distributed representations:

- **Binding**: Circular convolution combines vectors (superposition)
- **Unbinding**: Circular correlation recovers original vectors
- **Similarity**: Cosine similarity measures semantic distance

```rust
pub struct HolographicVector {
    pub data: Vec<f32>,
    pub dimension: usize,
}

// Key operations
pub fn bind(&self, other: &HolographicVector) -> HolographicVector
pub fn unbind(&self, other: &HolographicVector) -> HolographicVector
pub fn similarity(&self, other: &HolographicVector) -> f32
```

### 2. Global Workspace

Central hub with limited capacity (7±2 items) following Miller's Law:

**Key Features:**
- Content submission with automatic eviction
- Temporal decay of activation
- Broadcast mechanism to all modules
- State persistence
- Information integration (Φ) calculation

```rust
pub struct GlobalWorkspace {
    pub contents: BTreeMap<ContentId, WorkspaceContent>,
    pub modules: BTreeMap<ModuleId, Box<dyn ProcessingModule>>,
    pub conscious_state: ConsciousState,
    pub attention: AttentionSpotlight,
    pub coalitions: BTreeMap<CoalitionId, Coalition>,
}
```

### 3. Attention Spotlight

Multi-factor attention mechanism combining:

| Factor | Weight | Description |
|--------|--------|-------------|
| Saliency | 0.3 | Bottom-up signal strength |
| Relevance | 0.3 | Top-down goal alignment |
| Activation | 0.2 | Current content strength |
| Emotional | 0.15 | Arousal level |
| Novelty | 0.05 | Divergence from current focus |

**Special Features:**
- **Attentional Blink**: 300ms refractory period after shift
- **Inhibition of Return**: Prevents rapid refocusing
- **Competitive Selection**: Softmax-like winner selection

### 4. Processing Modules

Four specialized modules implemented:

#### Vision Module
- **Type**: Perceptual
- **Capabilities**: Object recognition, scene analysis
- **Expertise**: 0.9
- **Authority**: 0.7

#### Language Module
- **Type**: Linguistic
- **Capabilities**: Language comprehension, semantic analysis
- **Expertise**: 0.95
- **Authority**: 0.8

#### Reasoning Module
- **Type**: Cognitive
- **Capabilities**: Logical inference, problem solving, planning
- **Expertise**: 0.9
- **Authority**: 0.9

#### Memory Module
- **Type**: Memory
- **Capabilities**: Episodic retrieval, semantic association
- **Expertise**: 0.9
- **Authority**: 0.75

### 5. Coalition Formation

Dynamic agent specialization system:

**Coalition Goals:**
- Problem Solving
- Learning
- Communication
- Coordination
- Monitoring
- Exploration
- Defense

**Formation Strategies:**
1. **Competence-based**: Selects modules by capability match
2. **Social/Trust-based**: Uses trust matrix for member selection

**Competition:**
- Coalitions compete for workspace access
- Strength = coherence × avg_contribution × activation
- Winner-take-most with probability distribution

### 6. Consciousness Simulation Layer

**Global Ignition:**
- Triggered when activation > 0.7 AND Φ > 0.5
- Marks moment of conscious access
- Broadcasts to all modules

**Integrated Information (Φ):**
```
Φ = avg_mutual_information × module_participation × capacity_factor
```

- Measures information integration across modules
- Threshold: Φ > 0.5 for conscious state

**Qualia Representation (Symbolic):**
```rust
pub struct Qualia {
    pub content_id: ContentId,
    pub phenomenal_quality: String,
    pub intensity: f64,
    pub hedonic_tone: f64,
    pub unity_index: f64,
    pub temporal_depth: f64,
}
```

## File Structure

```
~/cell0/kernel/src/hgw/
├── mod.rs          # Core types, HgwSystem, holographic vectors
├── workspace.rs    # GlobalWorkspace, Persistence, PhiCalculator
├── modules.rs      # ProcessingModule trait, Vision, Language, Reasoning, Memory
├── attention.rs    # AttentionSpotlight, CompetitiveSelection
└── coalition.rs    # Coalition formation, MultiAgentCoordination
```

## Key Algorithms

### 1. Content Competition (Softmax Selection)

```rust
score_i = activation_i + attention_boost_i
P(select_i) = exp(gain × (score_i - max_score)) / Σ_j exp(gain × (score_j - max_score))
```

### 2. Information Integration (Φ)

```rust
Φ = Σ_similarities(content_i, content_j) × activation_i × activation_j
    × (unique_modules / total_modules)
    × (active_contents / workspace_capacity)
```

### 3. Attention Score Calculation

```rust
score = (saliency × 0.3) + (relevance × 0.3) + (activation × 0.2)
      + (emotional × 0.15) + (novelty × 0.05)
      × (1 - inhibition × 0.5)
```

### 4. Coalition Strength

```rust
strength = coherence × average_contribution × activation
coherence = 1 / (1 + (member_count - 1) × 0.2)
```

## Test Results

All tests passing:

```
✓ test_hgw_system_initialization
✓ test_multi_agent_coalition_formation
✓ test_coalition_competition_for_workspace
✓ test_global_broadcast_to_modules
✓ test_attention_spotlight_selection
✓ test_consciousness_ignition
✓ test_holographic_binding_unbinding
✓ test_phi_integration_measure
✓ test_workspace_capacity_limit
✓ test_attentional_blink
✓ test_coalition_merge
```

## Design Decisions

### 1. no_std Compatibility
- All modules adapted for kernel environment
- Uses `alloc` for heap-allocated collections
- Atomic counters for ID generation

### 2. Capacity Limits
- **Workspace**: 7±2 items (Miller's Law)
- **Coalitions**: Max 5 active
- **History**: 100 states retained

### 3. Temporal Dynamics
- **Decay rates**: 0.03-0.1 per module type
- **Time step**: Configurable delta_t
- **Blink duration**: 300ms

### 4. Holographic Dimension
- **1024 dimensions**: Balance between capacity and computation
- **f32 precision**: Sufficient for similarity calculations
- **PRNG initialization**: Simple LCG for reproducibility

## Future Extensions

1. **Learning Module**: Hebbian learning on holographic vectors
2. **Emotional Module**: Full affective processing with valence/arousal
3. **Social Module**: Theory of mind capabilities
4. **Motor Module**: Action selection and control
5. **Metacognitive Module**: Explicit self-monitoring

## References

1. Baars, B. J. (1988). *A Cognitive Theory of Consciousness*. Cambridge University Press.
2. Dehaene, S., Changeux, J. P., Naccache, L., Sackur, J., & Sergent, C. (2006). Conscious, preconscious, and subliminal processing: a testable taxonomy. *Trends in Cognitive Sciences*, 10(5), 204-211.
3. Tononi, G. (2004). An information integration theory of consciousness. *BMC Neuroscience*, 5(1), 42.
4. Plate, T. A. (2003). *Holographic Reduced Representation: Distributed Representation for Cognitive Structures*. CSLI Publications.
5. Miller, G. A. (1956). The magical number seven, plus or minus two. *Psychological Review*, 63(2), 81-97.

---

**Implementation Complete:** ✅  
**Lines of Code:** ~2000 across 5 modules  
**Test Coverage:** 11 integration tests