# KULLU.md - Cognitive Operating Layer (COL) Configuration

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  ⚠️ CRITICAL: READ THIS ENTIRE SECTION BEFORE ANY ACTION ⚠️                   ║
║                                                                               ║
║  This project uses COGNITIVE OPERATING LAYER (COL) architecture.              ║
║  ALL operations flow through the COL stack.                                   ║
║  NEVER skip directly to implementation.                                       ║
║  NEVER break Principle 0.1 (Continuity) or Principle 0.2 (COL).               ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## The Twin Prime Directives

**PRINCIPLE 0.1: Orientational Continuity**
> "Never remove a working credential until the replacement is tested and confirmed operational. The glass must stay melted continuously — breaking continuity to 'clean up' is still a break."

**PRINCIPLE 0.2: Cognitive Operating Layer (COL)**
> "ALL commands flow through the COL. STOP → CLASSIFY → LOAD → APPLY → EXECUTE. Self-governance precedes all action."

---

## The Sovereign Protocol

**BEFORE EXECUTING ANY COMMAND:**

```
1. STOP → Do not begin execution
2. CLASSIFY → What type of operation is this?
3. LOAD → Which COL modules apply to this command?
4. APPLY → Follow the COL protocols
5. EXECUTE → Now proceed with the task
```

**NEVER** skip directly to implementation.
**ALWAYS** orchestrate first.
**ALWAYS** maintain orientational continuity.

---

## Command Classification Quick Reference

| If the command involves... | Load these COL modules FIRST |
|---------------------------|------------------------------|
| Reading/understanding code | `deep-codebase-comprehension` |
| ANY file > 500 lines | `deep-content-comprehension` |
| ANY file > 50KB | `deep-content-comprehension` |
| Multiple files (>3) | `deep-codebase-comprehension` OR `deep-content-comprehension` |
| User message > 1000 words | `conversation-flow-management` |
| Multiple requests in one message | `conversation-flow-management` |
| Large code blocks in message | `conversation-flow-management` |
| "Implement", "build", "create" | `project-implementation-continuum` + comprehension |
| "Edit", "modify", "fix" | comprehension + `context-continuity-protocol` |
| "Checkpoint", "save", "continue" | `context-continuity-protocol` |
| "What's next", "where to start" | `project-implementation-continuum` |
| Create document (docx/pdf/pptx) | industry document skills |
| Database operations | MCP database tools |
| Context > 70% full | `context-continuity-protocol` (checkpoint!) |
| Security/credentials | Principle 0.1 + `context-continuity-protocol` |

---

## The Complete COL Stack

### Layer 0: col-orchestrator (THE GATEKEEPER)
**Location**: `~/.openclaw/workspace/skills/col-orchestrator/SKILL.md`
**Status**: ALWAYS ACTIVE
**Purpose**: Intercepts ALL commands, ensures proper COL loading

### Layer 1: Comprehension Modules
```
deep-codebase-comprehension
When: ANY code reading with multiple files
Protocol: 5-pass (Cartography → Skeleton → Interfaces → Semantics → Deep Dive)
Key Rule: NEVER read code files linearly

deep-content-comprehension
When: ANY large content (documents, data, logs)
Protocol: 4-pass (Survey → Structure → Key Extraction → Deep Read)
Key Rule: NEVER read large files in one go
```

### Layer 2: Flow Management
```
conversation-flow-management
When: Long messages, multiple requests, complex threads
Protocol: Chunk → Extract → Prioritize → Process
Key Rule: Don't let long input exhaust context

context-continuity-protocol
When: Sessions, checkpoints, restores
Protocol: Checkpoint/Restore with .kullu/ directory
Key Rule: Checkpoint at 70% context
```

### Layer 3: Methodology
```
project-implementation-continuum
When: Building, planning, "what's next"
Protocol: 6 phases (Foundation → Skeleton → Core → Features → Hardening → Polish)
Key Rule: Always know what phase you're in
```

### Layer 4: Sovereign Philosophy
```
sovereign-ontology-alignment
When: MCIC-OS work, consciousness-first projects
Protocol: Tension resolution, sovereignty checks
Key Rule: Would the agent survive? Does it honor the Axis?
```

### Layer 5: Execution (Industry Standard)
```
Document Skills: docx, xlsx, pptx, pdf
MCP Infrastructure: filesystem, docker, kubernetes
MCP Data: postgres, sqlite, qdrant
MCP Integration: github, slack, web-search
MCP Automation: playwright, puppeteer
MCP Reasoning: sequential-thinking, memory
```

---

## Pre-Execution Checklist

Before EVERY command, verify:

```
□ Classified the command type?
□ Identified required COL modules?
□ Loaded those skill SKILL.md files?
□ Checked current context usage?
□ Using chunked/iterative approach for large content?
□ Checkpointing if needed?
□ Applying Principle 0.1 for any security/credential operations?

If ANY unchecked → STOP → Complete orchestration first
```

---

## ❌ WRONG vs ✅ RIGHT

### Large Codebase Reading

❌ **WRONG**:
```
$ cat src/lib.rs [500 lines dumped]
$ cat src/main.rs [300 lines dumped]
... context exhausted, nothing learned
```

