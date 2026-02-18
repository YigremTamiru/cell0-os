#!/usr/bin/env python3
"""
Apple Reminders Skill for Cell 0 OS
Integration with Apple Reminders via remindctl CLI

Requirements:
- macOS 14+ (Sonoma)
- remindctl CLI installed
- Reminders permission granted
"""

import subprocess
import json
import re
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta

# Optional dateutil import with fallback
try:
    from dateutil import parser as date_parser
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False
    date_parser = None


class AppleRemindersSkill:
    """Skill for managing Apple Reminders via remindctl CLI."""
    
    def __init__(self):
        self.binary = "remindctl"
        self._check_binary()
    
    def _check_binary(self) -> None:
        """Check if remindctl is installed."""
        try:
            subprocess.run([self.binary, "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                f"remindctl not found. Please install it:\n"
                f"  brew install steipete/tap/remindctl\n"
                f"See skill.yaml setup instructions for details."
            )
    
    def _run_command(self, args: List[str], json_output: bool = True) -> Union[Dict, str]:
        """Run a remindctl command and return the output."""
        cmd = [self.binary]
        cmd.extend(args)
        
        if json_output:
            cmd.append("--json")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            if json_output and result.stdout:
                return json.loads(result.stdout)
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            raise RuntimeError(f"remindctl command failed: {error_msg}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON output: {e}")
    
    def _parse_date(self, date_str: str) -> str:
        """Parse and normalize date string to remindctl format."""
        if not date_str:
            return ""
        
        # Handle special keywords
        date_lower = date_str.lower().strip()
        if date_lower in ["today", "tomorrow", "yesterday"]:
            return date_lower
        
        # Try to parse as ISO date or datetime
        try:
            # Check if it's already in YYYY-MM-DD format
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                return date_str
            
            # Check if it's YYYY-MM-DD HH:mm format
            if re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}$', date_str):
                return date_str
            
            # Try parsing with dateutil if available
            if HAS_DATEUTIL and date_parser:
                dt = date_parser.parse(date_str)
                return dt.strftime("%Y-%m-%d %H:%M")
            
            # Fallback: return as-is for remindctl to handle
            return date_str
            
        except (ValueError, TypeError):
            # Return as-is, let remindctl handle it
            return date_str
    
    def _priority_to_flag(self, priority: Optional[str]) -> Optional[str]:
        """Convert priority string to remindctl flag."""
        if not priority:
            return None
        
        priority_map = {
            "low": "--priority low",
            "medium": "--priority medium", 
            "high": "--priority high",
            "none": "--priority none"
        }
        
        return priority_map.get(priority.lower())

    # =========================================================================
    # List Operations
    # =========================================================================
    
    def list_reminder_lists(self) -> List[Dict[str, Any]]:
        """
        List all reminder lists.
        
        Returns:
            List of dictionaries containing list information
        """
        result = self._run_command(["list"])
        
        # Handle both single object and array responses
        if isinstance(result, dict):
            return [result]
        elif isinstance(result, list):
            return result
        return []
    
    def create_list(self, name: str) -> Dict[str, Any]:
        """
        Create a new reminder list.
        
        Args:
            name: Name of the new list
            
        Returns:
            Dictionary with created list information
        """
        if not name or not name.strip():
            raise ValueError("List name cannot be empty")
        
        return self._run_command(["list", name, "--create"])
    
    def rename_list(self, old_name: str, new_name: str) -> Dict[str, Any]:
        """
        Rename an existing reminder list.
        
        Args:
            old_name: Current name of the list
            new_name: New name for the list
            
        Returns:
            Dictionary with updated list information
        """
        if not old_name or not old_name.strip():
            raise ValueError("Old list name cannot be empty")
        if not new_name or not new_name.strip():
            raise ValueError("New list name cannot be empty")
        
        return self._run_command(["list", old_name, "--rename", new_name])
    
    def delete_list(self, name: str, force: bool = False) -> Dict[str, Any]:
        """
        Delete a reminder list and all its reminders.
        
        Args:
            name: Name of the list to delete
            force: Force deletion without confirmation
            
        Returns:
            Dictionary with deletion result
        """
        if not name or not name.strip():
            raise ValueError("List name cannot be empty")
        
        args = ["list", name, "--delete"]
        if force:
            args.append("--force")
        
        return self._run_command(args)

    # =========================================================================
    # Reminder Operations
    # =========================================================================
    
    def list_reminders(
        self, 
        list_name: Optional[str] = None, 
        filter_type: str = "today"
    ) -> List[Dict[str, Any]]:
        """
        List reminders with optional filtering.
        
        Args:
            list_name: Filter by specific list (optional)
            filter_type: Filter by status - today, tomorrow, week, overdue, 
                        upcoming, completed, all (default: today)
            
        Returns:
            List of dictionaries containing reminder information
        """
        valid_filters = ["today", "tomorrow", "week", "overdue", 
                        "upcoming", "completed", "all"]
        
        if filter_type not in valid_filters:
            raise ValueError(f"Invalid filter_type. Must be one of: {valid_filters}")
        
        args = []
        
        # Handle list-specific queries
        if list_name:
            args.extend(["list", list_name])
        else:
            # Use filter as command when not specifying a list
            args.append(filter_type)
        
        result = self._run_command(args)
        
        # Handle both single object and array responses
        if isinstance(result, dict):
            return [result]
        elif isinstance(result, list):
            return result
        return []
    
    def create_reminder(
        self,
        title: str,
        list_name: Optional[str] = None,
        due_date: Optional[str] = None,
        notes: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new reminder.
        
        Args:
            title: Title of the reminder
            list_name: List to add reminder to (optional)
            due_date: Due date/time (optional)
            notes: Additional notes (optional)
            priority: Priority level - low, medium, high (optional)
            
        Returns:
            Dictionary with created reminder information
        """
        if not title or not title.strip():
            raise ValueError("Reminder title cannot be empty")
        
        args = ["add"]
        
        # Handle titled vs simple reminders
        if list_name or due_date or notes or priority:
            # Use --title flag for complex reminders
            args.extend(["--title", title])
            
            if list_name:
                args.extend(["--list", list_name])
            
            if due_date:
                parsed_date = self._parse_date(due_date)
                args.extend(["--due", parsed_date])
            
            if notes:
                args.extend(["--notes", notes])
            
            if priority:
                priority_flag = self._priority_to_flag(priority)
                if priority_flag:
                    args.extend(priority_flag.split())
        else:
            # Simple reminder with just title
            args.append(title)
        
        return self._run_command(args)
    
    def edit_reminder(
        self,
        reminder_id: str,
        title: Optional[str] = None,
        due_date: Optional[str] = None,
        list_name: Optional[str] = None,
        notes: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Edit an existing reminder.
        
        Args:
            reminder_id: ID of the reminder to edit
            title: New title (optional)
            due_date: New due date/time (optional)
            list_name: Move to different list (optional)
            notes: New notes (optional)
            priority: New priority level - low, medium, high (optional)
            
        Returns:
            Dictionary with updated reminder information
        """
        if not reminder_id or not reminder_id.strip():
            raise ValueError("Reminder ID cannot be empty")
        
        # Check if at least one field is being updated
        if not any([title, due_date, list_name, notes, priority]):
            raise ValueError("At least one field must be provided to update")
        
        args = ["edit", reminder_id]
        
        if title:
            args.extend(["--title", title])
        
        if due_date:
            parsed_date = self._parse_date(due_date)
            args.extend(["--due", parsed_date])
        
        if list_name:
            args.extend(["--list", list_name])
        
        if notes:
            args.extend(["--notes", notes])
        
        if priority:
            priority_flag = self._priority_to_flag(priority)
            if priority_flag:
                args.extend(priority_flag.split())
        
        return self._run_command(args)
    
    def complete_reminder(self, reminder_ids: Union[str, List[str]]) -> Dict[str, Any]:
        """
        Mark one or more reminders as complete.
        
        Args:
            reminder_ids: Single ID or list of IDs to complete
            
        Returns:
            Dictionary with completion result
        """
        if isinstance(reminder_ids, str):
            reminder_ids = [reminder_ids]
        
        if not reminder_ids:
            raise ValueError("At least one reminder ID must be provided")
        
        args = ["complete"]
        args.extend(reminder_ids)
        
        return self._run_command(args)
    
    def delete_reminder(
        self, 
        reminder_id: str, 
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a reminder.
        
        Args:
            reminder_id: ID of the reminder to delete
            force: Force deletion without confirmation
            
        Returns:
            Dictionary with deletion result
        """
        if not reminder_id or not reminder_id.strip():
            raise ValueError("Reminder ID cannot be empty")
        
        args = ["delete", reminder_id]
        
        if force:
            args.append("--force")
        
        return self._run_command(args)

    # =========================================================================
    # Specialized Queries
    # =========================================================================
    
    def get_reminder_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        Get reminders for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of reminders for that date
        """
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        
        result = self._run_command([date])
        
        if isinstance(result, dict):
            return [result]
        elif isinstance(result, list):
            return result
        return []
    
    def get_overdue_reminders(self) -> List[Dict[str, Any]]:
        """
        Get all overdue reminders.
        
        Returns:
            List of overdue reminders
        """
        result = self._run_command(["overdue"])
        
        if isinstance(result, dict):
            return [result]
        elif isinstance(result, list):
            return result
        return []
    
    def get_upcoming_reminders(self) -> List[Dict[str, Any]]:
        """
        Get upcoming reminders.
        
        Returns:
            List of upcoming reminders
        """
        result = self._run_command(["upcoming"])
        
        if isinstance(result, dict):
            return [result]
        elif isinstance(result, list):
            return result
        return []
    
    def get_completed_reminders(self) -> List[Dict[str, Any]]:
        """
        Get completed reminders.
        
        Returns:
            List of completed reminders
        """
        result = self._run_command(["completed"])
        
        if isinstance(result, dict):
            return [result]
        elif isinstance(result, list):
            return result
        return []
    
    def get_all_reminders(self) -> List[Dict[str, Any]]:
        """
        Get all reminders.
        
        Returns:
            List of all reminders
        """
        result = self._run_command(["all"])
        
        if isinstance(result, dict):
            return [result]
        elif isinstance(result, list):
            return result
        return []


def main():
    """Main entry point for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Apple Reminders Skill for Cell 0 OS"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List reminders
    list_parser = subparsers.add_parser("list", help="List reminders")
    list_parser.add_argument("--list-name", help="Filter by list name")
    list_parser.add_argument(
        "--filter", 
        default="today",
        choices=["today", "tomorrow", "week", "overdue", "upcoming", "completed", "all"],
        help="Filter reminders"
    )
    
    # List lists
    subparsers.add_parser("lists", help="List all reminder lists")
    
    # Create reminder
    create_parser = subparsers.add_parser("create", help="Create a reminder")
    create_parser.add_argument("title", help="Reminder title")
    create_parser.add_argument("--list", dest="list_name", help="List name")
    create_parser.add_argument("--due", dest="due_date", help="Due date")
    create_parser.add_argument("--notes", help="Notes")
    create_parser.add_argument(
        "--priority", 
        choices=["low", "medium", "high"],
        help="Priority level"
    )
    
    # Complete reminder
    complete_parser = subparsers.add_parser("complete", help="Complete reminder(s)")
    complete_parser.add_argument("ids", nargs="+", help="Reminder ID(s)")
    
    # Edit reminder
    edit_parser = subparsers.add_parser("edit", help="Edit a reminder")
    edit_parser.add_argument("id", help="Reminder ID")
    edit_parser.add_argument("--title", help="New title")
    edit_parser.add_argument("--due", dest="due_date", help="New due date")
    edit_parser.add_argument("--list", dest="list_name", help="New list")
    edit_parser.add_argument("--notes", help="New notes")
    edit_parser.add_argument(
        "--priority", 
        choices=["low", "medium", "high"],
        help="New priority"
    )
    
    # Delete reminder
    delete_parser = subparsers.add_parser("delete", help="Delete a reminder")
    delete_parser.add_argument("id", help="Reminder ID")
    delete_parser.add_argument("--force", action="store_true", help="Force delete")
    
    # Create list
    create_list_parser = subparsers.add_parser("create-list", help="Create a list")
    create_list_parser.add_argument("name", help="List name")
    
    # Rename list
    rename_list_parser = subparsers.add_parser("rename-list", help="Rename a list")
    rename_list_parser.add_argument("old_name", help="Current name")
    rename_list_parser.add_argument("new_name", help="New name")
    
    # Delete list
    delete_list_parser = subparsers.add_parser("delete-list", help="Delete a list")
    delete_list_parser.add_argument("name", help="List name")
    delete_list_parser.add_argument("--force", action="store_true", help="Force delete")
    
    # Overdue
    subparsers.add_parser("overdue", help="Get overdue reminders")
    
    # Upcoming
    subparsers.add_parser("upcoming", help="Get upcoming reminders")
    
    # By date
    date_parser_cmd = subparsers.add_parser("date", help="Get reminders by date")
    date_parser_cmd.add_argument("date", help="Date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        skill = AppleRemindersSkill()
        
        if args.command == "list":
            result = skill.list_reminders(args.list_name, args.filter)
        elif args.command == "lists":
            result = skill.list_reminder_lists()
        elif args.command == "create":
            result = skill.create_reminder(
                args.title, args.list_name, args.due_date, args.notes, args.priority
            )
        elif args.command == "complete":
            result = skill.complete_reminder(args.ids)
        elif args.command == "edit":
            result = skill.edit_reminder(
                args.id, args.title, args.due_date, args.list_name, args.notes, args.priority
            )
        elif args.command == "delete":
            result = skill.delete_reminder(args.id, args.force)
        elif args.command == "create-list":
            result = skill.create_list(args.name)
        elif args.command == "rename-list":
            result = skill.rename_list(args.old_name, args.new_name)
        elif args.command == "delete-list":
            result = skill.delete_list(args.name, args.force)
        elif args.command == "overdue":
            result = skill.get_overdue_reminders()
        elif args.command == "upcoming":
            result = skill.get_upcoming_reminders()
        elif args.command == "date":
            result = skill.get_reminder_by_date(args.date)
        else:
            parser.print_help()
            return
        
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Error: {e}", file=__import__('sys').stderr)
        exit(1)


if __name__ == "__main__":
    main()
