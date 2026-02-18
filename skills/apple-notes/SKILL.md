---
name: apple-notes
description: Manage Apple Notes via the memo CLI tool. Create, read, update, search, move, and export notes and folders on macOS.
homepage: https://github.com/antoniorodr/memo
metadata: {"clawdbot":{"emoji":"📝","requires":{"bins":["memo"],"os":["macos"]},"install":[{"id":"brew","kind":"brew","tap":"antoniorodr/memo","formula":"antoniorodr/memo/memo","bins":["memo"],"label":"Install memo CLI via Homebrew"},{"id":"pip","kind":"pip","package":"memo","label":"Install memo CLI via pip"}]}}
---

# Apple Notes Skill

Manage your Apple Notes from Cell 0 OS using the memo CLI tool.

## Capabilities

- ✅ List notes and folders
- ✅ Create new notes
- ✅ Read note content
- ✅ Update existing notes
- ✅ Search notes (fuzzy search)
- ✅ Move notes between folders
- ✅ Export notes to HTML/Markdown
- ✅ Delete notes and folders

## Prerequisites

- macOS 10.15 or later
- Apple Notes app
- memo CLI installed
- `$EDITOR` environment variable set

## Installation

### Option 1: Homebrew (Recommended)

```bash
brew tap antoniorodr/memo
brew install antoniorodr/memo/memo
```

### Option 2: pip

```bash
git clone https://github.com/antoniorodr/memo.git
cd memo
pip install .
```

### Option 3: pipx (Isolated)

```bash
pipx install git+https://github.com/antoniorodr/memo.git
```

## Configuration

Set your preferred editor for editing notes:

```bash
export EDITOR="vim"  # or nano, code, etc.
# Add to ~/.zshrc or ~/.bashrc to make permanent
```

Verify installation:

```bash
memo --version
memo --help
```

## Usage

### Python API

```python
from skills.apple_notes.apple_notes import AppleNotesSkill

skill = AppleNotesSkill()

# List all notes
notes = skill.list_notes()
for note in notes:
    print(note.title)

# Create a note
skill.create_note("Meeting Notes", "Discussed project timeline...", folder="Work")

# Search notes
results = skill.search_notes("meeting")

# Export notes
skill.export_notes(folder="Work", format=ExportFormat.MARKDOWN)
```

### Agent Tools

```python
from skills.apple_notes.tools import (
    list_notes_tool,
    create_note_tool,
    search_notes_tool
)

# List notes
result = list_notes_tool(folder="Work")
print(result["data"])

# Create note
result = create_note_tool(
    title="New Note",
    content="Note content here",
    folder="Personal"
)

# Search
result = search_notes_tool("project")
```

### CLI Usage (memo directly)

```bash
# List all notes
memo notes

# List notes in folder
memo notes --folder "Work"

# List folders
memo notes --flist

# Create note
memo notes --add --folder "Work"

# Edit note
memo notes --edit --folder "Work"

# Search
memo notes --search "keyword"

# Export
memo notes --export

# Move note
memo notes --move --folder "Source"
```

## Tool Registry

The following tools are available for agent use:

| Tool | Description |
|------|-------------|
| `apple_notes_list` | List all notes or notes in a folder |
| `apple_notes_list_folders` | List all folders |
| `apple_notes_create` | Create a new note |
| `apple_notes_read` | Read note content |
| `apple_notes_update` | Update an existing note |
| `apple_notes_search` | Search notes |
| `apple_notes_move` | Move note to different folder |
| `apple_notes_export` | Export notes to file |
| `apple_notes_delete` | Delete a note |
| `apple_notes_create_folder` | Create a new folder |
| `apple_notes_delete_folder` | Delete a folder |
| `apple_notes_stats` | Get note/folder statistics |

## File Structure

```
skills/apple-notes/
├── __init__.py          # Package initialization
├── skill.yaml           # Skill manifest
├── SKILL.md             # This file
├── apple_notes.py       # Main skill implementation
└── tools.py             # Agent tools

tests/
└── test_skill_apple_notes.py  # Unit tests
```

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/test_skill_apple_notes.py -v

# Run without integration tests
SKIP_INTEGRATION_TESTS=1 python tests/test_skill_apple_notes.py
```

## Troubleshooting

### Permission Denied
- Ensure Apple Notes has automation permissions
- Check System Preferences > Security & Privacy > Privacy > Automation

### Editor Not Opening
- Verify `$EDITOR` environment variable is set
- Example: `export EDITOR="vim"`

### Notes Not Appearing
- Ensure Notes app is not locked
- Try unlocking Notes app first

### Export Fails
- Check Desktop folder permissions
- Ensure sufficient disk space

## Limitations

- Images/attachments cannot be edited via memo
- Some rich formatting may be lost during export
- Requires Notes app to be accessible
- Folder creation uses placeholder notes (memo limitation)

## References

- memo CLI: https://github.com/antoniorodr/memo
- Apple Notes: https://support.apple.com/notes

## License

MIT License - Part of Cell 0 OS
