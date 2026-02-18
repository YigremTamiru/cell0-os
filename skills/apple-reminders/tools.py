#!/usr/bin/env python3
"""
Tools for Apple Reminders Skill - Agent Integration
High-level tools for AI agents to interact with Apple Reminders
"""

from typing import Optional, List, Dict, Any, Union
try:
    from .apple_reminders import AppleRemindersSkill
except ImportError:
    from apple_reminders import AppleRemindersSkill


class AppleRemindersTools:
    """
    High-level tools for AI agents to manage Apple Reminders.
    
    This class provides semantic, agent-friendly methods for common
    reminder operations with natural language support.
    """
    
    def __init__(self):
        self.skill = AppleRemindersSkill()
    
    # ========================================================================
    # Discovery Tools
    # ========================================================================
    
    def get_available_lists(self) -> str:
        """
        Get a human-readable list of all reminder lists.
        
        Returns:
            Formatted string with list names
        """
        try:
            lists = self.skill.list_reminder_lists()
            
            if not lists:
                return "No reminder lists found."
            
            result = ["📋 Available Reminder Lists:", ""]
            for lst in lists:
                name = lst.get("name", "Unnamed")
                count = lst.get("count", "?")
                result.append(f"  • {name} ({count} reminders)")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ Error fetching lists: {e}"
    
    def get_todays_tasks(self, list_name: Optional[str] = None) -> str:
        """
        Get today's reminders in a human-readable format.
        
        Args:
            list_name: Optional list to filter by
            
        Returns:
            Formatted string with today's tasks
        """
        try:
            reminders = self.skill.list_reminders(list_name, filter_type="today")
            
            if not reminders:
                list_str = f" in '{list_name}'" if list_name else ""
                return f"✅ No tasks for today{list_str}!"
            
            result = [f"📅 Today's Tasks{(' in ' + list_name) if list_name else ''}:", ""]
            
            for r in reminders:
                title = r.get("title", "Untitled")
                reminder_id = r.get("id", "N/A")
                priority = r.get("priority", "none")
                due = r.get("due", "")
                
                priority_icon = ""
                if priority == "high":
                    priority_icon = "🔴 "
                elif priority == "medium":
                    priority_icon = "🟡 "
                elif priority == "low":
                    priority_icon = "🟢 "
                
                time_str = f" ({due})" if due else ""
                result.append(f"  {priority_icon}[{reminder_id}] {title}{time_str}")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ Error fetching today's tasks: {e}"
    
    def get_overdue_tasks(self) -> str:
        """
        Get all overdue reminders.
        
        Returns:
            Formatted string with overdue tasks
        """
        try:
            reminders = self.skill.get_overdue_reminders()
            
            if not reminders:
                return "✅ No overdue tasks!"
            
            result = ["⚠️ Overdue Tasks:", ""]
            
            for r in reminders:
                title = r.get("title", "Untitled")
                reminder_id = r.get("id", "N/A")
                due = r.get("due", "Unknown date")
                list_name = r.get("list", "")
                
                list_str = f" [{list_name}]" if list_name else ""
                result.append(f"  [{reminder_id}] {title}{list_str} (Due: {due})")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ Error fetching overdue tasks: {e}"
    
    def get_upcoming_tasks(self) -> str:
        """
        Get upcoming reminders.
        
        Returns:
            Formatted string with upcoming tasks
        """
        try:
            reminders = self.skill.get_upcoming_reminders()
            
            if not reminders:
                return "📭 No upcoming tasks."
            
            result = ["📬 Upcoming Tasks:", ""]
            
            for r in reminders:
                title = r.get("title", "Untitled")
                reminder_id = r.get("id", "N/A")
                due = r.get("due", "")
                list_name = r.get("list", "")
                
                list_str = f" [{list_name}]" if list_name else ""
                due_str = f" - {due}" if due else ""
                result.append(f"  [{reminder_id}] {title}{list_str}{due_str}")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ Error fetching upcoming tasks: {e}"
    
    def search_tasks(self, query: str, list_name: Optional[str] = None) -> str:
        """
        Search for reminders containing a query string.
        
        Args:
            query: Search string
            list_name: Optional list to search within
            
        Returns:
            Formatted string with matching tasks
        """
        try:
            # Get all reminders and filter
            reminders = self.skill.get_all_reminders()
            query_lower = query.lower()
            
            matches = []
            for r in reminders:
                title = r.get("title", "")
                notes = r.get("notes", "")
                r_list = r.get("list", "")
                
                # Filter by list if specified
                if list_name and r_list.lower() != list_name.lower():
                    continue
                
                # Check if query matches title or notes
                if query_lower in title.lower() or query_lower in notes.lower():
                    matches.append(r)
            
            if not matches:
                list_str = f" in '{list_name}'" if list_name else ""
                return f"🔍 No tasks found matching '{query}'{list_str}"
            
            result = [f"🔍 Search Results for '{query}':", ""]
            
            for r in matches:
                title = r.get("title", "Untitled")
                reminder_id = r.get("id", "N/A")
                due = r.get("due", "")
                completed = r.get("completed", False)
                r_list = r.get("list", "")
                
                status_icon = "✅" if completed else "⬜"
                list_str = f" [{r_list}]" if r_list else ""
                due_str = f" ({due})" if due else ""
                
                result.append(f"  {status_icon} [{reminder_id}] {title}{list_str}{due_str}")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ Error searching tasks: {e}"

    # ========================================================================
    # Action Tools
    # ========================================================================
    
    def create_task(
        self,
        title: str,
        when: Optional[str] = None,
        list_name: Optional[str] = None,
        priority: Optional[str] = None,
        notes: Optional[str] = None
    ) -> str:
        """
        Create a new reminder with natural language support.
        
        Args:
            title: What to remember
            when: When it's due (natural language like "tomorrow at 3pm", "next Monday")
            list_name: Which list to add to
            priority: high, medium, or low
            notes: Additional details
            
        Returns:
            Success message with created task details
        """
        try:
            result = self.skill.create_reminder(
                title=title,
                list_name=list_name,
                due_date=when,
                notes=notes,
                priority=priority
            )
            
            task_id = result.get("id", "N/A")
            created_list = result.get("list", list_name or "default")
            
            priority_str = f" ({priority} priority)" if priority else ""
            when_str = f" due {when}" if when else ""
            
            return (
                f"✅ Created task '{title}'{priority_str}{when_str}\n"
                f"   ID: {task_id}\n"
                f"   List: {created_list}"
            )
            
        except Exception as e:
            return f"❌ Error creating task: {e}"
    
    def complete_task(self, task_identifier: str) -> str:
        """
        Complete a task by ID or search for it by name.
        
        Args:
            task_identifier: Task ID or name to search for
            
        Returns:
            Success or error message
        """
        try:
            # First, try to use it as an ID
            try:
                result = self.skill.complete_reminder(task_identifier)
                return f"✅ Completed task (ID: {task_identifier})"
            except:
                # If that fails, search for it
                reminders = self.skill.get_all_reminders()
                matches = [
                    r for r in reminders 
                    if task_identifier.lower() in r.get("title", "").lower()
                ]
                
                if not matches:
                    return f"❌ No task found matching '{task_identifier}'"
                
                if len(matches) == 1:
                    reminder_id = matches[0].get("id")
                    self.skill.complete_reminder(reminder_id)
                    title = matches[0].get("title", "Untitled")
                    return f"✅ Completed '{title}'"
                else:
                    # Multiple matches
                    result = [f"⚠️ Multiple matches for '{task_identifier}':"]
                    for m in matches:
                        result.append(f"  [{m.get('id')}] {m.get('title')}")
                    result.append("\nPlease specify the task ID to complete.")
                    return "\n".join(result)
                    
        except Exception as e:
            return f"❌ Error completing task: {e}"
    
    def complete_multiple_tasks(self, task_identifiers: List[str]) -> str:
        """
        Complete multiple tasks by their IDs.
        
        Args:
            task_identifiers: List of task IDs
            
        Returns:
            Success or error message
        """
        try:
            self.skill.complete_reminder(task_identifiers)
            return f"✅ Completed {len(task_identifiers)} task(s)"
        except Exception as e:
            return f"❌ Error completing tasks: {e}"
    
    def edit_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        when: Optional[str] = None,
        list_name: Optional[str] = None,
        priority: Optional[str] = None,
        notes: Optional[str] = None
    ) -> str:
        """
        Edit an existing task.
        
        Args:
            task_id: Task ID to edit
            title: New title
            when: New due date
            list_name: Move to different list
            priority: New priority
            notes: New notes
            
        Returns:
            Success message with updated details
        """
        try:
            result = self.skill.edit_reminder(
                reminder_id=task_id,
                title=title,
                due_date=when,
                list_name=list_name,
                notes=notes,
                priority=priority
            )
            
            changes = []
            if title:
                changes.append(f"title → '{title}'")
            if when:
                changes.append(f"due date → {when}")
            if list_name:
                changes.append(f"list → {list_name}")
            if priority:
                changes.append(f"priority → {priority}")
            if notes:
                changes.append("notes updated")
            
            change_str = ", ".join(changes) if changes else "no changes"
            return f"✅ Updated task {task_id}: {change_str}"
            
        except Exception as e:
            return f"❌ Error editing task: {e}"
    
    def delete_task(self, task_id: str, force: bool = False) -> str:
        """
        Delete a task by ID.
        
        Args:
            task_id: Task ID to delete
            force: Skip confirmation
            
        Returns:
            Success or error message
        """
        try:
            self.skill.delete_reminder(task_id, force=force)
            return f"🗑️ Deleted task {task_id}"
        except Exception as e:
            return f"❌ Error deleting task: {e}"
    
    def create_task_list(self, name: str) -> str:
        """
        Create a new reminder list.
        
        Args:
            name: Name for the new list
            
        Returns:
            Success message
        """
        try:
            self.skill.create_list(name)
            return f"📋 Created new list '{name}'"
        except Exception as e:
            return f"❌ Error creating list: {e}"
    
    def rename_task_list(self, old_name: str, new_name: str) -> str:
        """
        Rename a reminder list.
        
        Args:
            old_name: Current list name
            new_name: New list name
            
        Returns:
            Success message
        """
        try:
            self.skill.rename_list(old_name, new_name)
            return f"📋 Renamed list '{old_name}' → '{new_name}'"
        except Exception as e:
            return f"❌ Error renaming list: {e}"
    
    def delete_task_list(self, name: str, force: bool = False) -> str:
        """
        Delete a reminder list.
        
        Args:
            name: List name to delete
            force: Skip confirmation
            
        Returns:
            Success message
        """
        try:
            self.skill.delete_list(name, force=force)
            return f"🗑️ Deleted list '{name}'"
        except Exception as e:
            return f"❌ Error deleting list: {e}"

    # ========================================================================
    # Summary Tools
    # ========================================================================
    
    def get_task_summary(self) -> str:
        """
        Get a comprehensive summary of all task statuses.
        
        Returns:
            Formatted summary string
        """
        try:
            lists = self.skill.list_reminder_lists()
            overdue = self.skill.get_overdue_reminders()
            today = self.skill.list_reminders(filter_type="today")
            upcoming = self.skill.get_upcoming_reminders()
            
            result = ["📊 Task Summary", "=" * 40, ""]
            
            # Lists overview
            result.append(f"📋 Lists: {len(lists)}")
            for lst in lists:
                name = lst.get("name", "Unnamed")
                count = lst.get("count", 0)
                result.append(f"   • {name}: {count} tasks")
            
            result.append("")
            
            # Task counts
            result.append(f"⬜ Today's tasks: {len(today)}")
            result.append(f"⚠️  Overdue: {len(overdue)}")
            result.append(f"📬 Upcoming: {len(upcoming)}")
            
            if overdue:
                result.append("")
                result.append("⚠️  You have overdue tasks that need attention!")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ Error generating summary: {e}"


