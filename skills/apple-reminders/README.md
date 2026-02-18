# Apple Reminders Skill for Cell 0 OS

✅ **Integration with Apple Reminders via remindctl CLI**

## Overview

This skill provides comprehensive management of Apple Reminders through the command-line interface, enabling AI agents to:

- List reminders and reminder lists
- Create, edit, and delete reminders
- Mark reminders as complete
- Manage reminder lists (create, rename, delete)
- Query reminders by date, status, and priority

## Requirements

- macOS 14+ (Sonoma or later)
- [remindctl](https://github.com/steipete/remindctl) CLI tool
- Python 3.8+
- Apple Reminders permission

## Installation

### 1. Install remindctl

```bash
# Using Homebrew (recommended)
brew install steipete/tap/remindctl

# Or build from source
git clone https://github.com/steipete/remindctl.git
cd remindctl
pnpm install
pnpm build
sudo mv ./bin/remindctl /usr/local/bin/
```

### 2. Grant Permissions

```bash
# Trigger permission prompt
remindctl authorize
```

Or manually enable in:  
**System Settings → Privacy & Security → Reminders → Terminal**

### 3. Verify Installation

```bash
remindctl status
remindctl --help
```

## Quick Start

### Using the Skill Class

```python
from skills.apple_reminders import AppleRemindersSkill

skill = AppleRemindersSkill()

# List all lists
lists = skill.list_reminder_lists()

# Get today's reminders
today = skill.list_reminders(filter_type="today")

# Create a reminder
reminder = skill.create_reminder(
    title="Buy groceries",
    list_name="Personal",
    due_date="tomorrow",
    priority="high"
)

# Complete a reminder
skill.complete_reminder(reminder['id'])
```

### Using the Tools (for Agents)

```python
from skills.apple_reminders.tools import (
    get_today, create, complete, get_lists,
    get_overdue, search, summary
)

# Get formatted today's tasks
print(get_today())

# Create a task with natural language
result = create(
    title="Call mom",
    when="tomorrow at 3pm",
    priority="medium"
)
print(result)

# Complete a task
print(complete("task-id"))

# Search tasks
print(search("meeting"))

# Get summary
print(summary())
```

## Features

### Reminder Operations

| Operation | Method | Description |
|-----------|--------|-------------|
| List | `list_reminders()` | Get reminders with filters |
| Create | `create_reminder()` | Create new reminder |
| Edit | `edit_reminder()` | Modify existing reminder |
| Complete | `complete_reminder()` | Mark as done |
| Delete | `delete_reminder()` | Remove reminder |

### List Operations

| Operation | Method | Description |
|-----------|--------|-------------|
| List All | `list_reminder_lists()` | Get all lists |
| Create | `create_list()` | New list |
| Rename | `rename_list()` | Change list name |
| Delete | `delete_list()` | Remove list |

### Filters & Queries

| Filter | Method | Description |
|--------|--------|-------------|
| Today | `list_reminders(filter_type="today")` | Today's tasks |
| Tomorrow | `list_reminders(filter_type="tomorrow")` | Tomorrow's tasks |
| Week | `list_reminders(filter_type="week")` | This week |
| Overdue | `get_overdue_reminders()` | Past due |
| Upcoming | `get_upcoming_reminders()` | Future tasks |
| By Date | `get_reminder_by_date("2026-02-15")` | Specific date |

## Date Formats

The skill accepts various date formats:

- **Keywords**: `today`, `tomorrow`, `yesterday`
- **ISO Date**: `2026-02-15`
- **ISO Datetime**: `2026-02-15 14:30`
- **ISO 8601**: `2026-02-15T14:30:00Z`
- **Natural language** (via dateutil parsing)

## Priority Levels

- `high` - High priority (🔴)
- `medium` - Medium priority (🟡)
- `low` - Low priority (🟢)
- `none` - No priority

## CLI Usage

The skill can also be used as a standalone CLI:

```bash
# List today's tasks
python -m skills.apple_reminders.apple_reminders list

# List all lists
python -m skills.apple_reminders.apple_reminders lists

# Create a task
python -m skills.apple_reminders.apple_reminders create "Buy milk"

# Complete a task
python -m skills.apple_reminders.apple_reminders complete abc123

# Edit a task
python -m skills.apple_reminders.apple_reminders edit abc123 --title "New title"

# Delete a task
python -m skills.apple_reminders.apple_reminders delete abc123 --force

# Get overdue tasks
python -m skills.apple_reminders.apple_reminders overdue
```

## Testing

Run the test suite:

```bash
python tests/test_skill_apple_reminders.py
```

Tests use mocking to avoid requiring actual Apple Reminders access.

## API Reference

### AppleRemindersSkill

Main skill class providing low-level operations.

```python
class AppleRemindersSkill:
    def __init__(self)
    def list_reminder_lists(self) -> List[Dict]
    def create_list(self, name: str) -> Dict
    def rename_list(self, old_name: str, new_name: str) -> Dict
    def delete_list(self, name: str, force: bool = False) -> Dict
    def list_reminders(self, list_name=None, filter_type="today") -> List[Dict]
    def create_reminder(self, title, list_name=None, due_date=None, notes=None, priority=None) -> Dict
    def edit_reminder(self, reminder_id, title=None, due_date=None, list_name=None, notes=None, priority=None) -> Dict
    def complete_reminder(self, reminder_ids) -> Dict
    def delete_reminder(self, reminder_id, force=False) -> Dict
    def get_reminder_by_date(self, date: str) -> List[Dict]
    def get_overdue_reminders(self) -> List[Dict]
    def get_upcoming_reminders(self) -> List[Dict]
```

### AppleRemindersTools

High-level tools for AI agents with formatted output.

```python
class AppleRemindersTools:
    def get_available_lists(self) -> str
    def get_todays_tasks(self, list_name=None) -> str
    def get_overdue_tasks(self) -> str
    def get_upcoming_tasks(self) -> str
    def search_tasks(self, query: str, list_name=None) -> str
    def create_task(self, title, when=None, list_name=None, priority=None, notes=None) -> str
    def complete_task(self, task_identifier: str) -> str
    def edit_task(self, task_id, title=None, when=None, list_name=None, priority=None, notes=None) -> str
    def delete_task(self, task_id: str, force=False) -> str
    def create_task_list(self, name: str) -> str
    def rename_task_list(self, old_name: str, new_name: str) -> str
    def delete_task_list(self, name: str, force=False) -> str
    def get_task_summary(self) -> str
```

## Troubleshooting

### Permission Denied

```bash
remindctl authorize
# Or manually grant in System Settings
```

### Command Not Found

Ensure `remindctl` is in your PATH:
```bash
which remindctl
```

### No Reminders Appearing

1. Check Reminders app is not locked
2. Verify permissions in System Settings
3. Try `remindctl status`

### SSH Issues

When running over SSH, permissions must be granted on the Mac running the command, not the SSH client.

## License

MIT License - See LICENSE file for details.

## Credits

- [remindctl](https://github.com/steipete/remindctl) by Peter Steinberger
- Cell 0 OS Integration
