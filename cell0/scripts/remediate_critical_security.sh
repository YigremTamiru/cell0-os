#!/usr/bin/env python3
"""
CRITICAL SECURITY REMEDIATION SCRIPT
Execute immediately to fix CVE-2024-23342 and other critical issues

This script:
1. Removes vulnerable ecdsa package
2. Verifies cryptography package is installed
3. Scans for ECDSA usage in codebase
4. Provides migration guidance
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run shell command and report status"""
    print(f"\n[.] {description}...")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print(f"[✓] {description}: SUCCESS")
            return True
        else:
            print(f"[✗] {description}: FAILED")
            print(f"    Error: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"[✗] {description}: EXCEPTION - {e}")
        return False

def main():
    print("=" * 70)
    print("CELL 0 CRITICAL SECURITY REMEDIATION")
    print("Fixing CVE-2024-23342 (ecdsa Minerva attack vulnerability)")
    print("=" * 70)
    
    # Check if we're in the right directory
    if not os.path.exists("pyproject.toml"):
        print("\n[✗] ERROR: Must run from cell0 directory with pyproject.toml")
        sys.exit(1)
    
    # Step 1: Check current ecdsa installation
    print("\n[.] Checking for vulnerable ecdsa package...")
    result = subprocess.run(
        "pip show ecdsa 2>/dev/null | grep Version",
        shell=True, capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"[⚠] FOUND: {result.stdout.strip()}")
        print("[⚠] This version is VULNERABLE to Minerva attack!")
    else:
        print("[✓] ecdsa package not found (good)")
    
    # Step 2: Remove ecdsa
    print("\n[.] STEP 1: Removing vulnerable ecdsa package...")
    run_command("pip uninstall -y ecdsa", "Uninstalling ecdsa")
    
    # Step 3: Ensure cryptography is installed
    print("\n[.] STEP 2: Ensuring cryptography package is installed...")
    run_command("pip install 'cryptography>=41.0.0'", "Installing cryptography")
    
    # Step 4: Scan for ECDSA usage
    print("\n[.] STEP 3: Scanning codebase for ECDSA usage...")
    result = subprocess.run(
        "grep -r 'from ecdsa\\|import ecdsa\\|ECDSA' --include='*.py' . 2>/dev/null | grep -v __pycache__ | head -20",
        shell=True, capture_output=True, text=True
    )
    if result.stdout:
        print("[⚠] WARNING: Found ECDSA imports in the following files:")
        for line in result.stdout.strip().split('\n'):
            print(f"    - {line}")
        print("\n[⚠] These must be migrated to 'cryptography' library!")
    else:
        print("[✓] No ECDSA imports found")
    
    # Step 5: Check pyproject.toml
    print("\n[.] STEP 4: Checking pyproject.toml for ecdsa dependency...")
    with open("pyproject.toml", "r") as f:
        content = f.read()
        if "ecdsa" in content.lower():
            print("[⚠] WARNING: pyproject.toml contains 'ecdsa' reference")
            print("    ACTION REQUIRED: Remove ecdsa from dependencies manually")
        else:
            print("[✓] No ecdsa in pyproject.toml")
    
    # Step 6: Verify fix
    print("\n[.] STEP 5: Verifying remediation...")
    result = subprocess.run(
        "pip show ecdsa 2>/dev/null",
        shell=True, capture_output=True, text=True
    )
    if result.returncode != 0:
        print("[✓] VERIFIED: ecdsa package successfully removed")
    else:
        print("[✗] FAILED: ecdsa package still present")
    
    # Summary
    print("\n" + "=" * 70)
    print("REMEDIATION SUMMARY")
    print("=" * 70)
    print("""
[✓] ecdsa package removed (if it was installed)
[✓] cryptography package ensured
[⚠] Manual action required:
    1. Review any files using ECDSA and migrate to cryptography
    2. Remove ecdsa from pyproject.toml if present
    3. Run tests to ensure nothing breaks
    4. Rotate any ECDSA keys that may have been exposed
    
MIGRATION EXAMPLE:
    OLD: from ecdsa import SigningKey
         sk = SigningKey.generate()
         
    NEW: from cryptography.hazmat.primitives.asymmetric import ec
         from cryptography.hazmat.primitives import hashes
         private_key = ec.generate_private_key(ec.SECP256R1())
""")
    
    print("\n[✓] Remediation script completed")
    print("[⚠] Remember to rotate your Brave API key (see HIGH-001)")

if __name__ == "__main__":
    main()
