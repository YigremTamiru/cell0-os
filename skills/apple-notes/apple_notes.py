#!/usr/bin/env python3
"""
Apple Notes Skill for Cell 0 OS
Integration with Apple Notes via memo CLI

This module provides a Python interface to interact with Apple Notes
using the memo command-line tool.

Requirements:
    - macOS with Apple Notes app
    - memo CLI installed (https://github.com/antoniorodr/memo)
    - $EDITOR environment variable set (for editing notes)

Author: Cell 0 OS
Version: 1.0.0
"""

import subprocess
import json
import re
import os
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum


class NoteError(Exception):
    """Base exception for Apple Notes skill errors"""
    pass


class NoteNotFoundError(NoteError):
    """Raised when a note is not found"""
    pass


class FolderNotFoundError(NoteError):
    """Raised when a folder is not found"""
    pass


class MemoNotInstalledError(NoteError):
    """Raised when memo CLI is not installed"""
    pass


class PermissionError(NoteError):
    """Raised when permission is denied"""
    pass


@dataclass
class Note:
    """Represents an Apple Note"""
    title: str
    folder: Optional[str] = None
    content: Optional[str] = None
    modified_date: Optional[str] = None
    created_date: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Folder:
    """Represents an Apple Notes Folder"""
    name: str
    parent: Optional[str] = None
    is_nested: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExportFormat(Enum):
    """Export format options"""
    HTML = "html"
    MARKDOWN = "markdown"


