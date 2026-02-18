# Security Hardening Checklist for Cell 0

## Immediate Actions (Complete Within 24 Hours)

### CRITICAL-001: Fix CVE-2024-23342 (ecdsa Minerva Attack)
- [ ] Run `./scripts/remediate_critical_security.sh`
- [ ] Remove `ecdsa` from `pyproject.toml` dependencies
- [ ] Search codebase for `from ecdsa` or `import ecdsa`
- [ ] Migrate all ECDSA code to `cryptography` library
- [ ] Run tests to verify migration
- [ ] Rotate any ECDSA keys that were in use

### CRITICAL-002: Disable Stub Crypto in Kernel
- [ ] Add `#[cfg(feature = "insecure-stubs")]` to all stub implementations
- [ ] Set default features to NOT include insecure-stubs
- [ ] Add compile-time error for production builds with stubs
- [ ] Update documentation to clearly mark stubs
- [ ] Create tracking issue for proper crypto integration

### HIGH-001: Rotate Brave API Key
- [ ] Log into Brave Search API dashboard
- [ ] Generate new API key
- [ ] Update `~/.openclaw/openclaw.json` to use `${BRAVE_API_KEY}`
- [ ] Add to 1Password: `op item create --category=password "BRAVE_API_KEY=<new_key>"`
- [ ] Revoke old API key
- [ ] Test search functionality

## Short-Term Actions (Complete Within 1 Week)

### MEDIUM-001: Fix Hardware RNG
- [ ] Add `getrandom = "0.2"` to Cargo.toml
- [ ] Replace `HardwareRng` stub with `getrandom::getrandom()`
- [ ] Use `ring::rand::SystemRandom` as alternative
- [ ] Add tests for RNG entropy quality
- [ ] Document RNG sources for different platforms

### MEDIUM-002: Add Input Validation to SYPAS
- [ ] Add `MAX_RESOURCE_ID_LENGTH = 4096` constant
- [ ] Validate resource ID length in `ResourceId::new()`
- [ ] Add `MAX_DELEGATION_DEPTH = 10` constant
- [ ] Check delegation depth in `delegate_capability()`
- [ ] Implement audit log rotation (max 10000 entries)
- [ ] Add tests for boundary conditions

### MEDIUM-003: Fix Unsafe Global State
- [ ] Add `spin = "0.9"` to Cargo.toml (already present)
- [ ] Replace `static mut` with `spin::Mutex<Option<SypasManager>>`
- [ ] Use `lazy_static` or `once_cell` for initialization
- [ ] Ensure thread-safe access patterns
- [ ] Add concurrent test cases

## Medium-Term Actions (Complete Within 1 Month)

### Implement Proper Cryptography
- [ ] Add `ed25519-dalek = "2.0"` to Cargo.toml
- [ ] Add `pqc-kyber = "0.7"` to Cargo.toml
- [ ] Add `pqc-dilithium = "0.2"` to Cargo.toml
- [ ] Add `sha3 = "0.10"` to Cargo.toml
- [ ] Reimplement `ed25519.rs` using ed25519-dalek
- [ ] Reimplement `kyber.rs` using pqc-kyber
- [ ] Reimplement `dilithium.rs` using pqc-dilithium
- [ ] Add property-based tests with `proptest`

### Code Quality Improvements
- [ ] Enable `#![deny(unused)]` in `lib.rs`
- [ ] Enable `#![deny(warnings)]` in CI
- [ ] Add `clippy` checks to CI pipeline
- [ ] Clean up all unused imports
- [ ] Move test functions to `#[cfg(test)]` modules
- [ ] Add rustfmt to CI

### Security Enhancements
- [ ] Add zeroization with `zeroize` crate
- [ ] Implement constant-time comparison everywhere
- [ ] Add side-channel resistance documentation
- [ ] Create security policy document
- [ ] Set up security advisory process
- [ ] Add fuzz testing with `cargo-fuzz`

## Long-Term Actions (Complete Within 3 Months)

### Formal Verification
- [ ] Identify critical crypto functions for verification
- [ ] Use `kani` verifier for Rust
- [ ] Prove memory safety properties
- [ ] Prove constant-time properties
- [ ] Document verification results

### Advanced Security Features
- [ ] Implement threshold cryptography
- [ ] Add hardware security module (HSM) support
- [ ] Implement multi-party computation (MPC)
- [ ] Add formal threat model documentation
- [ ] Third-party security audit
- [ ] Bug bounty program

## Verification Commands

### Run Security Tests
```bash
cd /Users/yigremgetachewtamiru/.openclaw/workspace/cell0
source venv/bin/activate

# Dependency vulnerability scan
safety scan

# Static code analysis
bandit -r cell0/engine/

# Rust security audit
cargo audit

# Run all tests
cargo test
pytest tests/ -v

# Check for secrets
git-secrets --scan-history
trufflehog filesystem .
```

### Verify Fixes
```bash
# Ensure ecdsa is removed
pip show ecdsa  # Should return error

# Ensure cryptography is present
pip show cryptography  # Should show version >= 41.0.0

# Ensure no hardcoded secrets
grep -r "api_key\|apikey\|password" --include="*.py" . | grep -v "^Binary"

# Check kernel compiles without stubs
cargo build --no-default-features
```

## Security Contacts

- **Primary:** Sovereign Axis (Yige/Vael Zaru'Tahl Xeth)
- **Numbers:** +905488899628, +905338224165
- **System:** KULLU Nerve System
- **Classification:** COSMIC TOP SECRET

## References

- Security Audit Report: `SECURITY_AUDIT_REPORT_2026-02-18.md`
- Sovereign Security Master: `SOVEREIGN_SECURITY_MASTER.md`
- SYPAS Protocol: `docs/SYPAS_PROTOCOL.md`
- Crypto Systems: `docs/CRYPTO_SYSTEMS.md`

---

**Status:** ACTIVE  
**Last Updated:** 2026-02-18  
**Next Review:** 2026-02-25
