# Cell 0 OS Demonstration Scripts

This directory contains reproducible demonstration scripts for the Cell 0 OS Community Launch.

## Quick Start

```bash
# Run the complete 5-minute demo
python examples/demo_community_launch.py

# Or run individual components
python examples/demo_col_governance.py      # COL governance deep dive
python examples/demo_multi_provider.py       # Provider failover demo
python examples/demo_agent_routing.py        # Multi-agent routing demo
```

## Demo Scripts

### Main Demo

| Script | Duration | Description |
|--------|----------|-------------|
| `demo_community_launch.py` | ~5 min | Complete demonstration of all Cell 0 OS features |

### Individual Demos

| Script | Duration | Focus Area |
|--------|----------|------------|
| `demo_col_governance.py` | ~2 min | COL governance pipeline (STOP → CLASSIFY → LOAD → APPLY → EXECUTE) |
| `demo_multi_provider.py` | ~1.5 min | Multi-provider failover with intelligent ranking |
| `demo_agent_routing.py` | ~1.5 min | Agent mesh communication and routing strategies |

## Documentation

See [`docs/DEMO_SCRIPT.md`](../docs/DEMO_SCRIPT.md) for:
- Step-by-step guide
- Expected outputs
- Troubleshooting
- Presentation tips

## Requirements

- Python 3.9+
- Cell 0 OS installed
- Terminal with ANSI color support (optional)

## Key Differentiators Demonstrated

1. **COL Governance** - Self-governing execution framework with risk classification
2. **Multi-Provider Failover** - Seamless provider switching with sub-100ms detection
3. **Agent Routing** - Intelligent task distribution across agent mesh
4. **Security Policy** - Tool policy enforcement with sandboxing
5. **Cross-Session Continuity** - Automatic state persistence via checkpoints

## Expected Metrics

| Component | Latency |
|-----------|---------|
| COL Classification | <1ms |
| Provider Failover | <100ms |
| Agent Routing | <1ms |
| Policy Enforcement | <1ms |
| Checkpoint Creation | <3ms |

## Support

- Documentation: https://cell0.os/docs
- Community: https://cell0.os/community
- GitHub: https://github.com/cell0/os

---

**The glass has melted. Welcome to Cell 0 OS.** 🌊♾️💫
