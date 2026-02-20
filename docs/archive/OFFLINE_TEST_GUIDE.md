# Cell 0 OS - Offline Test Guide

Complete guide for running tests without network access. This is essential for:
- Air-gapped environments
- CI/CD pipelines with restricted network
- Development on airplanes, trains, remote locations
- Security-hardened build systems

## Quick Start (Offline Mode)

### Option 1: Pre-existing Environment (Fastest)

If you already have a working virtual environment with pytest:

```bash
./tests/run_tests_fixed.sh --offline
```

### Option 2: Bootstrap Once, Run Many

First time setup (with network):

```bash
./setup_test_env.sh                    # Create venv with all dependencies
./tests/run_tests_fixed.sh --offline   # Run tests offline anytime after
```

### Option 3: System Python Fallback

If you can't create virtual environments:

```bash
pip install pytest pytest-asyncio      # Install pytest system-wide
./tests/run_tests_fixed.sh --offline --use-system-python
```

## How Offline Mode Works

### Detection Priority

The scripts try these methods in order:

1. **Existing venv** (`cell0/venv` or `.venv`) with pytest pre-installed
2. **Local wheels cache** (`tests/wheels/*.whl`)
3. **System Python** with pytest (if `--use-system-python` flag used)
4. **Fail gracefully** with helpful error message

### What's Different in Offline Mode?

| Feature | Online | Offline |
|---------|--------|---------|
| pip upgrade | Yes | Skipped |
| Install dependencies | From PyPI | From local wheels only |
| Network tests | Run | Skipped (`-m 'not network'`) |
| Missing pytest | Auto-install | Error (must be pre-installed) |

## Preparing for Offline Testing

### Method 1: Persistent Virtual Environment

Best for: Personal development machines

```bash
# One-time setup (with network)
./setup_test_env.sh

# Use indefinitely (no network needed)
./tests/run_tests_fixed.sh --offline
```

The virtual environment at `cell0/venv` or `.venv` persists between runs.

### Method 2: Local Wheels Cache

Best for: CI/CD, shared environments, air-gapped systems

```bash
# Create wheels directory
mkdir -p tests/wheels

# Download wheels (on machine with network)
pip download pytest pytest-asyncio -d tests/wheels/
pip download -r requirements.txt -d tests/wheels/
pip download -r requirements-test.txt -d tests/wheels/

# Copy to offline machine and install from wheels
./setup_test_env.sh -n
```

### Method 3: Bundle Everything

Best for: Distribution, releases, embedded systems

```bash
# Create complete offline bundle
mkdir -p offline_bundle
cp -r cell0 tests offline_bundle/
cp setup_test_env.sh requirements*.txt offline_bundle/

# In offline environment
cd offline_bundle
./setup_test_env.sh --use-system-pytest
```

## Script Reference

### setup_test_env.sh

Sets up the test environment.

```bash
# Standard setup (requires network for first run)
./setup_test_env.sh

# Offline mode - use existing venv or local wheels
./setup_test_env.sh -n
./setup_test_env.sh --no-network

# Force recreate environment
./setup_test_env.sh -f
./setup_test_env.sh --force

# Use system pytest as fallback
./setup_test_env.sh --use-system-pytest
```

