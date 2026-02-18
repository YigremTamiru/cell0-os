#!/usr/bin/env python3
"""
Agent Tools for Apple Notes Skill

This module provides tool functions designed for agent/LLM consumption.
These tools wrap the main AppleNotesSkill with simpler interfaces suitable
for agent tool calling.

Each tool returns a standardized response format:
{
    "success": bool,
    "data": Any,
    "error": Optional[str],
    "message": Optional[str]
}

Author: Cell 0 OS
Version: 1.0.0
"""

import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import asdict

# Import from main skill module
from apple_notes import (
    AppleNotesSkill,
    Note,
    Folder,
    ExportFormat,
    NoteError,
    NoteNotFoundError,
    FolderNotFoundError,
    MemoNotInstalledError,
    PermissionError
)


# Response format helpers
def success_response(data: Any, message: str = "") -> Dict[str, Any]:
    """Create a successful response"""
    return {
        "success": True,
        "data": data,
        "error": None,
        "message": message
    }


def error_response(error: str, message: str = "") -> Dict[str, Any]:
    """Create an error response"""
    return {
        "success": False,
        "data": None,
        "error": error,
        "message": message
    }


# Tool functions for agents

def list_notes_tool(folder: Optional[str] = None) -> Dict[str, Any]:
    """
    Tool: List all notes or notes in a specific folder
    
    Args:
        folder: Optional folder name to filter notes
        
    Returns:
        Response with list of notes
    """
    try:
        skill = AppleNotesSkill()
        notes = skill.list_notes(folder=folder)
        
        notes_data = [note.to_dict() for note in notes]
        
        folder_info = f" in folder '{folder}'" if folder else ""
        return success_response(
            data=notes_data,
            message=f"Found {len(notes)} notes{folder_info}"
        )
    except Exception as e:
        return error_response(str(e))


def list_folders_tool() -> Dict[str, Any]:
    """
    Tool: List all folders and subfolders
    
    Returns:
        Response with list of folders
    """
    try:
        skill = AppleNotesSkill()
        folders = skill.list_folders()
        
        folders_data = [folder.to_dict() for folder in folders]
        
        return success_response(
            data=folders_data,
            message=f"Found {len(folders)} folders"
        )
    except Exception as e:
        return error_response(str(e))


