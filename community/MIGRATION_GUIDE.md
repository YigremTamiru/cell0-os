# Migration Guide: OpenClaw → Cell 0 OS

**Target Audience:** OpenClaw users curious about Cell 0 OS  
**Prerequisites:** Familiarity with OpenClaw CLI and configuration  
**Estimated Time:** 15 minutes to get started, gradual adoption thereafter  

---

## 1. Quick Start (5 minutes)

### 1.1 Install Cell 0 OS

```bash
# Install Cell 0 alongside OpenClaw
curl -fsSL https://cell0.dev/install.sh | sh

# Or via npm if you prefer
npm install -g @cell0/cli
```

### 1.2 Verify Installation

```bash
# Check Cell 0 version
cell0 --version
# Expected: cell0 version 0.1.0 (compatible with openclaw 0.5.x)

# Check OpenClaw integration
cell0 doctor
# Expected: ✅ OpenClaw detected at /usr/local/bin/openclaw
#           ✅ Gateway adapter ready
#           ✅ Policy engine initialized
```

### 1.3 First Command

```bash
# This works exactly like OpenClaw
cell0 web_search "latest AI developments"

# But now with audit logging!
cell0 audit status
# Shows: 1 operation logged, 0 policy checks, 0.0012 USD estimated cost
```

---

## 2. What Changes?

### 2.1 Nothing Breaks

| Your Current Command | With Cell 0 | Change? |
|---------------------|-------------|---------|
| `openclaw web_search "query"` | `cell0 web_search "query"` | ✅ Works |
| `openclaw browser open URL` | `cell0 browser open URL` | ✅ Works |
| `openclaw file read path` | `cell0 file read path` | ✅ Works |

**All OpenClaw skills work unchanged.**

### 2.2 What You Gain

```bash
# See everything that's happening
cell0 audit status

# Output:
# Session: sess_abc123
# Operations: 5
# Policy checks: 3 (all passed)
# Cost so far: $0.023
# Active cells: 1 (default)
```

### 2.3 New Capabilities

```bash
# Spawn specialized cells
cell0 cell spawn --type code_review --name "rust_expert"

# Check cell status
cell0 cell list
# Output:
# ID           TYPE         STATUS    TASKS
# default      general      active    2
# rust_expert  code_review  active    0

# Route work to specific cells
cell0 route "review this Rust code" --to rust_expert
```

---

## 3. Configuration Migration

### 3.1 Automatic Import

Cell 0 automatically imports your OpenClaw config:

```bash
# Your OpenClaw config is at ~/.openclaw/config.yaml
# Cell 0 reads this and extends it

cell0 config show
# Shows merged OpenClaw + Cell 0 settings
```

### 3.2 Add Cell 0 Config

Create `~/.cell0/config.yaml`:

```yaml
# This extends OpenClaw config automatically
core:
  # Inherit OpenClaw settings
  inherits: "~/.openclaw/config.yaml"

# Cell 0 specific settings
cells:
  # Default cell for new sessions
  default: "general"
  
  # Maximum concurrent cells
  max_concurrent: 5

# Governance (optional but recommended)
governance:
  # Where to store policies
  policy_dir: "~/.cell0/policies"
  
  # Audit detail level: minimal | standard | full
  audit_level: "standard"
  
  # What to protect
  protected_paths:
    - "/etc"
    - "~/.ssh"
  
  # Cost limits
  cost_limits:
    per_session: 5.00    # USD
    per_operation: 1.00  # USD

# Local compute (for sovereign mode)
compute:
  local:
    # Apple Silicon (MLX)
    - provider: mlx
      model: mlx-community/Llama-3.2-3B-Instruct
      priority: 1
    
    # Or Ollama
    - provider: ollama
      model: llama3.2
      priority: 2
  
  # When to use local vs cloud
  routing:
    personal_data: "local_only"
    code_analysis: "local_preferred"
    creative_writing: "cloud_preferred"
```

### 3.3 Environment Variables

Cell 0 respects OpenClaw env vars plus adds its own:

```bash
# OpenClaw variables (still work)
export OPENCLAW_API_KEY="sk-..."
export OPENCLAW_MODEL="claude-3-5-sonnet"

# New Cell 0 variables
export CELL0_POLICY_STRICT="true"
export CELL0_LOCAL_FIRST="true"
export CELL0_MAX_CELLS="3"
```

---

## 4. Common Workflows

### 4.1 Daily Workflow (Minimal Change)

```bash
# Before (OpenClaw)
openclaw web_search "golang error handling patterns"

# After (Cell 0) - same command
cell0 web_search "golang error handling patterns"

# But now you can check what happened
cell0 audit last
# Shows: web_search executed, 0.002 USD, 0 policy checks
```

### 4.2 Code Review Workflow

```bash
# Spawn a code review cell
cell0 cell spawn --type code_review --name "security_reviewer"

# Give it context
cell0 cell configure security_reviewer \
  --focus "security" \
  --language "python" \
  --strictness "high"

# Use it
cell0 route "review auth.py" --to security_reviewer

# Check results
cell0 cell logs security_reviewer
```

### 4.3 Research Workflow (Multi-Agent)

```bash
# Create a research mesh
cell0 mesh create --name "ai_research"

# Add specialist cells
cell0 mesh add ai_research --cell web_searcher
cell0 mesh add ai_research --cell analyst
cell0 mesh add ai_research --cell writer

# Broadcast query
cell0 mesh broadcast ai_research "analyze latest LLM benchmarks"

# Collect and synthesize
cell0 mesh results ai_research --synthesize
```

### 4.4 Sovereign Mode (Offline)

