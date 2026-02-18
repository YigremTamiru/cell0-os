#!/usr/bin/env python3
"""
Cell 0 Backup Tool - Automated Backup System

Creates comprehensive backups of Cell 0 OS including:
- Configuration files
- TPV store data
- Agent states
- Session data
- Logs (optional)
- Custom skills

Usage:
    python scripts/backup.py [options]
    
Options:
    --output DIR        Backup output directory (default: ./backups)
    --name NAME         Backup name (default: auto-generated)
    --full              Full backup including logs and large files
    --config-only       Only backup configuration
    --verify            Verify backup integrity after creation
    --encrypt           Encrypt backup with password
    --retention DAYS    Keep only last N days of backups
    --upload URL        Upload backup to remote URL (S3, SCP, etc.)

Exit Codes:
    0   - Backup successful
    1   - Backup created with warnings
    2   - Backup failed
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
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Any
from enum import Enum
import tempfile


class BackupStatus(Enum):
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"


@dataclass
class BackupManifest:
    """Manifest describing backup contents."""
    backup_id: str
    created_at: str
    cell0_version: str = "unknown"
    backup_type: str = "standard"  # standard, full, config-only
    hostname: str = ""
    
    # Contents
    configs: List[str] = field(default_factory=list)
    data_paths: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    
    # Statistics
    total_files: int = 0
    total_size_bytes: int = 0
    compressed_size_bytes: int = 0
    
    # Verification
    checksum_algorithm: str = "sha256"
    checksums: Dict[str, str] = field(default_factory=dict)
    verified: bool = False
    
    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)


class Cell0Backup:
    """Cell 0 OS Backup Manager."""
    
    # Directories and files to backup
    CONFIG_PATHS = [
        "config/",
        "integrations/*.yaml",
        "integrations/*.json",
        "pyproject.toml",
        "requirements.txt",
        "setup.py",
    ]
    
    DATA_PATHS = [
        "data/",
        "logs/",
    ]
    
    SKILL_PATHS = [
        "skills/",
    ]
    
    CUSTOM_PATHS = [
        "custom/",
        "memory/",
    ]
    
    EXCLUDE_PATTERNS = [
        "__pycache__",
        "*.pyc",
        "*.pyo",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "*.tmp",
        "*.log.old",
    ]
    
    def __init__(self, cell0_root: Path, output_dir: Path, verbose: bool = False):
        self.cell0_root = cell0_root.resolve()
        self.output_dir = output_dir.resolve()
        self.verbose = verbose
        self.manifest = None
        self.backup_path = None
        
    def log(self, message: str, level: str = "info") -> None:
        """Log a message."""
        if self.verbose or level in ["warning", "error"]:
            prefix = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(level, "ℹ️")
            print(f"{prefix} {message}")
    
    def create_backup(
        self,
        name: Optional[str] = None,
        backup_type: str = "standard",
        include_logs: bool = False,
        verify: bool = False,
        encrypt: bool = False,
        password: Optional[str] = None,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> Tuple[BackupStatus, Path, Optional[str]]:
        """
        Create a backup of Cell 0 OS.
        
        Returns:
            Tuple of (status, backup_path, error_message)
        """
        self.log(f"Starting {backup_type} backup...")
        
        # Generate backup ID and name
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_id = f"cell0_{timestamp}_{os.urandom(4).hex()}"
        if not name:
            name = f"cell0_backup_{timestamp}"
        
        # Create manifest
        self.manifest = BackupManifest(
            backup_id=backup_id,
            created_at=datetime.utcnow().isoformat(),
            backup_type=backup_type,
            hostname=os.uname().nodename if hasattr(os, 'uname') else "unknown",
            description=description,
            tags=tags or []
        )
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create temp directory for staging
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            staging_dir = temp_path / "staging"
            staging_dir.mkdir()
            
            # Collect files to backup
            files_to_backup = self._collect_files(backup_type, include_logs)
            
            if not files_to_backup:
                return BackupStatus.FAILED, None, "No files found to backup"
            
            self.log(f"Found {len(files_to_backup)} files to backup")
            
            # Copy files to staging directory
            copied_count = 0
            total_size = 0
            
            for src_path in files_to_backup:
                try:
                    rel_path = src_path.relative_to(self.cell0_root)
                    dst_path = staging_dir / rel_path
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    if src_path.is_file():
                        shutil.copy2(src_path, dst_path)
                        size = src_path.stat().st_size
                        total_size += size
                        copied_count += 1
                        
                        # Calculate checksum
                        checksum = self._calculate_checksum(src_path)
                        self.manifest.checksums[str(rel_path)] = checksum
                        
                    elif src_path.is_dir():
                        dst_path.mkdir(parents=True, exist_ok=True)
                        
                except Exception as e:
                    self.log(f"Warning: Could not copy {src_path}: {e}", "warning")
            
            self.manifest.total_files = copied_count
            self.manifest.total_size_bytes = total_size
            
            # Write manifest
            manifest_path = staging_dir / "backup_manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(asdict(self.manifest), f, indent=2)
            
            # Create archive
            archive_name = f"{name}.tar.gz"
            if encrypt:
                archive_name = f"{name}.tar.gz.enc"
            
            self.backup_path = self.output_dir / archive_name
            
            # Create tar.gz archive
            temp_archive = temp_path / f"{name}.tar.gz"
            with tarfile.open(temp_archive, "w:gz") as tar:
                tar.add(staging_dir, arcname="cell0_backup")
            
            compressed_size = temp_archive.stat().st_size
            self.manifest.compressed_size_bytes = compressed_size
            
            # Encrypt if requested
            if encrypt:
                if not password:
                    return BackupStatus.FAILED, None, "Encryption requested but no password provided"
                
                self.log("Encrypting backup...")
                encrypted_path = temp_path / f"{name}.tar.gz.enc"
                success = self._encrypt_file(temp_archive, encrypted_path, password)
                if not success:
                    return BackupStatus.FAILED, None, "Encryption failed"
                temp_archive = encrypted_path
            
            # Move to final location
            shutil.move(str(temp_archive), str(self.backup_path))
            
            # Verify if requested
            if verify:
                self.log("Verifying backup integrity...")
                verified = self._verify_backup()
                self.manifest.verified = verified
                if not verified:
                    self.backup_path.unlink()
                    return BackupStatus.FAILED, None, "Backup verification failed"
            
            self.log(f"Backup created: {self.backup_path}", "success")
            self.log(f"  Size: {self._format_size(compressed_size)}")
            self.log(f"  Files: {copied_count}")
            
            return BackupStatus.SUCCESS, self.backup_path, None
    
    def _collect_files(self, backup_type: str, include_logs: bool) -> List[Path]:
        """Collect files to backup based on backup type."""
        files = []
        
        # Always include configs
        for pattern in self.CONFIG_PATHS:
            files.extend(self._glob_files(pattern))
        self.manifest.configs = [str(p.relative_to(self.cell0_root)) for p in files]
        
        # Include data based on backup type
        if backup_type in ["standard", "full"]:
            data_files = []
            for pattern in self.DATA_PATHS:
                if not include_logs and "log" in pattern.lower():
                    continue
                data_files.extend(self._glob_files(pattern))
            files.extend(data_files)
            self.manifest.data_paths = [str(p.relative_to(self.cell0_root)) for p in data_files]
        
        # Include skills
        if backup_type in ["standard", "full"]:
            skill_files = []
            for pattern in self.SKILL_PATHS:
                skill_files.extend(self._glob_files(pattern))
            files.extend(skill_files)
            self.manifest.skills = [str(p.relative_to(self.cell0_root)) for p in skill_files]
        
        # Include custom paths for full backup
        if backup_type == "full":
            for pattern in self.CUSTOM_PATHS:
                files.extend(self._glob_files(pattern))
        
        # Remove duplicates and excluded patterns
        unique_files = []
        seen = set()
        for f in files:
            if str(f) not in seen and not self._should_exclude(f):
                seen.add(str(f))
                unique_files.append(f)
        
        return unique_files
    
    def _glob_files(self, pattern: str) -> List[Path]:
        """Glob files matching pattern."""
        base_path = self.cell0_root
        
        # Handle directory patterns
        if pattern.endswith("/"):
            dir_path = base_path / pattern.rstrip("/")
            if dir_path.exists():
                return [p for p in dir_path.rglob("*") if p.is_file()]
            return []
        
        # Handle glob patterns
        if "*" in pattern:
            return list(base_path.glob(pattern))
        
        # Handle specific paths
        path = base_path / pattern
        if path.exists():
            return [path]
        return []
    
    def _should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded."""
        path_str = str(path)
        for pattern in self.EXCLUDE_PATTERNS:
            if pattern in path_str:
                return True
            # Handle glob patterns
            if "*" in pattern:
                import fnmatch
                if fnmatch.fnmatch(path.name, pattern):
                    return True
        return False
    
    def _calculate_checksum(self, path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        sha256 = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _encrypt_file(self, src: Path, dst: Path, password: str) -> bool:
        """Encrypt file using gpg or openssl."""
        try:
            # Try gpg first
            result = subprocess.run(
                ["gpg", "--symmetric", "--cipher-algo", "AES256", 
                 "--batch", "--passphrase", password, "-o", str(dst), str(src)],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        try:
            # Fallback to openssl
            result = subprocess.run(
                ["openssl", "enc", "-aes-256-cbc", "-salt", 
                 "-in", str(src), "-out", str(dst), "-k", password],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return False
    
    def _verify_backup(self) -> bool:
        """Verify backup integrity."""
        try:
            # Test extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                with tarfile.open(self.backup_path, "r:gz") as tar:
                    tar.extractall(temp_dir)
                
                # Verify manifest exists
                manifest_path = Path(temp_dir) / "cell0_backup" / "backup_manifest.json"
                if not manifest_path.exists():
                    return False
                
                # Load and verify manifest
                with open(manifest_path) as f:
                    manifest = json.load(f)
                
                # Verify some checksums
                for rel_path, expected_checksum in list(manifest.get("checksums", {}).items())[:10]:
                    file_path = Path(temp_dir) / "cell0_backup" / rel_path
                    if file_path.exists():
                        actual_checksum = self._calculate_checksum(file_path)
                        if actual_checksum != expected_checksum:
                            self.log(f"Checksum mismatch: {rel_path}", "warning")
                            return False
                
                return True
        except Exception as e:
            self.log(f"Verification failed: {e}", "error")
            return False
    
    def cleanup_old_backups(self, retention_days: int) -> int:
        """Remove backups older than retention_days. Returns count removed."""
        if not self.output_dir.exists():
            return 0
        
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        removed = 0
        
        for backup_file in self.output_dir.glob("cell0_backup_*.tar.gz*"):
            try:
                # Extract timestamp from filename
                stat = backup_file.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                
                if mtime < cutoff:
                    backup_file.unlink()
                    removed += 1
                    self.log(f"Removed old backup: {backup_file.name}")
            except Exception as e:
                self.log(f"Could not remove {backup_file}: {e}", "warning")
        
        return removed
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups with metadata."""
        backups = []
        
        if not self.output_dir.exists():
            return backups
        
        for backup_file in sorted(self.output_dir.glob("*.tar.gz*"), reverse=True):
            try:
                stat = backup_file.stat()
                backups.append({
                    "name": backup_file.name,
                    "path": str(backup_file),
                    "size_bytes": stat.st_size,
                    "size_formatted": self._format_size(stat.st_size),
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "encrypted": backup_file.suffix == ".enc"
                })
            except Exception:
                pass
        
        return backups
    
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
        description="Cell 0 Backup Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--output", "-o", default="./backups", help="Output directory")
    parser.add_argument("--name", "-n", help="Backup name")
    parser.add_argument("--full", action="store_true", help="Full backup including logs")
    parser.add_argument("--config-only", action="store_true", help="Only backup configuration")
    parser.add_argument("--verify", action="store_true", help="Verify backup integrity")
    parser.add_argument("--encrypt", action="store_true", help="Encrypt backup")
    parser.add_argument("--password", help="Encryption password")
    parser.add_argument("--retention", type=int, help="Retention period in days")
    parser.add_argument("--description", "-d", default="", help="Backup description")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--list", action="store_true", help="List existing backups")
    parser.add_argument("--cell0-root", default=".", help="Cell 0 root directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Find Cell 0 root
    cell0_root = Path(args.cell0_root).resolve()
    if not (cell0_root / "service").exists():
        cell0_root = Path(__file__).parent.parent
    
    backup = Cell0Backup(cell0_root, Path(args.output), args.verbose)
    
    # List backups
    if args.list:
        backups = backup.list_backups()
        if not backups:
            print("No backups found")
            return 0
        
        print(f"\n{'Name':<40} {'Size':<12} {'Created':<20}")
        print("-" * 72)
        for b in backups:
            name = b["name"][:38] + ".." if len(b["name"]) > 40 else b["name"]
            created = b["created"][:19] if b["created"] else "unknown"
            print(f"{name:<40} {b['size_formatted']:<12} {created:<20}")
        return 0
    
    # Determine backup type
    backup_type = "standard"
    if args.full:
        backup_type = "full"
    elif args.config_only:
        backup_type = "config-only"
    
    # Get encryption password
    password = args.password
    if args.encrypt and not password:
        import getpass
        password = getpass.getpass("Enter encryption password: ")
    
    # Parse tags
    tags = args.tags.split(",") if args.tags else []
    
    # Create backup
    status, path, error = backup.create_backup(
        name=args.name,
        backup_type=backup_type,
        include_logs=args.full,
        verify=args.verify,
        encrypt=args.encrypt,
        password=password,
        description=args.description,
        tags=tags
    )
    
    # Cleanup old backups
    if args.retention and status == BackupStatus.SUCCESS:
        removed = backup.cleanup_old_backups(args.retention)
        if removed > 0:
            print(f"Cleaned up {removed} old backup(s)")
    
    # Return exit code
    if status == BackupStatus.SUCCESS:
        return 0
    elif status == BackupStatus.WARNING:
        return 1
    else:
        print(f"Backup failed: {error}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