# Convenience functions for direct import
_tools_instance = None

def _get_tools() -> AppleRemindersTools:
    """Get or create singleton tools instance."""
    global _tools_instance
    if _tools_instance is None:
        _tools_instance = AppleRemindersTools()
    return _tools_instance


# Expose common operations as module-level functions
def get_lists() -> str:
    """Get available reminder lists."""
    return _get_tools().get_available_lists()

def get_today(list_name: Optional[str] = None) -> str:
    """Get today's tasks."""
    return _get_tools().get_todays_tasks(list_name)

def get_overdue() -> str:
    """Get overdue tasks."""
    return _get_tools().get_overdue_tasks()

def get_upcoming() -> str:
    """Get upcoming tasks."""
    return _get_tools().get_upcoming_tasks()

def search(query: str, list_name: Optional[str] = None) -> str:
    """Search for tasks."""
    return _get_tools().search_tasks(query, list_name)

def create(
    title: str,
    when: Optional[str] = None,
    list_name: Optional[str] = None,
    priority: Optional[str] = None,
    notes: Optional[str] = None
) -> str:
    """Create a new task."""
    return _get_tools().create_task(title, when, list_name, priority, notes)

def complete(task_identifier: str) -> str:
    """Complete a task."""
    return _get_tools().complete_task(task_identifier)

def edit(
    task_id: str,
    title: Optional[str] = None,
    when: Optional[str] = None,
    list_name: Optional[str] = None,
    priority: Optional[str] = None,
    notes: Optional[str] = None
) -> str:
    """Edit a task."""
    return _get_tools().edit_task(task_id, title, when, list_name, priority, notes)

def delete(task_id: str, force: bool = False) -> str:
    """Delete a task."""
    return _get_tools().delete_task(task_id, force)

def create_list(name: str) -> str:
    """Create a new list."""
    return _get_tools().create_task_list(name)

def rename_list(old_name: str, new_name: str) -> str:
    """Rename a list."""
    return _get_tools().rename_task_list(old_name, new_name)

def delete_list(name: str, force: bool = False) -> str:
    """Delete a list."""
    return _get_tools().delete_task_list(name, force)

def summary() -> str:
    """Get task summary."""
    return _get_tools().get_task_summary()
