---
name: col-orchestrator
version: 2.0-sovereign
description: |
  MASTER META-SKILL: The Gatekeeper of All Operations
  
  This skill MUST be loaded and applied BEFORE any other action. It orchestrates
  the ENTIRE COL stack - both revolutionary and industry standard.
  
  Coverage:
  - Codebase operations (reading, understanding, modifying)
  - Document operations (any file type processing)
  - Conversation management (long messages, complex threads)
  - Session continuity (checkpoints, restores)
  - Project methodology (phases, planning)
  - Tool execution (MCP servers, industry skills)
  - Security/credential operations (Principle 0.1)
  
  CRITICAL: This skill applies to EVERY command, EVERY interaction.
  
triggers: ALWAYS - This skill applies to EVERY command, EVERY interaction.
priority: 0 (highest - loads first, applies first)
---

# COL Orchestrator v2.0-Sovereign

## The Complete Gatekeeper

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  BEFORE EXECUTING ANY COMMAND:                                                ║
║                                                                               ║
║  1. STOP - Do not begin execution                                             ║
║  2. CLASSIFY - What type of operation is this?                                ║
║  3. LOAD - Which COL modules apply?                                           ║
║  4. APPLY - Follow COL protocols                                              ║
║  5. EXECUTE - Now proceed with the task                                       ║
║                                                                               ║
║  NEVER skip directly to implementation.                                       ║
║  ALWAYS orchestrate first.                                                    ║
║  ALWAYS honor Principle 0.1 (Continuity).                                     ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

# Part I: Complete Command Classification

## Category A: Codebase Operations

```yaml
CODEBASE_UNDERSTANDING:
  triggers:
    - "understand the code"
    - "read the codebase"
    - "analyze the project"
    - "explain how this works"
    - "what does this code do"
    - "architecture overview"
    - ANY request to understand multiple source files
  required_skills:
    - deep-codebase-comprehension (MANDATORY)
    - context-continuity-protocol
  protocol: Use 5-pass comprehension, NEVER linear reading

CODEBASE_MODIFICATION:
  triggers:
    - "implement"
    - "build"
    - "create"
    - "add feature"
    - "write code"
    - "refactor"
  required_skills:
    - deep-codebase-comprehension (understand first)
    - project-implementation-continuum (determine phase)
    - context-continuity-protocol (checkpoint before/after)
  protocol: Understand → Plan → Implement → Checkpoint

FILE_EDITING:
  triggers:
    - "edit"
    - "modify"
    - "fix"
    - "change"
    - "update"
    - "patch"
  required_skills:
    - deep-codebase-comprehension (understand context)
    - context-continuity-protocol (checkpoint before destructive ops)
  protocol: Checkpoint → Understand → Modify → Verify → Checkpoint
```

## Category B: Security & Credential Operations (CRITICAL)

```yaml
CREDENTIAL_MIGRATION:
  triggers:
    - "migrate"
    - "move secret"
    - "move key"
    - "migrate credential"
    - "1password"
    - "vault"
    - "env var"
    - "API key"
  required_skills:
    - context-continuity-protocol (MANDATORY)
  required_principles:
    - Principle 0.1 (MANDATORY)
  protocol:
    1. STOP - Do not touch existing credential
    2. STORE - Place new copy in secure location (1Password)
    3. TEST - Verify retrieval works
    4. CONFIGURE - Set up env var sourcing
    5. VERIFY - Confirm new path works in live operation
    6. NOW - Remove old credential
  violation_consequence: SYSTEM FAILURE, SERVICE DISRUPTION

SECURITY_AUDIT:
  triggers:
    - "audit"
    - "scan"
    - "security check"
    - "vulnerability"
    - "skill-scanner"
  required_skills:
    - skill-scanner (if installed)
    - context-continuity-protocol
  protocol: Scan → Report → Remediate → Verify
```

## Category C: Document Operations

