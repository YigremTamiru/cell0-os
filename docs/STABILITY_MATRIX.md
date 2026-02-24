# Cell 0 OS Stability Matrix

> **Component stability classifications for safe adoption — v1.3.0**

This matrix categorizes Cell 0 OS components by stability level, helping contributors and users understand what's safe to use vs. what's experimental.

## Stability Levels

| Level | Icon | Description | Recommendation |
|-------|------|-------------|----------------|
| **Stable** | 🟢 | Production-tested, API-stable | Safe for production |
| **Beta** | 🟡 | Feature-complete, testing phase | Use with caution |
| **Experimental** | 🟠 | Active development, may change | Development only |
| **Deprecated** | ⚪ | Planned removal | Migrate away |

## Component Matrix

### Core Components

| Component | Status | Since | Notes |
|-----------|--------|-------|-------|
| COL Engine | 🟢 Stable | v1.0.0 | Core classification loop |
| Agent Lifecycle | 🟢 Stable | v1.0.0 | Spawn, heartbeat, terminate |
| Skill Registry | 🟢 Stable | v1.1.0 | Plugin system |
| Memory System | 🟡 Beta | v1.2.0 | Daily notes stable, long-term in beta |
| Gateway | 🟢 Stable | v1.0.0 | HTTP/WebSocket gateway; port auto-selection (default :18789), session persistence added in v1.3.0 |
| Channel Router | 🟢 Stable | v1.3.0 | All 10 channels fully implemented; `cell0 channels` CLI |

### Skills

| Skill | Status | Since | Notes |
|-------|--------|-------|-------|
| read | 🟢 Stable | v1.0.0 | File reading |
| write | 🟢 Stable | v1.0.0 | File writing |
| edit | 🟢 Stable | v1.0.0 | Surgical edits |
| exec | 🟢 Stable | v1.0.0 | Shell execution |
| web_search | 🟡 Beta | v1.2.0 | Brave API integration |
| web_fetch | 🟡 Beta | v1.2.0 | Content extraction |
| browser | 🟠 Experimental | v1.3.0 | Playwright automation |
| canvas | 🟠 Experimental | v1.3.0 | UI rendering |
| tts | 🟡 Beta | v1.2.0 | Text-to-speech |
| message | 🟡 Beta | v1.2.0 | Channel messaging |
| nodes | 🟠 Experimental | v1.3.0 | Device pairing |
| process | 🟡 Beta | v1.2.0 | Background process management |

### COL Operations

| Operation | Status | Since | Notes |
|-----------|--------|-------|-------|
| STOP | 🟢 Stable | v1.0.0 | Emergency halt |
| CLASSIFY | 🟢 Stable | v1.0.0 | Intent classification |
| LOAD | 🟢 Stable | v1.0.0 | Context loading |
| APPLY | 🟢 Stable | v1.0.0 | Command application |
| EXECUTE | 🟢 Stable | v1.0.0 | Execution phase |
| PARALLEL | 🟡 Beta | v1.2.0 | Parallel execution |
| REASONING | 🟠 Experimental | v1.3.0 | Extended thinking mode |

### Memory Features

| Feature | Status | Since | Notes |
|---------|--------|-------|-------|
| Daily Notes | 🟢 Stable | v1.0.0 | Auto-dated memory files |
| MEMORY.md | 🟡 Beta | v1.1.0 | Long-term memory curation |
| Memory Search | 🟠 Experimental | v1.3.0 | Vector-based retrieval |
| Cross-Session Recall | 🟡 Beta | v1.2.0 | Persistent agent memory |

### Security Features

| Feature | Status | Since | Notes |
|---------|--------|-------|-------|
| Policy Enforcement | 🟢 Stable | v1.0.0 | Command validation |
| Credential Isolation | 🟢 Stable | v1.0.0 | 1Password integration |
| Sub-Agent Sandbox | 🟢 Stable | v1.1.0 | Docker isolation |
| Skill Scanner | 🟡 Beta | v1.2.0 | Pre-install validation |
| Audit Logging | 🟢 Stable | v1.3.0 | Operation logging; JSONL ethics audit via EthicsConsensus |

### Meta-Agent (v1.3.0)

| Component | Status | Since | Notes |
|-----------|--------|-------|-------|
| SelfImprovementEngine | 🟡 Beta | v1.3.0 | 5-min OBSERVE→REFLECT→GOAL-SET→ACT→EVALUATE loop |
| GoalManager | 🟡 Beta | v1.3.0 | 17 domains, JSON persistence |
| EthicsConsensus | 🟡 Beta | v1.3.0 | 6 rules, JSONL audit log |

