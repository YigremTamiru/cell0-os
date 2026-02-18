# Cell0-OS Security Audit Report
**Date:** 2026-02-15  
**Auditor:** Security Sub-Agent  
**Location:** ~/cell0/

## Executive Summary

**CRITICAL ISSUES FOUND:** The system has **3 CRITICAL** and **2 HIGH** severity security issues that must be fixed before production deployment.

---

## 1. CRITICAL: .env File Committed to Repository

**Severity:** CRITICAL  
**Status:** IMMEDIATE ACTION REQUIRED

### Finding
The `.env` file exists in the repository and contains sensitive configuration:

```bash
# File: ~/cell0/.env (COMMITTED)
CELL0_ALLOW_LOCAL_ADMIN=true
CELL0_WHATSAPP_PHONE_NUMBER_ID=+905338224165  # EXPOSED PHONE NUMBER
CELL0_PUBLIC_HOST=agent.kulluai.com
```

### Risk
- Phone number (+905338224165) is exposed in version control
- Configuration secrets can be retrieved from git history
- Anyone with repository access can see production configuration

### Fix Required
```bash
# 1. Remove .env from git tracking
git rm --cached .env
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore
echo ".env.*" >> .gitignore

# 2. Create .env.example template instead
cat > .env.example << 'EOF'
# Copy to .env and fill in real values
CELL0_DEFAULT_PROVIDER=ollama
CELL0_DEFAULT_MODEL=ollama/qwen2.5:7b
CELL0_PORT=18800
CELL0_WS_PORT=8765
CELL0_PUBLIC_HOST=your-domain.com
CELL0_TUNNEL_NAME=your-tunnel
CELL0_WHATSAPP_PHONE_NUMBER_ID=your-phone-id
CELL0_ADMIN_TOKEN=your-secure-random-token
EOF

# 3. Commit the changes
git add .gitignore .env.example
git commit -m "security: Remove .env from repository, add example template"

# 4. Rotate any exposed secrets immediately
```

---

## 2. CRITICAL: Admin Token Stored in localStorage (XSS Risk)

**Severity:** CRITICAL  
**File:** `service/ui/assets/app.js` (lines 45-46, 547-548)

### Finding
Admin authentication tokens are stored in browser localStorage:

```javascript
// app.js - Lines 45-46
const token = (localStorage.getItem("cell0.adminToken") || "").trim();
return token ? { "X-Cell0-Admin-Token": token } : {};

// app.js - Line 547
localStorage.setItem("cell0.adminToken", token);

// app.js - Line 548 (unmasked input)
dom.adminTokenInput.value = localStorage.getItem("cell0.adminToken") || "";
```

### Risk
- XSS attack can steal admin tokens from localStorage
- Tokens persist in browser indefinitely (no expiration)
- Input field displays token in plaintext

### Fix Required
```javascript
// Option 1: Use httpOnly cookies (server-side set)
// Option 2: Use sessionStorage (cleared on tab close)
// Option 3: Mask the input field

// Minimum fix for UI (app.js)
dom.adminTokenInput.type = "password"; // Mask the input

// Better: Use sessionStorage instead of localStorage
const token = (sessionStorage.getItem("cell0.adminToken") || "").trim();
sessionStorage.setItem("cell0.adminToken", token);

// Best: Use secure httpOnly cookies set by server
```

---

## 3. CRITICAL: CELL0_ALLOW_LOCAL_ADMIN Enabled by Default

**Severity:** CRITICAL  
**File:** `.env`, `cell0/config.py`

### Finding
```bash
# .env
CELL0_ALLOW_LOCAL_ADMIN=true
```

```python
# cell0/config.py - Line 123
"allow_local_admin": True,
```

### Risk
- In production with reverse proxy, attackers can spoof `X-Forwarded-For` 
- Admin endpoints can be accessed without authentication if behind load balancer
- The `_is_local_request()` check only validates `request.client.host`

### Fix Required
```python
# cell0/config.py - Change default
"allow_local_admin": False,  # Must be explicitly enabled in dev only
```

```bash
# .env - For development only (never in production)
CELL0_ALLOW_LOCAL_ADMIN=false
```

---

## 4. HIGH: No CORS Configuration

**Severity:** HIGH  
**File:** `service/cell0d.py`

### Finding
The FastAPI application does not configure CORS middleware:

```python
# cell0d.py - Missing CORS configuration
app = FastAPI(
    title="Cell 0 Daemon API",
    # ... no CORS middleware added
)
```

### Risk
- API may accept cross-origin requests from any domain
- Browser-based attacks can make requests to the API

### Fix Required
```python
# Add to cell0d.py
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(...)

# Restrictive CORS for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CELL0_CORS_ORIGINS", "http://localhost:18800").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

---

## 5. HIGH: Verbose Error Messages Expose Details

**Severity:** HIGH  
**File:** `service/cell0d.py`

### Finding
The exception handler returns detailed error information:

```python
# cell0d.py - Lines ~1072-1079
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            code="INTERNAL_ERROR",
            details={"message": str(exc)}  # EXPOSES INTERNAL DETAILS
        ).dict()
    )