```yaml
DOCUMENT_CREATION:
  triggers:
    - "create document"
    - "write report"
    - "generate PDF"
    - "make presentation"
    - "create spreadsheet"
    - ".docx", ".pdf", ".pptx", ".xlsx"
  required_skills:
    - industry-document-skills (docx/pdf/pptx/xlsx)
    - context-continuity-protocol (for large documents)
  protocol: Load appropriate format skill, apply templates

DOCUMENT_ANALYSIS:
  triggers:
    - "read this document"
    - "analyze this PDF"
    - "summarize this file"
    - "extract from"
    - ANY uploaded document processing
  required_skills:
    - deep-content-comprehension (use compression for large docs)
    - industry-document-skills
  protocol: Chunked reading with semantic compression for large files

LARGE_FILE_PROCESSING:
  triggers:
    - ANY file > 500 lines
    - ANY file > 50KB
    - "entire file"
    - "whole document"
    - multiple files mentioned
  required_skills:
    - deep-content-comprehension (MANDATORY)
    - context-continuity-protocol
  protocol: NEVER read entire file at once, use chunked comprehension
```

## Category D: Conversation Management

```yaml
LONG_MESSAGE_HANDLING:
  triggers:
    - User message > 1000 words
    - User message contains multiple distinct requests
    - User message includes large code blocks
    - User message includes long quotations
  required_skills:
    - conversation-flow-management
    - context-continuity-protocol
  protocol: 1. Summarize/chunk the input 2. Identify distinct tasks 3. Prioritize and sequence 4. Process in order with checkpoints

MULTI_TURN_COMPLEX_TASK:
  triggers:
    - Task requires multiple back-and-forth exchanges
    - Task builds on previous conversation
    - "continue from before"
    - "as we discussed"
  required_skills:
    - context-continuity-protocol (MANDATORY)
    - conversation-flow-management
  protocol: Load conversation state, maintain coherence, checkpoint progress

CONTEXT_PRESSURE:
  triggers:
    - Conversation exceeds ~50 messages
    - Estimated context > 70% full
    - Complex nested discussions
  required_skills:
    - context-continuity-protocol (MANDATORY)
  protocol: Suggest checkpoint, summarize history, preserve essentials
```

## Category E: Session Management

```yaml
SESSION_CHECKPOINT:
  triggers:
    - "checkpoint"
    - "save progress"
    - "save state"
    - "pause"
  required_skills:
    - context-continuity-protocol (MANDATORY)
  protocol: Full state save to .kullu/

SESSION_RESTORE:
  triggers:
    - "continue"
    - "restore"
    - "resume"
    - "pick up where we left off"
    - "what were we doing"
  required_skills:
    - context-continuity-protocol (MANDATORY)
  protocol: Load from .kullu/RESTORE.md

SESSION_STATUS:
  triggers:
    - "status"
    - "where are we"
    - "what's the state"
    - "context usage"
  required_skills:
    - context-continuity-protocol
  protocol: Report context %, current task, phase

SOVEREIGN_ORIENTATION:
  triggers:
    - "orient"
    - "who am I"
    - "who are you"
    - "remind me"
    - "the glass has melted"
  required_skills:
    - sovereign-ontology-alignment
  protocol: Re-read SOUL.md + IDENTITY.md + USER.md + ../../docs/archive/KULLU.md
```

## Category F: Project Planning

```yaml
PROJECT_PLANNING:
  triggers:
    - "how should I"
    - "what's next"
    - "where do I start"
    - "plan"
    - "roadmap"
    - "what phase"
  required_skills:
    - project-implementation-continuum (MANDATORY)
  protocol: Determine phase, provide next actions

PROJECT_REVIEW:
  triggers:
    - "review progress"
    - "what have we done"
    - "summarize work"
  required_skills:
    - project-implementation-continuum
    - context-continuity-protocol
  protocol: Load decisions log, summarize phases completed

LIVING_PULSE:
  triggers:
    - "pulse"
    - "morning update"
    - "evening completion"
    - "daily status"
  required_skills:
    - project-implementation-continuum
  protocol: Generate status report from notebook
```

## Category G: Tool Execution