### Integrations

| Integration | Status | Since | Notes |
|-------------|--------|-------|-------|
| OpenAI | 🟢 Stable | v1.0.0 | GPT models |
| Anthropic | 🟢 Stable | v1.0.0 | Claude models |
| Moonshot | 🟢 Stable | v1.1.0 | Kimi models |
| 1Password | 🟢 Stable | v1.0.0 | Credential management |
| Telegram | 🟢 Stable | v1.3.0 | Native fetch, Bot API |
| Discord | 🟢 Stable | v1.3.0 | WebSocket Gateway v10 |
| Slack | 🟢 Stable | v1.3.0 | Socket Mode |
| WhatsApp | 🟢 Stable | v1.3.0 | Baileys Web QR, fully implemented |
| Signal | 🟢 Stable | v1.3.0 | signal-cli bridge |
| Matrix | 🟢 Stable | v1.3.0 | Client-Server API |
| Google Chat | 🟢 Stable | v1.3.0 | Webhook |
| MS Teams | 🟢 Stable | v1.3.0 | Webhook |
| BlueBubbles/iMessage | 🟢 Stable | v1.3.0 | Local REST + WebSocket |
| WebChat | 🟢 Stable | v1.3.0 | Browser-native, Nerve Portal |
| Chrome Extension | 🟠 Experimental | v1.3.0 | Browser relay |

## Stability Transition Process

```
Experimental → Beta → Stable → Deprecated
     ↑                          ↓
   New feature               Removal
```

### Criteria for Promotion

**Experimental → Beta:**
- [ ] Feature complete
- [ ] Basic tests passing
- [ ] Documentation exists
- [ ] No critical bugs for 2 weeks

**Beta → Stable:**
- [ ] 95%+ test coverage
- [ ] Production usage for 30 days
- [ ] Performance benchmarks meet targets
- [ ] API documentation complete
- [ ] Migration guide (if breaking changes)

**Stable → Deprecated:**
- [ ] Replacement feature available
- [ ] Deprecation notice for 2 releases
- [ ] Migration path documented

## Using This Matrix

### For Contributors

- **Start with Stable** components to learn the codebase
- **Experimental** areas need the most help
- Check status before submitting PRs

### For Users

- **Production deployments:** Use only 🟢 Stable
- **Development/Testing:** 🟡 Beta acceptable
- **Research/Exploration:** 🟠 Experimental available

### For Enterprise

Stable components come with:
- Semver guarantees
- Security patches
- Performance SLAs
- Support commitment

## Current Development Focus

**v1.3.0 (completed):**
- All 10 channel adapters fully implemented — CI passing, all green
- Meta-Agent subsystem added: SelfImprovementEngine, GoalManager (17 domains), EthicsConsensus (6 rules)
- Gateway: port auto-selection and session persistence
- `cell0 channels` CLI command shipped
- QR pairing utility (`src/channels/setup/qr.ts`) for WhatsApp and future QR-based channels

**Q1 2026:**
- Promoting Memory System to Stable
- Browser skill → Beta
- Canvas API → Beta
- Meta-Agent (GoalManager, EthicsConsensus, SelfImprovementEngine) → Stable

**Q2 2026:**
- Reasoning mode → Beta
- Memory Search → Beta
- Chrome Extension → Beta

**Q3 2026:**
- All Beta features → Stable (target)
- New experimental: Multi-agent coordination

## Version Compatibility

| Cell 0 Version | Stable API | Beta API | Experimental |
|----------------|------------|----------|--------------|
| v1.0.x | ✅ Full | ⚠️ May change | 🔥 Active dev |
| v1.1.x | ✅ Full | ⚠️ May change | 🔥 Active dev |
| v1.2.x | ✅ Full | ⚠️ Minor changes | 🔥 Active dev |
| v1.3.x | ✅ Full | ✅ Stable soon | ⚠️ Stabilizing |

## Reporting Issues

| Component Level | Issue Priority | Response Target |
|-----------------|----------------|-----------------|
| 🟢 Stable | High | 24 hours |
| 🟡 Beta | Medium | 72 hours |
| 🟠 Experimental | Low | Best effort |

## See Also

- [Benchmarks](./BENCHMARKS.md) - Performance data
- [Architecture](../docs/ARCHITECTURE.md) - System design
- [Contributing](archive/CONTRIBUTOR_MAP.md) - How to help
