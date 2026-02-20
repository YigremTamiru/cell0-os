# Cell 0 OS — Bug Fix History

> Comprehensive log of all bugs found and fixed during development.
> Each entry documents: the bug, root cause analysis, fix applied, and verification.

---

## Phase 3B Hotfix — 2026-02-19

### BUG-001: Portal JS Parse Failure — All Tabs Broken

| Field | Detail |
|-------|--------|
| **Severity** | 🔴 Critical |
| **File** | `src/portal/portal.ts` L834 |
| **Symptom** | Only the Agent Library tab worked. Chat, Monitor, Nerve Map, Config, and Glassbox were completely non-functional. Boot sequence never completed. |
| **Root Cause** | The `onclick` handler for Agent Library folders used `\x27` (hex escape for single quote) inside a TypeScript template literal. TypeScript resolved `\x27` to a literal `'` in the compiled output, creating malformed JavaScript: `onclick="toggleCategory(this, ''+cat.slug+'')"`. This broke the entire `<script>` block — the browser's JS parser stopped at the first syntax error, preventing `runBootSequence()` from executing, which meant `initApp()`, `initTabs()`, and all rendering functions never ran. |
| **Fix** | Replaced inline `\x27` quoting with `this.dataset.slug` — the category slug was already available via the `data-slug="..."` HTML attribute on the same element. |
| **Verification** | 4/4 JS parse tests pass: `new Function()`, IIFE wrap, `node --check`, Acorn parser. All 5 Portal tabs functional in browser. |

```diff
- html += '<div ... onclick="toggleCategory(this, \x27'+cat.slug+'\x27)">'
+ html += '<div ... onclick="toggleCategory(this,this.dataset.slug)">'
```

---

### BUG-002: ANSI Escape Sequences in Boot Lines

| Field | Detail |
|-------|--------|
| **Severity** | 🔴 Critical |
| **File** | `src/portal/portal.ts` L457-477 |
| **Symptom** | Boot sequence animation never started. Black/stuck screen in portal. |
| **Root Cause** | The `bootLines` array contained `\\x1b[32m` ANSI escape codes intended to simulate terminal coloring. Inside TypeScript's template literal, `\\x1b` was resolved to `\x1b` — the raw ESC character (0x1B). This non-printable byte was injected into the browser's JS, causing a parse error before any code could execute. The `.replace()` calls meant to strip these codes were also escaped incorrectly. |
| **Fix** | Removed all ANSI escape sequences from bootLines. Replaced `'[ \\x1b[32m OK \\x1b[0m ]'` with plain `'[ OK ]'`. Removed the `.replace(/\\x1b\\[32m/g, '')` strip calls since they were no longer needed. |
| **Verification** | `cat -v` confirms no non-printable characters. Boot sequence animates correctly in browser. |

```diff
- { text: '[ \\x1b[32m OK \\x1b[0m ] Starting Cell 0 OS...', cls: 'boot-ok' },
+ { text: '[ OK ] Starting Cell 0 OS Gateway v1.2.0...', cls: 'boot-ok' },
```

---

### BUG-003: Dangling textContent Assignment

| Field | Detail |
|-------|--------|
| **Severity** | 🟡 Medium |
| **File** | `src/portal/portal.ts` L484 |
| **Symptom** | Would have caused a parse error if BUG-001/002 were fixed independently. |
| **Root Cause** | After applying the BUG-002 sed fix to remove ANSI `.replace()` calls, the line `line.textContent = bootLines[i].text` was left without a semicolon and with a trailing blank line where the `.replace()` chain had been. |
| **Fix** | Added semicolon: `line.textContent = bootLines[i].text;` |
| **Verification** | `node --check` passes on extracted portal script. |

```diff
- line.textContent = bootLines[i].text
-   
+ line.textContent = bootLines[i].text;
```

---

### BUG-004: Python Backend 30-Second Timeout

| Field | Detail |
|-------|--------|
| **Severity** | 🟠 High |
| **File** | `src/gateway/python-bridge.ts` L136 |
| **Symptom** | Gateway startup showed `⚠️ Python backend failed to start: Error: Python daemon did not become ready after 30000ms` and ran in "standalone mode" despite the Python daemon being fully operational. |
| **Root Cause** | The Python bridge health check polled `/api/system/health` but the Python daemon's actual health endpoint is `/health`. The health check retried 30 times (30 seconds) hitting 404 every time before giving up. |
| **Fix** | Changed health check URL from `/api/system/health` to `/health`. |
| **Verification** | Gateway now reports `[python-bridge] Python daemon is ready` within ~1 second of startup. |

```diff
- const res = await fetch(`${this.baseUrl}/api/system/health`);
+ const res = await fetch(`${this.baseUrl}/health`);
```

---

### BUG-005: Missing Agent Library Boot Line

| Field | Detail |
|-------|--------|
| **Severity** | 🟢 Low |
| **File** | `src/portal/portal.ts` L472 |
| **Symptom** | Boot sequence didn't mention Agent Library status. |
| **Root Cause** | Phase 3B added the Agent Library but didn't add a corresponding boot status line to the portal's boot animation sequence. |
| **Fix** | Added `{ text: '[ OK ] Agent Library: 12 categories, 66 specialists', cls: 'boot-ok' }` to the bootLines array. |
| **Verification** | Boot sequence now shows Agent Library status during animation. |

---

## Phase 2 Hotfix — 2026-02-18

### BUG-000: resolveGatewayPort Null Safety

| Field | Detail |
|-------|--------|
| **Severity** | 🟡 Medium |
| **File** | `src/config/config.ts` |
| **Symptom** | `resolveGatewayPort(undefined)` threw TypeError crash. |
| **Root Cause** | Function didn't handle null/undefined config object. |
| **Fix** | Added null-safe optional chaining in function signature and body. |
| **Verification** | `resolveGatewayPort({})` returns default 18789. `resolveGatewayPort(undefined)` returns 18789. |
