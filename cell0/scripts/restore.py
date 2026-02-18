#!/usr/bin/env python3
"""
Cell 0 Restore Tool - Recovery System

Restores Cell 0 OS from backups created by backup.py.
Supports selective restoration and integrity verification.

Usage:
    python scripts/restore.py BACKUP_FILE [options]
    
Options:
    --target DIR        Target directory (default: current)
    --configs-only      Only restore configuration files
    --data-only         Only restore data files
    --skills-only       Only restore custom skills
    --verify-only       Only verify backup, don't restore
    --force             Overwrite existing files without prompting
    --password          Decryption password (if encrypted)
    --dry-run           Show what would be restored without doing it
    --list              List contents of backup without restoring

Exit Codes:
    0   - Restore successful
    1   - Restore completed with warnings
    2   - Restore failed
"""

import sys
import os
import json
import shutil
import tarfile
import hashlib
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import tempfile


class RestoreStatus(Enum):
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"


class Cell0Restore:
    """Cell 0 OS Restore Manager."""
    
    def __init__(self, backup_path: Path, target_dir: Path, verbose: bool = False, dry_run: bool = False):
        self.backup_path = backup_path.resolve()
        self.target_dir = target_dir.resolve()
        self.verbose = verbose
        self.dry_run = dry_run
        self.manifest = None
        self.temp_dir = None
        
    def log(self, message: str, level: str = "info") -> None:
        """Log a message."""
        if self.verbose or level in ["warning", "error"]:
            prefix = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌", "dry": "🔍"}.get(level, "ℹ️")
            dry_prefix = "[DRY-RUN] " if self.dry_run and level != "dry" else ""
            print(f"{prefix} {dry_prefix}{message}")
    
    def verify_backup(self, password: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Verify backup integrity without extracting.
        
        Returns:
            Tuple of (success, error_message)
        """
        self.log("Verifying backup integrity...")
        
        if not self.backup_path.exists():
            return False, f"Backup file not found: {self.backup_path}"
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Handle encrypted backups
                archive_path = self.backup_path
                if self.backup_path.suffix == ".enc" or str(self.backup_path).endswith(".tar.gz.enc"):
                    if not password:
                        return False, "Backup is encrypted but no password provided"
                    
                    self.log("Decrypting backup...")
                    decrypted_path = temp_path / "backup.tar.gz"
                    success = self._decrypt_file(self.backup_path, decrypted_path, password)
                    if not success:
                        return False, "Decryption failed - wrong password?"
                    archive_path = decrypted_path
                
                # Test archive integrity
                try:
                    with tarfile.open(archive_path, "r:gz") as tar:
                        tar.getmembers()
                except tarfile.TarError as e:
                    return False, f"Archive is corrupted: {e}"
                
                # Extract and verify manifest
                with tarfile.open(archive_path, "r:gz") as tar:
                    manifest_member = None
                    for member in tar.getmembers():
                        if member.name.endswith("backup_manifest.json"):
                            manifest_member = member
                            break
                    
                    if not manifest_member:
                        return False, "Backup manifest not found"
                    
                    tar.extract(manifest_member, temp_path)
                    manifest_path = temp_path / manifest_member.name
                    
                    with open(manifest_path) as f:
                        self.manifest = json.load(f)
                
                # Verify checksums (sample)
                verification_errors = []
                checksums = self.manifest.get("checksums", {})
                
                with tarfile.open(archive_path, "r:gz") as tar:
                    for rel_path, expected_checksum in list(checksums.items())[:20]:
                        member = None
                        for m in tar.getmembers():
                            if m.name.endswith(rel_path):
                                member = m
                                break
                        
                        if member:
                            tar.extract(member, temp_path)
                            extracted_path = temp_path / member.name
                            if extracted_path.exists():
                                actual_checksum = self._calculate_checksum(extracted_path)
                                if actual_checksum != expected_checksum:
                                    verification_errors.append(rel_path)
                
                if verification_errors:
                    return False, f"Checksum verification failed for {len(verification_errors)} file(s)"
                
                self.log("Backup verification successful", "success")
                return True, None
                
        except Exception as e:
            return False, f"Verification failed: {e}"
    
    def restore(
        self,
        configs_only: bool = False,
        data_only: bool = False,
        skills_only: bool = False,
        force: bool = False,
        password: Optional[str] = None
    ) -> Tuple[RestoreStatus, Optional[str]]:
        """
        Restore from backup.
        
        Returns:
            Tuple of (status, error_message)
        """
        self.log(f"Starting restore from: {self.backup_path}")
        
        # Verify first
        success, error = self.verify_backup(password)
        if not success:
            return RestoreStatus.FAILED, error
        
        # Create target directory if needed
        if not self.dry_run:
            self.target_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine what to restore
        restore_configs = configs_only or not (data_only or skills_only)
        restore_data = data_only or not (configs_only or skills_only)
        restore_skills = skills_only or not (configs_only or data_only)
        
        self.log(f"Restore configuration: configs={restore_configs}, data={restore_data}, skills={restore_skills}")
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Handle encrypted backups
                archive_path = self.backup_path
                if self.backup_path.suffix == ".enc" or str(self.backup_path).endswith(".tar.gz.enc"):
                    self.log("Decrypting backup...")
                    decrypted_path = temp_path / "backup.tar.gz"
                    success = self._decrypt_file(self.backup_path, decrypted_path, password)
                    if not success:
                        return RestoreStatus.FAILED, "Decryption failed"
                    archive_path = decrypted_path
                
                # Extract archive
                self.log("Extracting backup...")
                extract_dir = temp_path / "extracted"
                extract_dir.mkdir()
                
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(extract_dir)
                
                # Find the backup contents
                backup_root = extract_dir
                for item in extract_dir.iterdir():
                    if item.is_dir():
                        backup_root = item
                        break
                
                # Perform restoration
                restored_count = 0
                warning_count = 0
                
                if restore_configs:
                    count, warnings = self._restore_category(
                        backup_root, "configs", force
                    )
                    restored_count += count
                    warning_count += warnings
                
                if restore_data:
                    count, warnings = self._restore_category(
                        backup_root, "data", force
                    )
                    restored_count += count
                    warning_count += warnings
                
                if restore_skills:
                    count, warnings = self._restore_category(
                        backup_root, "skills", force
                    )
                    restored_count += count
                    warning_count += warnings
                
                self.log(f"Restored {restored_count} file(s)", "success")
                if warning_count > 0:
                    self.log(f"Warnings: {warning_count}", "warning")
                
                status = RestoreStatus.WARNING if warning_count > 0 else RestoreStatus.SUCCESS
                return status, None
                
        except Exception as e:
            return RestoreStatus.FAILED, f"Restore failed: {e}"
    
    def _restore_category(
        self,
        backup_root: Path,
        category: str,
        force: bool
    ) -> Tuple[int, int]:
        """Restore a category of files. Returns (restored_count, warning_count)."""
        restored = 0
        warnings = 0
        
        # Map category to manifest key
        manifest_key = f"{category}_paths" if category == "data" else category
        paths = self.manifest.get(manifest_key, [])
        
        for rel_path in paths:
            src = backup_root / rel_path
            dst = self.target_dir / rel_path
            
            if not src.exists():
                continue
            
            if src.is_file():
                # Check for conflicts
                if dst.exists() and not force:
                    if not self.dry_run:
                        self.log(f"Skipping existing file: {rel_path}", "warning")
                        warnings += 1
                        continue
                
                if not self.dry_run:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    self.log(f"Restored: {rel_path}")
                else:
                    self.log(f"Would restore: {rel_path}", "dry")
                
                restored += 1
            
            elif src.is_dir():
                # Restore directory contents
                for file_path in src.rglob("*"):
                    if file_path.is_file():
                        rel_file = file_path.relative_to(backup_root)
                        dst_file = self.target_dir / rel_file
                        
                        if dst_file.exists() and not force:
                            if not self.dry_run:
                                warnings += 1
                            continue
                        
                        if not self.dry_run:
                            dst_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(file_path, dst_file)
                        
                        restored += 1
        
        return restored, warnings
    
    def list_contents(self, password: Optional[str] = None) -> bool:
        """List backup contents without restoring."""
        success, error = self.verify_backup(password)
        if not success:
            print(f"Cannot list contents: {error}")
            return False
        
        print("\n" + "=" * 70)
        print("Backup Contents".center(70))
        print("=" * 70)
        print(f"Backup ID: {self.manifest.get('backup_id', 'unknown')}")
        print(f"Created:   {self.manifest.get('created_at', 'unknown')}")
        print(f"Type:      {self.manifest.get('backup_type', 'unknown')}")
        print(f"Hostname:  {self.manifest.get('hostname', 'unknown')}")
        print(f"Files:     {self.manifest.get('total_files', 0)}")
        
        size_bytes = self.manifest.get('total_size_bytes', 0)
        size_formatted = self._format_size(size_bytes)
        print(f"Size:      {size_formatted}")
        
        if self.manifest.get('description'):
            print(f"Description: {self.manifest['description']}")
        
        if self.manifest.get('tags'):
            print(f"Tags:      {', '.join(self.manifest['tags'])}")
        
        print("\n--- Configuration Files ---")
        for path in self.manifest.get('configs', [])[:20]:
            print(f"  {path}")
        if len(self.manifest.get('configs', [])) > 20:
            print(f"  ... and {len(self.manifest['configs']) - 20} more")
        
        print("\n--- Data Files ---")
        for path in self.manifest.get('data_paths', [])[:10]:
            print(f"  {path}")
        if len(self.manifest.get('data_paths', [])) > 10:
            print(f"  ... and {len(self.manifest['data_paths']) - 10} more")
        
        print("\n--- Skills ---")
        for path in self.manifest.get('skills', [])[:10]:
            print(f"  {path}")
        if len(self.manifest.get('skills', [])) > 10:
            print(f"  ... and {len(self.manifest['skills']) - 10} more")
        
        print("=" * 70)
        return True
    
    def _decrypt_file(self, src: Path, dst: Path, password: str) -> bool:
        """Decrypt file using gpg or openssl."""
        # Try gpg first
        try:
            result = subprocess.run(
                ["gpg", "--decrypt", "--batch", "--passphrase", password,
                 "-o", str(dst), str(src)],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Fallback to openssl
        try:
            result = subprocess.run(
                ["openssl", "enc", "-aes-256-cbc", "-d",
                 "-in", str(src), "-out", str(dst), "-k", password],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return False
    
    def _calculate_checksum(self, path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        sha256 = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format byte size to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cell 0 Restore Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("backup", nargs="?", help="Backup file to restore from")
    parser.add_argument("--target", "-t", default=".", help="Target directory")
    parser.add_argument("--configs-only", action="store_true", help="Only restore configs")
    parser.add_argument("--data-only", action="store_true", help="Only restore data")
    parser.add_argument("--skills-only", action="store_true", help="Only restore skills")
    parser.add_argument("--verify-only", action="store_true", help="Only verify backup")
    parser.add_argument("--force", "-f", action="store_true", help="Overwrite existing files")
    parser.add_argument("--password", "-p", help="Decryption password")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Show what would be done")
    parser.add_argument("--list", "-l", action="store_true", help="List backup contents")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.backup and not args.list:
        parser.error("Backup file is required (unless using --list with a backup)")
    
    if args.list and not args.backup:
        # List mode requires backup
        parser.error("Backup file is required for --list")
    
    backup_path = Path(args.backup)
    target_dir = Path(args.target)
    
    restore = Cell0Restore(backup_path, target_dir, args.verbose, args.dry_run)
    
    # List mode
    if args.list:
        password = args.password
        if not password and (backup_path.suffix == ".enc" or str(backup_path).endswith(".tar.gz.enc")):
            import getpass
            password = getpass.getpass("Enter decryption password: ")
        
        success = restore.list_contents(password)
        return 0 if success else 2
    
    # Verify only mode
    if args.verify_only:
        password = args.password
        if not password and (backup_path.suffix == ".enc" or str(backup_path).endswith(".tar.gz.enc")):
            import getpass
            password = getpass.getpass("Enter decryption password: ")
        
        success, error = restore.verify_backup(password)
        if success:
            print("✅ Backup verification successful")
            return 0
        else:
            print(f"❌ Verification failed: {error}")
            return 2
    
    # Get password if needed
    password = args.password
    if not password and (backup_path.suffix == ".enc" or str(backup_path).endswith(".tar.gz.enc")):
        import getpass
        password = getpass.getpass("Enter decryption password: ")
    
    # Perform restore
    status, error = restore.restore(
        configs_only=args.configs_only,
        data_only=args.data_only,
        skills_only=args.skills_only,
        force=args.force,
        password=password
    )
    
    if status == RestoreStatus.SUCCESS:
        print("\n✅ Restore completed successfully")
        return 0
    elif status == RestoreStatus.WARNING:
        print("\n⚠️  Restore completed with warnings")
        return 1
    else:
        print(f"\n❌ Restore failed: {error}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