```

Also in chat completion:
```python
# Returns full error details to client
failure_reason = result.get("error", "Provider response unavailable")
assistant_content = f"[cell0-degraded] {failure_reason or 'No provider response available'}"
```

### Risk
- Stack traces and internal errors exposed to clients
- Attackers can probe for vulnerabilities using error messages
- Provider API errors may leak sensitive configuration

### Fix Required
```python
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)  # Log full details
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            code="INTERNAL_ERROR",
            details=None  # Never expose internal details to client
        ).dict()
    )

# For degraded responses, don't expose raw errors
if failure_reason and "No module named" in failure_reason:
    failure_reason = "Provider dependencies missing"  # Generic message
```

---

## 6. MEDIUM: Provider Keys Status Endpoint Exposes Key Availability

**Severity:** MEDIUM  
**File:** `engine/api_keys.py`, `service/cell0d.py`

### Finding
The `/api/providers/keys` endpoint exposes which providers have keys configured:

```python
# api_keys.py
return {
    "provider": provider,
    "key_available": key is not None,  # Exposes if key exists
    "source": "1password" if self._op.is_available() and key else "environment",
    "environment_variable": env_var,  # Exposes env var name
}
```

### Risk
- Information disclosure about configured providers
- Environment variable naming conventions exposed

### Fix Required
```python
# Only expose to authenticated admin users
@app.get("/api/providers/keys", tags=["Providers"])
async def provider_keys(_admin: None = Depends(require_admin_access)):
    ...
```

---

## 7. MEDIUM: Webhook Verify Token in Query Parameter

**Severity:** MEDIUM  
**File:** `service/cell0d.py`

### Finding
WhatsApp webhook verification uses query parameters:

```python
@app.get("/api/channels/whatsapp/webhook")
async def whatsapp_webhook_verify(
    hub_verify_token: Optional[str] = Query(default=None, alias="hub.verify_token"),
    ...
):
```

### Risk
- Verify token may be logged in proxy/web server access logs
- URLs with tokens may be stored in browser history

### Fix Required
- Use POST with body for verification (Meta API limitation - cannot change)
- Ensure reverse proxy is configured to not log query parameters

---

## Positive Security Findings ✓

### ✓ Proper API Key Management
- API keys stored in 1Password vault or environment variables
- No hardcoded secrets in source code
- Key rotation support implemented

### ✓ Webhook Signature Verification
- Slack signatures verified with HMAC-SHA256
- WhatsApp signatures verified with HMAC-SHA256
- Replay protection with WebhookReplayGuard

### ✓ Admin Endpoint Protection
```python
async def require_admin_access(request: Request) -> None:
    configured = os.getenv("CELL0_ADMIN_TOKEN")
    if configured:
        provided = _extract_admin_token(request)
        if provided and hmac.compare_digest(configured, provided):
            return
        raise HTTPException(status_code=401, detail="Admin token required")
```

### ✓ Secrets Masked in UI
```python
def _mask(value: str) -> str:
    if not value:
        return "<unset>"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"
```

### ✓ Rate Limiting
Token bucket rate limiter implemented for providers

---

## Security Checklist

| Requirement | Status | Notes |
|-------------|--------|-------|
| No hardcoded secrets | ✓ PASS | Uses env vars/1Password |
| API keys in .env only | ✗ FAIL | .env is committed! |
| .gitignore excludes secrets | ⚠️ PARTIAL | .gitignore correct but file tracked |
| Tokens masked in UI | ✓ PASS | _mask() function used |
| Admin endpoints auth | ✓ PASS | require_admin_access implemented |
| CORS secure | ✗ FAIL | No CORS middleware configured |
| Error messages sanitized | ✗ FAIL | Detailed errors exposed |

---

## Immediate Action Items

1. **URGENT:** Remove `.env` from git repository and rotate exposed secrets
2. **URGENT:** Change `CELL0_ALLOW_LOCAL_ADMIN` default to `false`
3. **URGENT:** Fix admin token storage (use httpOnly cookies)
4. **HIGH:** Add CORS middleware with restrictive configuration
5. **HIGH:** Sanitize error messages in production
6. **MEDIUM:** Protect provider key status endpoint with admin auth

---

## Production Deployment Checklist

Before deploying to production, verify:

- [ ] .env file is NOT in repository
- [ ] CELL0_ALLOW_LOCAL_ADMIN=false
- [ ] CELL0_ADMIN_TOKEN is set to cryptographically secure random value
- [ ] CORS origins are restricted to known domains
- [ ] Error logging goes to file (not exposed to clients)
- [ ] Webhook secrets are rotated
- [ ] TLS/SSL is enabled (HTTPS)
- [ ] Rate limiting is enabled
- [ ] 1Password vault is configured for key storage