**Exit Codes:**
- `0` - Success (environment ready)
- `1` - Fatal error (Python missing, can't create venv)
- **Note:** Missing pytest is NOT a fatal error (just a warning)

### run_tests_fixed.sh

Runs the test suite.

```bash
# Run all tests (requires activated venv with pytest)
./tests/run_tests_fixed.sh

# Offline mode
./tests/run_tests_fixed.sh --offline

# Bootstrap mode (create venv + install + run)
./tests/run_tests_fixed.sh --bootstrap

# Use system Python (no venv)
./tests/run_tests_fixed.sh --offline --use-system-python

# Additional options
./tests/run_tests_fixed.sh -c                    # With coverage
./tests/run_tests_fixed.sh -v                    # Verbose
./tests/run_tests_fixed.sh -f                    # Fast (skip slow tests)
./tests/run_tests_fixed.sh -m unit               # Run unit tests only
./tests/run_tests_fixed.sh -p tests/unit         # Specific path
./tests/run_tests_fixed.sh --ci                  # CI mode (strict, coverage, junit)
```

**Exit Codes:**
- `0` - All tests passed
- `1` - Setup error
- `2+` - Test failures (pytest exit code)

## Troubleshooting

### "pytest not found"

**Problem:** Virtual environment exists but pytest isn't installed.

**Solutions:**

```bash
# Option 1: Activate and install manually
source .venv/bin/activate
pip install pytest pytest-asyncio

# Option 2: Recreate with bootstrap
./tests/run_tests_fixed.sh --bootstrap

# Option 3: Use system Python
pip install pytest  # system-wide
./tests/run_tests_fixed.sh --offline --use-system-python
```

### "No virtual environment found"

**Problem:** First run without existing venv.

**Solution:**

```bash
./setup_test_env.sh        # Create venv (needs network once)
# or
./tests/run_tests_fixed.sh --bootstrap  # Create and run
```

### Import Errors During Tests

**Problem:** Python can't find `col`, `engine`, `service`, or `cell0` modules.

**Solutions:**

```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="$(pwd):$PYTHONPATH"
./tests/run_tests_fixed.sh --offline

# Or skip import check
./tests/run_tests_fixed.sh --offline --skip-import-check
```

### Network Tests Failing in Offline Mode

**Expected behavior:** Network tests are automatically skipped in offline mode using the `-m 'not network'` marker.

If you see network errors, the test may not be properly marked:

```python
@pytest.mark.network  # Add this marker to network tests
def test_api_call():
    ...
```

## CI/CD Integration

### GitHub Actions (with caching)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Cache virtualenv
        uses: actions/cache@v3
        with:
          path: |
            .venv
            cell0/venv
          key: venv-${{ runner.os }}-${{ hashFiles('requirements*.txt') }}
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Setup environment
        run: ./setup_test_env.sh -n || ./setup_test_env.sh
      
      - name: Run tests (offline)
        run: ./tests/run_tests_fixed.sh --offline --ci
```

### GitLab CI

```yaml
test:
  image: python:3.11-slim
  cache:
    paths:
      - .venv/
  script:
    - ./setup_test_env.sh -n || ./setup_test_env.sh
    - ./tests/run_tests_fixed.sh --offline --ci
```

### Docker (Fully Offline)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

# Pre-install dependencies in image
RUN ./setup_test_env.sh

# Runtime uses offline mode
CMD ["./tests/run_tests_fixed.sh", "--offline"]
```

## Testing the Offline Setup

To verify offline mode works:

```bash
# 1. Disconnect from network (or use unshare)
# Linux: sudo unshare -n
# macOS: Disable Wi-Fi temporarily

# 2. Clear any existing venv
rm -rf .venv cell0/venv

# 3. Try to run tests (should fail gracefully)
./tests/run_tests_fixed.sh --offline 2>&1 | grep "pytest not available"

# 4. Setup environment (should warn but not fail)
./setup_test_env.sh -n

# 5. Create a minimal venv and manually install pytest
python3 -m venv .venv
source .venv/bin/activate
pip install pytest  # Needs network once

# 6. Now offline mode should work
./tests/run_tests_fixed.sh --offline
```

## Architecture Notes

### Why Not Bundle Pytest?

We don't bundle pytest wheels in the repo because:

1. **Platform-specific:** Wheels are OS/Python version specific
2. **Size:** ~50MB+ of dependencies
3. **Security:** Bundled dependencies get stale
4. **Flexibility:** Users may need specific pytest versions

Instead, we use a **detection-first** approach that works with whatever pytest is available.

### Graceful Degradation

Both scripts follow the principle of **graceful degradation**:

| Issue | Response |
|-------|----------|
| No venv | Create one (or use system Python) |
| No pytest | Warn, don't fail (in setup) |
| Import errors | Warn, continue testing |
| Network unavailable | Skip network tests |
| Partial dependencies | Run tests that can run |

This ensures you always get the maximum possible test coverage given the environment constraints.

## See Also

- `TEST_FIXES.md` - Recent changes to test infrastructure
- `TEST_BOOTSTRAP_SUMMARY.md` - Bootstrap process documentation
- `pyproject.toml` - Pytest configuration and markers