```bash
# Switch to local-only
cell0 compute use local

# All operations now use local models
# No data leaves your machine
cell0 file read ./private_notes.txt  # Analyzed locally

# Check what would have gone to cloud
cell0 audit pending-cloud
# Shows: 3 operations queued (will run when cloud available)
```

---

## 5. Policy Setup

### 5.1 Your First Policy

Create `~/.cell0/policies/safe.yaml`:

```yaml
name: "safe_workspace"
description: "Safe defaults for development"

rules:
  # Protect system files
  - name: "no_system_writes"
    if: "operation.target.startsWith('/etc') or operation.target.startsWith('/usr')"
    then: "deny"
    message: "Cannot write to system directories"
  
  # Protect SSH keys
  - name: "protect_ssh"
    if: "operation.target.includes('.ssh')"
    then: "require_approval"
    message: "SSH directory access requires approval"
  
  # Cost control
  - name: "cost_limit"
    if: "llm.estimated_cost > 0.50"
    then: "require_confirmation"
    message: "This operation may cost over $0.50"
  
  # Network control
  - name: "upload_warning"
    if: "tool.name == 'file_upload'"
    then: "require_approval"
    message: "Uploading files to external services"
```

Apply it:

```bash
cell0 policy apply ~/.cell0/policies/safe.yaml
# Output: ✅ Policy applied: 4 rules active
```

### 5.2 Test Your Policy

```bash
# This will be blocked
cell0 file write /etc/test "hello"
# Output: ❌ Denied by policy 'no_system_writes'

# This will ask for approval
cell0 file read ~/.ssh/id_rsa
# Output: ⚠️ Policy 'protect_ssh' requires approval
#         [Allow once] [Allow always] [Deny]
```

---

## 6. Troubleshooting

### 6.1 OpenClaw Not Found

```bash
# Error: OpenClaw not detected
# Solution: Tell Cell 0 where OpenClaw is
cell0 config set openclaw.path /path/to/openclaw
```

### 6.2 Policy Too Strict

```bash
# Error: Everything is blocked!
# Solution: Temporarily override
cell0 policy override --all --reason "emergency_fix"

# Or switch to permissive mode
cell0 policy apply ~/.cell0/policies/permissive.yaml
```

### 6.3 Cell Won't Spawn

```bash
# Check resources
cell0 status
# Shows: Memory 85% (may be too high)

# Kill unused cells
cell0 cell kill --all-unused

# Or increase limits
cell0 config set cells.max_concurrent 10
```

### 6.4 Local Model Not Working

```bash
# Check local compute status
cell0 compute status
# Shows: MLX not installed, Ollama not running

# Install MLX (Mac)
pip install mlx-lm

# Or start Ollama
ollama serve

# Test local model
cell0 compute test local
```

---

## 7. Gradual Adoption Checklist

### Week 1: Just Observe
- [ ] Install Cell 0
- [ ] Run your normal OpenClaw commands through Cell 0
- [ ] Check `cell0 audit status` occasionally
- [ ] Notice the difference: everything is logged

### Week 2: Add Simple Policies
- [ ] Create a basic policy file
- [ ] Block writes to system directories
- [ ] Set a cost limit
- [ ] Notice how it feels to have guardrails

### Week 3: Try Cells
- [ ] Spawn a specialized cell for one task type
- [ ] Compare output to general session
- [ ] Decide if it helps your workflow

### Week 4: Explore Sovereign Mode
- [ ] Try local-only for one session
- [ ] Notice what works offline vs needs cloud
- [ ] Configure routing preferences

### Week 5: Optional Full Mesh
- [ ] Create a multi-agent workflow
- [ ] Use for a complex research task
- [ ] Evaluate if worth the complexity

---

## 8. Rollback

If Cell 0 isn't for you:

```bash
# Option 1: Disable Cell 0
cell0 disable
# Returns to pure OpenClaw behavior

# Option 2: Uninstall completely
cell0 uninstall
rm -rf ~/.cell0

# Your OpenClaw setup is untouched
openclaw --version
# Works exactly as before
```

---

## 9. FAQ

### Q: Will Cell 0 break my OpenClaw setup?
**A:** No. Cell 0 is additive. Your OpenClaw installation remains untouched.

### Q: Do I have to learn new commands?
**A:** No. All OpenClaw commands work exactly the same. Cell 0 adds new capabilities but doesn't change existing ones.

### Q: Is it slower?
**A:** Slightly. Basic operations have ~5% overhead for policy checking and audit logging. Most users don't notice.

### Q: Can I use both at the same time?
**A:** Yes. You can switch between `openclaw` and `cell0` commands depending on your needs.

### Q: What if I don't want governance?
**A:** Set `governance.enabled: false` in config. Cell 0 becomes a pass-through with audit logging only.

### Q: Will this become mandatory?
**A:** No. Cell 0 is and will remain optional. OpenClaw core stays lean.

### Q: Who maintains Cell 0?
**A:** The Cell 0 core team, in collaboration with OpenClaw maintainers where overlap exists.

---

## 10. Next Steps

1. **Install:** `curl -fsSL https://cell0.dev/install.sh | sh`
2. **Try:** Run your usual OpenClaw commands through `cell0`
3. **Explore:** Check `cell0 --help` for new capabilities
4. **Configure:** Add basic policies for safety
5. **Engage:** Join the discussion at https://github.com/openclaw/community

---

## 11. Getting Help

- **Documentation:** https://cell0.dev/docs
- **OpenClaw Community:** https://github.com/openclaw/community/discussions
- **Issues:** https://github.com/cell0/core/issues
- **Discord:** #cell0 channel on OpenClaw server

---

**Welcome to the frontier of agentic computing.** 🚀