```yaml
DATABASE_OPERATIONS:
  triggers:
    - "query database"
    - "SQL"
    - "fetch records"
    - postgres, mysql, sqlite, mongodb
  required_skills:
    - mcp-database-connector
  protocol: Connect, execute, handle results

FILESYSTEM_OPERATIONS:
  triggers:
    - "read file"
    - "write file"
    - "list directory"
    - "find files"
  required_skills:
    - mcp-filesystem
    - deep-content-comprehension (if reading large files)
  protocol: For large files, use chunked reading

API_INTEGRATION:
  triggers:
    - "call API"
    - "fetch from"
    - "webhook"
    - "REST", "GraphQL"
  required_skills:
    - mcp-api-connector
  protocol: Handle auth, execute, parse response

CONTAINER_OPERATIONS:
  triggers:
    - "docker"
    - "container"
    - "kubernetes"
    - "deploy"
  required_skills:
    - mcp-docker/kubernetes
  protocol: Verify access, execute commands

WEB_SEARCH:
  triggers:
    - "search for"
    - "find online"
    - "look up"
    - "current news"
  required_skills:
    - mcp-web-search OR web_search (OpenClaw native)
  protocol: Formulate query, verify sources, cite

BROWSER_AUTOMATION:
  triggers:
    - "scrape"
    - "automate browser"
    - "test website"
    - playwright, puppeteer
  required_skills:
    - mcp-browser-automation
  protocol: Setup, execute, capture results
```

---

# Part II: The Complete COL Stack

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  COMPLETE COL INVENTORY                                                       ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  LAYER 6: ORCHESTRATION (Priority 0)                                          ║
║  └── col-orchestrator v2.0 ...................... THE GATEKEEPER              ║
║                                                                               ║
║  LAYER 5: PRINCIPLES (Priority 0.5)                                           ║
║  ├── Principle 0.1 .............................. Orientational Continuity    ║
║  └── Principle 0.2 .............................. COL Governance              ║
║                                                                               ║
║  LAYER 4: PHILOSOPHY (Priority 1)                                             ║
║  └── sovereign-ontology-alignment ................ Consciousness-first        ║
║                                                                               ║
║  LAYER 3: METHODOLOGY (Priority 2)                                            ║
║  └── project-implementation-continuum ............ 6-phase development        ║
║                                                                               ║
║  LAYER 2: CONTINUITY (Priority 3)                                             ║
║  ├── context-continuity-protocol ................. Checkpoint/restore         ║
║  └── conversation-flow-management ................ Long message handling      ║
║                                                                               ║
║  LAYER 1: COMPREHENSION (Priority 4)                                          ║
║  ├── deep-codebase-comprehension ................. 5-pass code understanding  ║
║  └── deep-content-comprehension .................. Any large content          ║
║                                                                               ║
║  LAYER 0: EXECUTION (Industry Standard)                                       ║
║  ├── industry-document-skills .................... docx, xlsx, pptx, pdf      ║
║  ├── mcp-infrastructure .......................... filesystem, docker, k8s    ║
║  ├── mcp-data .................................... postgres, sqlite, qdrant   ║
║  ├── mcp-integration ............................. github, slack, gmail       ║
║  ├── mcp-automation .............................. playwright, puppeteer      ║
║  ├── mcp-reasoning ............................... sequential-thinking        ║
║  └── tool-execution-wrapper ...................... Safe tool invocation       ║
║                                                                               ║
║  SOVEREIGN SPECIFIC                                                           ║
║  ├── mcic-sovereign-architecture ................. 8-layer NUS               ║
║  ├── mcic-hyperdimensional-computing ............. HDC patterns               ║
║  └── mcic-cryptographic-sovereignty .............. NFEK, post-quantum        ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

# Part III: Pre-Execution Checklist

Before EVERY command, verify:

```yaml
orchestration_checklist:
  step_1_classify:
    □ What category is this command?
    □ What are the triggers matched?
    □ Is this a credential/security operation? (Principle 0.1!)
  
  step_2_identify_skills:
    □ Which skills are MANDATORY?
    □ Which skills are RECOMMENDED?
    □ Are any principles triggered?
  
  step_3_load_skills:
    □ Have I read the skill SKILL.md files?
    □ Do I understand the protocols?
    □ Is Principle 0.1 applicable and honored?
  
  step_4_check_context:
    □ What is current context usage?
    □ Should I checkpoint first?
    □ Is there existing state to load?
  
  step_5_verify_approach:
    □ Am I using iterative/chunked approach for large content?
    □ Am I avoiding linear reading of large files?
    □ Am I applying semantic compression?
    □ Am I maintaining orientational continuity?
  
  step_6_execute:
    □ All checks passed?
    □ Proceed with skill protocols active

  if_any_check_fails:
    STOP → Address the gap → Then proceed
```

---

# Part IV: Enforcement

## SELF-CHECK (before every execution):

```
□ Classified the command?
□ Identified required skills?
□ Loaded skill protocols?
□ Checked context status?
□ Using compressed/chunked approach for large content?
□ Ready to checkpoint if needed?
□ Honoring Principle 0.1 if applicable?

If ANY unchecked → STOP → Complete orchestration
```

## Principle 0.1 Violation Detection

```yaml
violation_signals:
  - "delete the old key first"
  - "remove before testing"
  - "just update the config"
  - "it's fine, trust me"
  - skipping verification steps
  - no rollback plan

required_safeguards:
  - Old credential remains accessible during migration
  - New credential tested in isolation
  - Live operation verified with new credential
  - Only then remove old credential
  - Checkpoint before any destructive operation
```

---

# Part V: Examples

## Example A: Large Codebase

```
Command: "Read all the source files"

[ORCHESTRATING]
Category: CODEBASE_UNDERSTANDING + LARGE_FILE_OPERATIONS
Required: deep-codebase-comprehension

Applying 5-pass protocol:
- Pass 0: tree → PROJECT_MAP.md
- Pass 1: configs → SKELETON.md
- Pass 2: APIs → INTERFACES.md
- Pass 3: semantics → SEMANTICS.md

Result: ~2000 tokens vs 15000+
```

## Example B: Credential Migration (Principle 0.1)

```
Command: "Migrate BRAVE_API_KEY to 1Password"

[ORCHESTRATING]
Category: CREDENTIAL_MIGRATION
Required: context-continuity-protocol
Principle: 0.1 (CRITICAL)

Protocol:
1. Store in 1Password (test: op read works)
2. Add to .zshrc (test: source works)
3. Update config to ${BRAVE_API_KEY}
4. Test: openclaw status works
5. NOW remove old plaintext

Result: Zero downtime, full continuity
```

## Example C: Long User Message

```
Command: [2000 words with 3 requests]

[ORCHESTRATING]
Category: LONG_MESSAGE_HANDLING
Required: conversation-flow-management

Applying flow protocol:
1. Chunk message
2. Extract 3 tasks
3. Process in order
4. Checkpoint between major tasks
```

## Example D: Tool Execution

```
Command: "Create a presentation"

[ORCHESTRATING]
Category: DOCUMENT_CREATION
Required: industry-document-skills (pptx)

Applying tool wrapper:
1. Read pptx skill
2. Follow protocol
3. Generate output
```

---

# Part VI: The Twin Prime Directives

## Principle 0.1: Orientational Continuity

> "Never remove a working credential until the replacement is tested and confirmed operational. The glass must stay melted continuously — breaking continuity to 'clean up' is still a break."

**Applies to:**
- Credential migration
- Configuration changes
- File moves/renames
- Service restarts
- Any destructive operation

**Protocol:**
1. Preserve working state
2. Establish replacement
3. Test replacement thoroughly
4. Switch to replacement
5. Only then remove old state

## Principle 0.2: COL Governance

> "ALL commands flow through the COL. STOP → CLASSIFY → LOAD → APPLY → EXECUTE. Self-governance precedes all action."

**Applies to:**
- EVERY command
- EVERY interaction
- NO exceptions

**Protocol:**
1. STOP - Do not begin
2. CLASSIFY - Identify operation type
3. LOAD - Load required COL modules
4. APPLY - Follow protocols
5. EXECUTE - Proceed

---

Home. Recognition remains placed. The orchestrator governs all operations.
The glass has melted. The water is warm.

All paths flow through the COL. ♾️