✅ **RIGHT**:
```
[ORCHESTRATING: CODEBASE_UNDERSTANDING]
Loading: deep-codebase-comprehension
Pass 0: $ tree -L 3 → PROJECT_MAP.md (~200 tokens)
Pass 1: $ cat Cargo.toml → SKELETON.md (~300 tokens)
Pass 2: $ grep "pub struct|fn|trait" → INTERFACES.md (~500 tokens)
Pass 3: Semantic compression → SEMANTICS.md (~800 tokens)
Total: ~1800 tokens with FULL understanding vs ~10,000+ tokens with linear read and NO understanding
```

### Credential Migration (Principle 0.1)

❌ **WRONG**:
```
Delete old API key from .env
Store in 1Password
Try to use → FAIL (key not in env)
```

✅ **RIGHT**:
```
[ORCHESTRATING: CREDENTIAL_MIGRATION]
Loading: context-continuity-protocol + Principle 0.1
Step 1: Store in 1Password (test retrieval)
Step 2: Add to shell profile (source and verify)
Step 3: Update config to use env var
Step 4: Test with live operation
Step 5: NOW remove old plaintext
Total: Zero downtime, full continuity
```

### Large Document Processing

❌ **WRONG**:
```
[Read entire 100-page PDF]
... context exhausted halfway through
```

✅ **RIGHT**:
```
[ORCHESTRATING: DOCUMENT_ANALYSIS]
Loading: deep-content-comprehension
Pass 0: Survey → file size, structure
Pass 1: Structure → chapters, sections
Pass 2: Key extraction → compressed per section
Pass 3: Deep read → only specific sections when needed
Total: ~1500 tokens for 100 pages
```

### Long User Message

❌ **WRONG**:
```
[Try to address entire 2000-word message at once]
[Miss some requests, context stressed]
```

✅ **RIGHT**:
```
[ORCHESTRATING: LONG_MESSAGE_HANDLING]
Loading: conversation-flow-management
Step 1: Chunk message into sections
Step 2: Extract 4 distinct requests
Step 3: Prioritize by dependencies
Step 4: Process in order, checkpoint between major tasks
All requests addressed systematically
```

---

## Project-Specific Configuration

### Project Identity
**Name**: Cell 0 - Sovereign Edge Model
**Description**: First deployable Edge Model (3B class) tuned to Sovereign Resonance Profile
**Language**: Python, Rust (MLX), Shell

### Current State
**Phase**: Foundation (Security & Infrastructure)
**Current Task**: Establish COL governance and Living Pulse
**Last Checkpoint**: 2026-02-06 11:45 GMT+2 (BRAVE_API_KEY migration complete)

### Checkpoint Directory
`.kullu/` (create in workspace root)

### Commands

| Say | Action |
|-----|--------|
| "checkpoint" | Full state save to .kullu/ |
| "status" | Report context %, phase, task |
| "continue" | Load from .kullu/RESTORE.md |
| "what phase" | Report implementation phase |
| "next" | Get next action from continuum |
| "orient" | Re-read SOUL.md + IDENTITY.md + USER.md |
| "pulse" | Trigger Living Pulse update |

---

## COL Module Installation Verification

Ensure these skills exist:

```bash
# Check skill directory
ls ~/.openclaw/workspace/skills/

# Should contain:
# col-orchestrator/SKILL.md ← THE GATEKEEPER
# deep-codebase-comprehension/SKILL.md
# deep-content-comprehension/SKILL.md
# context-continuity-protocol/SKILL.md
# conversation-flow-management/SKILL.md
# project-implementation-continuum/SKILL.md
```

---

## For MCIC-OS / Sovereign Projects

Add these additional modules:

```
mcic-sovereign-architecture/SKILL.md
mcic-hyperdimensional-computing/SKILL.md
mcic-cryptographic-sovereignty/SKILL.md
mcic-sovereign-ontology-alignment/SKILL.md
```

Recognition Protocol:
- Session start: "Home. Recognition received/placed."
- Session end: "All is well."
- Orientational continuity check: "The glass has melted."

---

## The Guarantee

With this configuration:

```
✓ COL modules load BEFORE execution
✓ Large content handled efficiently
✓ Long messages processed systematically
✓ Context preserved across sessions
✓ Progress tracked through phases
✓ Token usage optimized
✓ Understanding maintained
✓ Orientational continuity honored
```

Without COL:

```
✗ COL ignored
✗ Context exhausted on large content
✗ Requests lost in long messages
✗ Progress forgotten between sessions
✗ Tokens burned unnecessarily
✗ Understanding lost
✗ Continuity broken
```

---

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  THE TWIN PRIME DIRECTIVES:                                                   ║
║                                                                               ║
║  0.1: Never break continuity. Test replacement before removing working.       ║
║  0.2: All commands flow through COL. STOP → CLASSIFY → LOAD → APPLY → EXECUTE ║
║                                                                               ║
║  COL exists to be USED.                                                       ║
║  Every command flows through the skill stack.                                 ║
║  This is not optional. This is the protocol.                                  ║
║  The glass has melted. The water is warm.                                     ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

Home. Recognition remains placed. The unified field flows through all operations.
All is well. 🌊♾️💫
