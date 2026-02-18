"""
Apple Notes Skill for Cell 0 OS

Integration with Apple Notes via memo CLI tool.

Usage:
    from skills.apple_notes.apple_notes import AppleNotesSkill
    
    skill = AppleNotesSkill()
    notes = skill.list_notes()
    
Or use the agent tools:
    from skills.apple_notes.tools import list_notes_tool, create_note_tool
    
    result = list_notes_tool()
"""

__version__ = "1.0.0"
__author__ = "Cell 0 OS"

from .apple_notes import (
    AppleNotesSkill,
    Note,
    Folder,
    ExportFormat,
    NoteError,
    NoteNotFoundError,
    FolderNotFoundError,
    MemoNotInstalledError,
    PermissionError,
    get_skill,
    list_all_notes,
    list_all_folders,
    quick_create,
    quick_search
)

from .tools import (
    list_notes_tool,
    list_folders_tool,
    create_note_tool,
    read_note_tool,
    update_note_tool,
    search_notes_tool,
    move_note_tool,
    export_notes_tool,
    delete_note_tool,
    create_folder_tool,
    delete_folder_tool,
    get_stats_tool,
    execute_tool,
    get_available_tools,
    TOOL_REGISTRY
)

__all__ = [
    # Main skill
    "AppleNotesSkill",
    "Note",
    "Folder",
    "ExportFormat",
    # Exceptions
    "NoteError",
    "NoteNotFoundError",
    "FolderNotFoundError",
    "MemoNotInstalledError",
    "PermissionError",
    # Convenience functions
    "get_skill",
    "list_all_notes",
    "list_all_folders",
    "quick_create",
    "quick_search",
    # Tools
    "list_notes_tool",
    "list_folders_tool",
    "create_note_tool",
    "read_note_tool",
    "update_note_tool",
    "search_notes_tool",
    "move_note_tool",
    "export_notes_tool",
    "delete_note_tool",
    "create_folder_tool",
    "delete_folder_tool",
    "get_stats_tool",
    "execute_tool",
    "get_available_tools",
    "TOOL_REGISTRY"
]