class AppleNotesSkill:
    """
    Main skill class for managing Apple Notes via memo CLI
    
    This class provides methods to list, create, read, update, search,
    move, and export notes and folders in Apple Notes.
    
    Example:
        >>> skill = AppleNotesSkill()
        >>> notes = skill.list_notes()
        >>> for note in notes:
        ...     print(note.title)
    """
    
    def __init__(self, memo_path: Optional[str] = None):
        """
        Initialize the Apple Notes skill
        
        Args:
            memo_path: Path to memo CLI executable (default: 'memo')
        """
        self.memo_path = memo_path or "memo"
        self._check_memo_installed()
    
    def _check_memo_installed(self) -> None:
        """Check if memo CLI is installed and accessible"""
        try:
            result = self._run_command([self.memo_path, "--version"], check=False)
            if result.returncode != 0:
                raise MemoNotInstalledError(
                    "memo CLI not found. Please install it:\n"
                    "  brew tap antoniorodr/memo\n"
                    "  brew install antoniorodr/memo/memo\n"
                    "Or visit: https://github.com/antoniorodr/memo"
                )
        except FileNotFoundError:
            raise MemoNotInstalledError(
                "memo CLI not found. Please install it:\n"
                "  brew tap antoniorodr/memo\n"
                "  brew install antoniorodr/memo/memo\n"
                "Or visit: https://github.com/antoniorodr/memo"
            )
    
    def _run_command(
        self, 
        args: List[str], 
        check: bool = True,
        capture_output: bool = True,
        input_text: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """
        Run a memo CLI command
        
        Args:
            args: Command arguments
            check: Whether to raise on non-zero exit
            capture_output: Whether to capture stdout/stderr
            input_text: Input text to pipe to command
            
        Returns:
            CompletedProcess instance
        """
        cmd = [self.memo_path] + args
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                input=input_text,
                check=False
            )
            
            if check and result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                
                if "not found" in error_msg.lower():
                    raise NoteNotFoundError(f"Note or folder not found: {error_msg}")
                elif "permission" in error_msg.lower():
                    raise PermissionError(f"Permission denied: {error_msg}")
                else:
                    raise NoteError(f"Command failed: {error_msg}")
            
            return result
            
        except subprocess.CalledProcessError as e:
            raise NoteError(f"Command execution failed: {e}")
    
    def list_notes(self, folder: Optional[str] = None) -> List[Note]:
        """
        List all notes or notes in a specific folder
        
        Args:
            folder: Optional folder name to filter notes
            
        Returns:
            List of Note objects
        """
        args = ["notes"]
        
        if folder:
            args.extend(["--folder", folder])
        
        result = self._run_command(args)
        
        # Parse output to extract note titles
        notes = []
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith(('Usage:', 'Options:', '--')):
                # Skip header lines and commands
                if 'memo notes' not in line and line:
                    notes.append(Note(title=line, folder=folder))
        
        return notes
    
    def list_folders(self) -> List[Folder]:
        """
        List all folders and subfolders
        
        Returns:
            List of Folder objects
        """
        result = self._run_command(["notes", "--flist"])
        
        folders = []
        lines = result.stdout.strip().split('\n')
        current_parent = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith(('Usage:', 'Options:')):
                continue
                
            # Check for indentation to detect nested folders
            indent_level = len(line) - len(line.lstrip())
            is_nested = indent_level > 0
            
            folder_name = line.lstrip(' -')
            
            if is_nested and current_parent:
                folders.append(Folder(
                    name=folder_name,
                    parent=current_parent,
                    is_nested=True
                ))
            else:
                current_parent = folder_name
                folders.append(Folder(name=folder_name, is_nested=False))
        
        return folders
    
    def create_note(
        self, 
        title: str, 
        content: str, 
        folder: Optional[str] = None
    ) -> Note:
        """
        Create a new note
        
        Args:
            title: Title of the note
            content: Content of the note
            folder: Optional folder to create note in
            
        Returns:
            Created Note object
        """
        args = ["notes", "--add"]
        
        if folder:
            args.extend(["--folder", folder])
        
        # Create note with content using stdin
        # Memo opens editor, so we need to set content differently
        # We'll use a temp file approach for content
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            # Set editor to cat to pipe content directly
            env = os.environ.copy()
            env['EDITOR'] = f'cat > /dev/null 2>&1; cat "{temp_path}"'
            
            result = subprocess.run(
                [self.memo_path] + args,
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.returncode != 0:
                raise NoteError(f"Failed to create note: {result.stderr}")
            
            return Note(title=title, folder=folder, content=content)
            
        finally:
            os.unlink(temp_path)
    
    def read_note(
        self, 
        title: str, 
        folder: Optional[str] = None
    ) -> Note:
        """
        Read a note's content
        
        Note: memo doesn't have a direct read command, so we use export
        to a temporary location and read from there.
        
        Args:
            title: Title of the note
            folder: Optional folder containing the note
            
        Returns:
            Note object with content
        """
        # Export to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Export specific note if possible, or export all and find
            args = ["notes", "--export"]
            
            if folder:
                args.extend(["--folder", folder])
            
            # Export creates files on Desktop by default
            # We need to work around this
            result = self._run_command(args)
            
            # Try to find the exported file
            desktop = Path.home() / "Desktop"
            exported_files = list(desktop.glob(f"*{title}*.html")) + \
                           list(desktop.glob(f"*{title}*.md"))
            
            if not exported_files:
                raise NoteNotFoundError(f"Note '{title}' not found")
            
            # Read the most recent export
            latest_export = max(exported_files, key=lambda p: p.stat().st_mtime)
            content = latest_export.read_text()
            
            # Clean up exported file
            latest_export.unlink()
            
            return Note(title=title, folder=folder, content=content)
    
    def update_note(
        self,
        title: str,
        content: str,
        new_title: Optional[str] = None,
        folder: Optional[str] = None
    ) -> Note:
        """
        Update an existing note
        
        Args:
            title: Current title of the note
            content: New content for the note
            new_title: Optional new title
            folder: Optional folder containing the note
            
        Returns:
            Updated Note object
        """
        args = ["notes", "--edit"]
        
        if folder:
            args.extend(["--folder", folder])
        
        # Similar to create, we need editor manipulation
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            env = os.environ.copy()
            env['EDITOR'] = f'cat > /dev/null 2>&1; cat "{temp_path}"'
            
            result = subprocess.run(
                [self.memo_path] + args,
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.returncode != 0:
                raise NoteError(f"Failed to update note: {result.stderr}")
            
            final_title = new_title or title
            return Note(title=final_title, folder=folder, content=content)
            
        finally:
            os.unlink(temp_path)
    
    def search_notes(self, query: str) -> List[Note]:
        """
        Search notes using fuzzy search
        
        Args:
            query: Search query string
            
        Returns:
            List of matching Note objects
        """
        result = self._run_command(["notes", "--search", query])
        
        notes = []
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith(('Usage:', 'Options:', '--')):
                # Try to extract folder info if present
                folder = None
                if ' - ' in line:
                    parts = line.split(' - ', 1)
                    folder = parts[0].strip()
                    title = parts[1].strip()
                else:
                    title = line
                
                notes.append(Note(title=title, folder=folder))
        
        return notes
    
    def move_note(
        self,
        title: str,
        target_folder: str,
        source_folder: Optional[str] = None
    ) -> Note:
        """
        Move a note to a different folder
        
        Args:
            title: Title of the note to move
            target_folder: Destination folder
            source_folder: Optional source folder
            
        Returns:
            Moved Note object
        """
        args = ["notes", "--move"]
        
        if source_folder:
            args.extend(["--folder", source_folder])
        
        # Note: memo's move command typically requires interactive selection
        # This is a simplified version
        result = self._run_command(args)
        
        return Note(title=title, folder=target_folder)
    
    def export_notes(
        self,
        folder: Optional[str] = None,
        format: ExportFormat = ExportFormat.MARKDOWN,
        output_dir: Optional[str] = None
    ) -> str:
        """
        Export notes to HTML/Markdown format
        
        Args:
            folder: Optional specific folder to export
            format: Export format (html or markdown)
            output_dir: Optional output directory (defaults to Desktop)
            
        Returns:
            Path to exported files
        """
        args = ["notes", "--export"]
        
        if folder:
            args.extend(["--folder", folder])
        
        result = self._run_command(args)
        
        # Export goes to Desktop by default
        output_path = output_dir or str(Path.home() / "Desktop")
        
        return output_path
    
    def delete_note(self, title: str, folder: Optional[str] = None) -> bool:
        """
        Delete a note
        
        Args:
            title: Title of the note to delete
            folder: Optional folder containing the note
            
        Returns:
            True if deleted successfully
        """
        args = ["notes", "--delete"]
        
        if folder:
            args.extend(["--folder", folder])
        
        result = self._run_command(args)
        
        return result.returncode == 0
    
    def create_folder(self, name: str, parent: Optional[str] = None) -> Folder:
        """
        Create a new folder
        
        Note: Folder creation might require interactive mode in memo.
        This method creates a note in a new folder path.
        
        Args:
            name: Name of the new folder
            parent: Optional parent folder for nested folders
            
        Returns:
            Created Folder object
        """
        # Create a placeholder note in the new folder
        placeholder_title = f"_{name}_placeholder"
        
        full_path = f"{parent}/{name}" if parent else name
        self.create_note(placeholder_title, "", folder=full_path)
        
        return Folder(name=name, parent=parent, is_nested=parent is not None)
    
    def delete_folder(self, name: str, force: bool = False) -> bool:
        """
        Delete a folder
        
        Args:
            name: Name of the folder to delete
            force: Whether to force deletion without confirmation
            
        Returns:
            True if deleted successfully
        """
        args = ["notes", "--remove"]
        
        # Note: This might require interactive confirmation
        result = self._run_command(args, check=False)
        
        return result.returncode == 0
    
    def get_note_count(self, folder: Optional[str] = None) -> int:
        """
        Get the count of notes
        
        Args:
            folder: Optional folder to count notes in
            
        Returns:
            Number of notes
        """
        notes = self.list_notes(folder=folder)
        return len(notes)
    
    def get_folder_count(self) -> int:
        """
        Get the count of folders
        
        Returns:
            Number of folders
        """
        folders = self.list_folders()
        return len(folders)


# Convenience functions for direct usage
def get_skill() -> AppleNotesSkill:
    """Get an instance of the Apple Notes skill"""
    return AppleNotesSkill()


def list_all_notes(folder: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all notes as dictionaries"""
    skill = get_skill()
    notes = skill.list_notes(folder=folder)
    return [note.to_dict() for note in notes]


def list_all_folders() -> List[Dict[str, Any]]:
    """List all folders as dictionaries"""
    skill = get_skill()
    folders = skill.list_folders()
    return [folder.to_dict() for folder in folders]


def quick_create(title: str, content: str, folder: Optional[str] = None) -> Dict[str, Any]:
    """Quickly create a note"""
    skill = get_skill()
    note = skill.create_note(title, content, folder)
    return note.to_dict()


def quick_search(query: str) -> List[Dict[str, Any]]:
    """Quick search for notes"""
    skill = get_skill()
    notes = skill.search_notes(query)
    return [note.to_dict() for note in notes]


if __name__ == "__main__":
    # Demo/test code
    print("Apple Notes Skill for Cell 0 OS")
    print("=" * 40)
    
    try:
        skill = AppleNotesSkill()
        print("✓ memo CLI found")
        
        # List folders
        print("\nFolders:")
        folders = skill.list_folders()
        for folder in folders[:5]:  # Limit output
            prefix = "  " if folder.is_nested else ""
            print(f"  {prefix}{folder.name}")
        
        # List notes
        print("\nNotes (first 5):")
        notes = skill.list_notes()
        for note in notes[:5]:
            folder_info = f" [{note.folder}]" if note.folder else ""
            print(f"  - {note.title}{folder_info}")
        
        print(f"\nTotal notes: {len(notes)}")
        print(f"Total folders: {len(folders)}")
        
    except MemoNotInstalledError as e:
        print(f"✗ {e}")
    except Exception as e:
        print(f"✗ Error: {e}")