def create_note_tool(
    title: str,
    content: str,
    folder: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tool: Create a new note
    
    Args:
        title: Title of the note
        content: Content of the note
        folder: Optional folder to create note in
        
    Returns:
        Response with created note
    """
    try:
        skill = AppleNotesSkill()
        note = skill.create_note(title, content, folder)
        
        return success_response(
            data=note.to_dict(),
            message=f"Created note '{title}'" + (f" in folder '{folder}'" if folder else "")
        )
    except Exception as e:
        return error_response(str(e))


def read_note_tool(title: str, folder: Optional[str] = None) -> Dict[str, Any]:
    """
    Tool: Read a note's content
    
    Args:
        title: Title of the note
        folder: Optional folder containing the note
        
    Returns:
        Response with note content
    """
    try:
        skill = AppleNotesSkill()
        note = skill.read_note(title, folder)
        
        return success_response(
            data=note.to_dict(),
            message=f"Retrieved note '{title}'"
        )
    except NoteNotFoundError:
        return error_response(
            f"Note '{title}' not found" + (f" in folder '{folder}'" if folder else "")
        )
    except Exception as e:
        return error_response(str(e))


def update_note_tool(
    title: str,
    content: str,
    new_title: Optional[str] = None,
    folder: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tool: Update an existing note
    
    Args:
        title: Current title of the note
        content: New content for the note
        new_title: Optional new title
        folder: Optional folder containing the note
        
    Returns:
        Response with updated note
    """
    try:
        skill = AppleNotesSkill()
        note = skill.update_note(title, content, new_title, folder)
        
        final_title = new_title or title
        return success_response(
            data=note.to_dict(),
            message=f"Updated note '{final_title}'"
        )
    except NoteNotFoundError:
        return error_response(f"Note '{title}' not found")
    except Exception as e:
        return error_response(str(e))


def search_notes_tool(query: str) -> Dict[str, Any]:
    """
    Tool: Search notes using fuzzy search
    
    Args:
        query: Search query string
        
    Returns:
        Response with matching notes
    """
    try:
        skill = AppleNotesSkill()
        notes = skill.search_notes(query)
        
        notes_data = [note.to_dict() for note in notes]
        
        return success_response(
            data=notes_data,
            message=f"Found {len(notes)} notes matching '{query}'"
        )
    except Exception as e:
        return error_response(str(e))


def move_note_tool(
    title: str,
    target_folder: str,
    source_folder: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tool: Move a note to a different folder
    
    Args:
        title: Title of the note to move
        target_folder: Destination folder
        source_folder: Optional source folder
        
    Returns:
        Response with moved note
    """
    try:
        skill = AppleNotesSkill()
        note = skill.move_note(title, target_folder, source_folder)
        
        return success_response(
            data=note.to_dict(),
            message=f"Moved note '{title}' to folder '{target_folder}'"
        )
    except NoteNotFoundError:
        source_info = f" in folder '{source_folder}'" if source_folder else ""
        return error_response(f"Note '{title}' not found{source_info}")
    except Exception as e:
        return error_response(str(e))


def export_notes_tool(
    folder: Optional[str] = None,
    format: str = "markdown",
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tool: Export notes to HTML/Markdown format
    
    Args:
        folder: Optional specific folder to export
        format: Export format ('html' or 'markdown')
        output_dir: Optional output directory
        
    Returns:
        Response with export path
    """
    try:
        skill = AppleNotesSkill()
        
        export_format = ExportFormat.HTML if format.lower() == "html" else ExportFormat.MARKDOWN
        export_path = skill.export_notes(folder, export_format, output_dir)
        
        folder_info = f" from folder '{folder}'" if folder else ""
        return success_response(
            data={"export_path": export_path, "format": format},
            message=f"Exported notes{folder_info} to {export_path}"
        )
    except Exception as e:
        return error_response(str(e))


def delete_note_tool(title: str, folder: Optional[str] = None) -> Dict[str, Any]:
    """
    Tool: Delete a note
    
    Args:
        title: Title of the note to delete
        folder: Optional folder containing the note
        
    Returns:
        Response with deletion status
    """
    try:
        skill = AppleNotesSkill()
        success = skill.delete_note(title, folder)
        
        if success:
            return success_response(
                data={"deleted": True},
                message=f"Deleted note '{title}'"
            )
        else:
            return error_response(f"Failed to delete note '{title}'")
    except NoteNotFoundError:
        return error_response(f"Note '{title}' not found")
    except Exception as e:
        return error_response(str(e))


def create_folder_tool(name: str, parent: Optional[str] = None) -> Dict[str, Any]:
    """
    Tool: Create a new folder
    
    Args:
        name: Name of the new folder
        parent: Optional parent folder
        
    Returns:
        Response with created folder
    """
    try:
        skill = AppleNotesSkill()
        folder = skill.create_folder(name, parent)
        
        return success_response(
            data=folder.to_dict(),
            message=f"Created folder '{name}'" + (f" under '{parent}'" if parent else "")
        )
    except Exception as e:
        return error_response(str(e))


def delete_folder_tool(name: str, force: bool = False) -> Dict[str, Any]:
    """
    Tool: Delete a folder
    
    Args:
        name: Name of the folder to delete
        force: Whether to force deletion
        
    Returns:
        Response with deletion status
    """
    try:
        skill = AppleNotesSkill()
        success = skill.delete_folder(name, force)
        
        if success:
            return success_response(
                data={"deleted": True},
                message=f"Deleted folder '{name}'"
            )
        else:
            return error_response(f"Failed to delete folder '{name}'")
    except FolderNotFoundError:
        return error_response(f"Folder '{name}' not found")
    except Exception as e:
        return error_response(str(e))


def get_stats_tool() -> Dict[str, Any]:
    """
    Tool: Get statistics about notes and folders
    
    Returns:
        Response with counts and statistics
    """
    try:
        skill = AppleNotesSkill()
        
        note_count = skill.get_note_count()
        folder_count = skill.get_folder_count()
        
        return success_response(
            data={
                "total_notes": note_count,
                "total_folders": folder_count
            },
            message=f"Statistics: {note_count} notes, {folder_count} folders"
        )
    except Exception as e:
        return error_response(str(e))


# Tool registry for agent discovery
TOOL_REGISTRY = {
    "apple_notes_list": {
        "function": list_notes_tool,
        "description": "List all notes or notes in a specific folder",
        "parameters": {
            "folder": {
                "type": "string",
                "description": "Optional folder name to filter notes",
                "required": False
            }
        }
    },
    "apple_notes_list_folders": {
        "function": list_folders_tool,
        "description": "List all folders and subfolders",
        "parameters": {}
    },
    "apple_notes_create": {
        "function": create_note_tool,
        "description": "Create a new note",
        "parameters": {
            "title": {
                "type": "string",
                "description": "Title of the note",
                "required": True
            },
            "content": {
                "type": "string",
                "description": "Content of the note",
                "required": True
            },
            "folder": {
                "type": "string",
                "description": "Optional folder to create note in",
                "required": False
            }
        }
    },
    "apple_notes_read": {
        "function": read_note_tool,
        "description": "Read a note's content",
        "parameters": {
            "title": {
                "type": "string",
                "description": "Title of the note",
                "required": True
            },
            "folder": {
                "type": "string",
                "description": "Optional folder containing the note",
                "required": False
            }
        }
    },
    "apple_notes_update": {
        "function": update_note_tool,
        "description": "Update an existing note",
        "parameters": {
            "title": {
                "type": "string",
                "description": "Current title of the note",
                "required": True
            },
            "content": {
                "type": "string",
                "description": "New content for the note",
                "required": True
            },
            "new_title": {
                "type": "string",
                "description": "Optional new title",
                "required": False
            },
            "folder": {
                "type": "string",
                "description": "Optional folder containing the note",
                "required": False
            }
        }
    },
    "apple_notes_search": {
        "function": search_notes_tool,
        "description": "Search notes using fuzzy search",
        "parameters": {
            "query": {
                "type": "string",
                "description": "Search query string",
                "required": True
            }
        }
    },
    "apple_notes_move": {
        "function": move_note_tool,
        "description": "Move a note to a different folder",
        "parameters": {
            "title": {
                "type": "string",
                "description": "Title of the note to move",
                "required": True
            },
            "target_folder": {
                "type": "string",
                "description": "Destination folder",
                "required": True
            },
            "source_folder": {
                "type": "string",
                "description": "Optional source folder",
                "required": False
            }
        }
    },
    "apple_notes_export": {
        "function": export_notes_tool,
        "description": "Export notes to HTML/Markdown",
        "parameters": {
            "folder": {
                "type": "string",
                "description": "Optional specific folder to export",
                "required": False
            },
            "format": {
                "type": "string",
                "description": "Export format: 'html' or 'markdown'",
                "required": False
            },
            "output_dir": {
                "type": "string",
                "description": "Optional output directory",
                "required": False
            }
        }
    },
    "apple_notes_delete": {
        "function": delete_note_tool,
        "description": "Delete a note",
        "parameters": {
            "title": {
                "type": "string",
                "description": "Title of the note to delete",
                "required": True
            },
            "folder": {
                "type": "string",
                "description": "Optional folder containing the note",
                "required": False
            }
        }
    },
    "apple_notes_create_folder": {
        "function": create_folder_tool,
        "description": "Create a new folder",
        "parameters": {
            "name": {
                "type": "string",
                "description": "Name of the new folder",
                "required": True
            },
            "parent": {
                "type": "string",
                "description": "Optional parent folder",
                "required": False
            }
        }
    },
    "apple_notes_delete_folder": {
        "function": delete_folder_tool,
        "description": "Delete a folder",
        "parameters": {
            "name": {
                "type": "string",
                "description": "Name of the folder to delete",
                "required": True
            },
            "force": {
                "type": "boolean",
                "description": "Whether to force deletion",
                "required": False
            }
        }
    },
    "apple_notes_stats": {
        "function": get_stats_tool,
        "description": "Get statistics about notes and folders",
        "parameters": {}
    }
}


def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    Execute a tool by name with given parameters
    
    Args:
        tool_name: Name of the tool to execute
        **kwargs: Tool parameters
        
    Returns:
        Tool response
    """
    if tool_name not in TOOL_REGISTRY:
        return error_response(f"Unknown tool: {tool_name}")
    
    tool = TOOL_REGISTRY[tool_name]
    func = tool["function"]
    
    try:
        return func(**kwargs)
    except Exception as e:
        return error_response(f"Tool execution failed: {str(e)}")


def get_available_tools() -> Dict[str, Any]:
    """
    Get list of available tools for agent discovery
    
    Returns:
        Dictionary of available tools
    """
    return {
        name: {
            "description": info["description"],
            "parameters": info["parameters"]
        }
        for name, info in TOOL_REGISTRY.items()
    }


if __name__ == "__main__":
    # Demo tool usage
    print("Apple Notes Agent Tools")
    print("=" * 50)
    
    # Show available tools
    tools = get_available_tools()
    print(f"\nAvailable tools ({len(tools)}):")
    for name, info in tools.items():
        print(f"  • {name}: {info['description']}")
    
    # Demo tool execution
    print("\n" + "=" * 50)
    print("Demo: Getting stats...")
    
    try:
        result = execute_tool("apple_notes_stats")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")
