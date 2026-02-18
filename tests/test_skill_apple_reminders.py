#!/usr/bin/env python3
"""
Tests for Apple Reminders Skill

These tests use mocking to avoid requiring actual Apple Reminders
and remindctl installation during testing.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import subprocess
from datetime import datetime

# Mock dateutil for tests if not available
import sys
from unittest.mock import MagicMock
mock_dateutil = MagicMock()
sys.modules['dateutil'] = mock_dateutil

# Import the skill modules
import sys
import os

# Add paths for imports - use relative paths
skills_path = os.path.join(os.path.dirname(__file__), '..', 'skills')
sys.path.insert(0, os.path.join(skills_path, 'apple-reminders'))
sys.path.insert(0, skills_path)

# Use absolute import to avoid module caching issues
import importlib.util
spec = importlib.util.spec_from_file_location(
    "apple_reminders_skill", 
    os.path.join(skills_path, 'apple-reminders', 'apple_reminders.py')
)
apple_reminders_module = importlib.util.module_from_spec(spec)
sys.modules["apple_reminders_skill"] = apple_reminders_module
spec.loader.exec_module(apple_reminders_module)
AppleRemindersSkill = apple_reminders_module.AppleRemindersSkill

spec_tools = importlib.util.spec_from_file_location(
    "apple_reminders_tools",
    os.path.join(skills_path, 'apple-reminders', 'tools.py')
)
tools_module = importlib.util.module_from_spec(spec_tools)
sys.modules["apple_reminders_tools"] = tools_module
spec_tools.loader.exec_module(tools_module)
AppleRemindersTools = tools_module.AppleRemindersTools


class TestAppleRemindersSkill(unittest.TestCase):
    """Test cases for AppleRemindersSkill class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_subprocess = Mock()
        self.mock_subprocess.run = Mock()
    
    @patch('apple_reminders.subprocess.run')
    def test_init_checks_binary(self, mock_run):
        """Test that initialization checks for remindctl binary."""
        mock_run.return_value = Mock(returncode=0)
        
        skill = AppleRemindersSkill()
        
        mock_run.assert_called_once_with(
            ['remindctl', '--version'],
            capture_output=True,
            check=True
        )
        self.assertEqual(skill.binary, 'remindctl')
    
    @patch('apple_reminders.subprocess.run')
    def test_init_raises_on_missing_binary(self, mock_run):
        """Test that initialization raises error if remindctl not found."""
        mock_run.side_effect = FileNotFoundError()
        
        with self.assertRaises(RuntimeError) as context:
            AppleRemindersSkill()
        
        self.assertIn('remindctl not found', str(context.exception))
    
    @patch('apple_reminders.subprocess.run')
    def test_list_reminder_lists(self, mock_run):
        """Test listing reminder lists."""
        # Mock successful command
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps([
                {"name": "Personal", "count": 5},
                {"name": "Work", "count": 3}
            ]),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        result = skill.list_reminder_lists()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'Personal')
        self.assertEqual(result[1]['count'], 3)
        mock_run.assert_called_with(
            ['remindctl', 'list', '--json'],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('apple_reminders.subprocess.run')
    def test_create_list(self, mock_run):
        """Test creating a reminder list."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({"name": "Shopping", "created": True}),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        result = skill.create_list("Shopping")
        
        self.assertEqual(result['name'], 'Shopping')
        mock_run.assert_called_with(
            ['remindctl', 'list', 'Shopping', '--create', '--json'],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('apple_reminders.subprocess.run')
    def test_create_list_empty_name_raises(self, mock_run):
        """Test that creating list with empty name raises error."""
        mock_run.return_value = Mock(returncode=0)
        
        skill = AppleRemindersSkill()
        
        with self.assertRaises(ValueError):
            skill.create_list("")
        
        with self.assertRaises(ValueError):
            skill.create_list("   ")
    
    @patch('apple_reminders.subprocess.run')
    def test_rename_list(self, mock_run):
        """Test renaming a reminder list."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({"old_name": "Old", "new_name": "New"}),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        result = skill.rename_list("Old", "New")
        
        self.assertEqual(result['new_name'], 'New')
        mock_run.assert_called_with(
            ['remindctl', 'list', 'Old', '--rename', 'New', '--json'],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('apple_reminders.subprocess.run')
    def test_delete_list(self, mock_run):
        """Test deleting a reminder list."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({"deleted": True, "name": "OldList"}),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        result = skill.delete_list("OldList", force=True)
        
        self.assertTrue(result['deleted'])
        mock_run.assert_called_with(
            ['remindctl', 'list', 'OldList', '--delete', '--force', '--json'],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('apple_reminders.subprocess.run')
    def test_list_reminders_default(self, mock_run):
        """Test listing reminders with default filter."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps([
                {"id": "abc123", "title": "Task 1", "completed": False},
                {"id": "def456", "title": "Task 2", "completed": False}
            ]),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        result = skill.list_reminders()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['title'], 'Task 1')
    
    @patch('apple_reminders.subprocess.run')
    def test_list_reminders_with_list_filter(self, mock_run):
        """Test listing reminders from specific list."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps([{"id": "1", "title": "Work Task"}]),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        result = skill.list_reminders(list_name="Work")
        
        mock_run.assert_called_with(
            ['remindctl', 'list', 'Work', '--json'],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('apple_reminders.subprocess.run')
    def test_list_reminders_invalid_filter_raises(self, mock_run):
        """Test that invalid filter raises error."""
        mock_run.return_value = Mock(returncode=0)
        
        skill = AppleRemindersSkill()
        
        with self.assertRaises(ValueError):
            skill.list_reminders(filter_type="invalid")
    
    @patch('apple_reminders.subprocess.run')
    def test_create_simple_reminder(self, mock_run):
        """Test creating a simple reminder."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({"id": "new123", "title": "Buy milk"}),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        result = skill.create_reminder("Buy milk")
        
        self.assertEqual(result['title'], 'Buy milk')
        mock_run.assert_called_with(
            ['remindctl', 'add', 'Buy milk', '--json'],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('apple_reminders.subprocess.run')
    def test_create_complex_reminder(self, mock_run):
        """Test creating a reminder with all options."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({"id": "new456", "title": "Call mom"}),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        result = skill.create_reminder(
            title="Call mom",
            list_name="Personal",
            due_date="tomorrow",
            notes="Don't forget",
            priority="high"
        )
        
        call_args = mock_run.call_args[0][0]
        self.assertIn('add', call_args)
        self.assertIn('--title', call_args)
        self.assertIn('Call mom', call_args)
        self.assertIn('--list', call_args)
        self.assertIn('Personal', call_args)
        self.assertIn('--due', call_args)
        self.assertIn('tomorrow', call_args)
        self.assertIn('--priority', call_args)
        self.assertIn('high', call_args)
    
    @patch('apple_reminders.subprocess.run')
    def test_create_reminder_empty_title_raises(self, mock_run):
        """Test that creating reminder with empty title raises error."""
        mock_run.return_value = Mock(returncode=0)
        
        skill = AppleRemindersSkill()
        
        with self.assertRaises(ValueError):
            skill.create_reminder("")
    
    @patch('apple_reminders.subprocess.run')
    def test_edit_reminder(self, mock_run):
        """Test editing a reminder."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({"id": "abc", "title": "New Title"}),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        result = skill.edit_reminder("abc", title="New Title", priority="medium")
        
        call_args = mock_run.call_args[0][0]
        self.assertIn('edit', call_args)
        self.assertIn('abc', call_args)
        self.assertIn('--title', call_args)
        self.assertIn('New Title', call_args)
        self.assertIn('--priority', call_args)
        self.assertIn('medium', call_args)
    
    @patch('apple_reminders.subprocess.run')
    def test_edit_reminder_no_changes_raises(self, mock_run):
        """Test that editing without changes raises error."""
        mock_run.return_value = Mock(returncode=0)
        
        skill = AppleRemindersSkill()
        
        with self.assertRaises(ValueError):
            skill.edit_reminder("abc")
    
    @patch('apple_reminders.subprocess.run')
    def test_complete_single_reminder(self, mock_run):
        """Test completing a single reminder."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({"completed": ["abc123"]}),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        result = skill.complete_reminder("abc123")
        
        mock_run.assert_called_with(
            ['remindctl', 'complete', 'abc123', '--json'],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('apple_reminders.subprocess.run')
    def test_complete_multiple_reminders(self, mock_run):
        """Test completing multiple reminders."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({"completed": ["1", "2", "3"]}),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        result = skill.complete_reminder(["1", "2", "3"])
        
        mock_run.assert_called_with(
            ['remindctl', 'complete', '1', '2', '3', '--json'],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('apple_reminders.subprocess.run')
    def test_delete_reminder(self, mock_run):
        """Test deleting a reminder."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({"deleted": True, "id": "abc123"}),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        result = skill.delete_reminder("abc123", force=True)
        
        mock_run.assert_called_with(
            ['remindctl', 'delete', 'abc123', '--force', '--json'],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('apple_reminders.subprocess.run')
    def test_get_reminder_by_date(self, mock_run):
        """Test getting reminders by specific date."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps([{"id": "1", "title": "Meeting"}]),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        result = skill.get_reminder_by_date("2026-02-15")
        
        self.assertEqual(len(result), 1)
        mock_run.assert_called_with(
            ['remindctl', '2026-02-15', '--json'],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('apple_reminders.subprocess.run')
    def test_get_reminder_by_date_invalid_format_raises(self, mock_run):
        """Test that invalid date format raises error."""
        mock_run.return_value = Mock(returncode=0)
        
        skill = AppleRemindersSkill()
        
        with self.assertRaises(ValueError):
            skill.get_reminder_by_date("not-a-date")
        
        with self.assertRaises(ValueError):
            skill.get_reminder_by_date("15-02-2026")  # Wrong format
    
    @patch('apple_reminders.subprocess.run')
    def test_get_overdue_reminders(self, mock_run):
        """Test getting overdue reminders."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps([
                {"id": "1", "title": "Late Task", "due": "2026-01-01"}
            ]),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        result = skill.get_overdue_reminders()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], 'Late Task')
    
    @patch('apple_reminders.subprocess.run')
    def test_get_upcoming_reminders(self, mock_run):
        """Test getting upcoming reminders."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps([
                {"id": "1", "title": "Future Task", "due": "2026-03-01"}
            ]),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        result = skill.get_upcoming_reminders()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], 'Future Task')
    
    @patch('apple_reminders.subprocess.run')
    def test_date_parsing_keywords(self, mock_run):
        """Test that date keywords are handled correctly."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({"id": "1"}),
            stderr=''
        )
        
        skill = AppleRemindersSkill()
        
        # Test keyword handling
        self.assertEqual(skill._parse_date("today"), "today")
        self.assertEqual(skill._parse_date("TODAY"), "today")
        self.assertEqual(skill._parse_date("tomorrow"), "tomorrow")
        self.assertEqual(skill._parse_date("yesterday"), "yesterday")
    
    @patch('apple_reminders.subprocess.run')
    def test_date_parsing_iso_format(self, mock_run):
        """Test ISO date format parsing."""
        mock_run.return_value = Mock(returncode=0)
        
        skill = AppleRemindersSkill()
        
        # Test ISO format
        self.assertEqual(skill._parse_date("2026-02-15"), "2026-02-15")
        self.assertEqual(skill._parse_date("2026-02-15 14:30"), "2026-02-15 14:30")
    
    @patch('apple_reminders.subprocess.run')
    def test_priority_mapping(self, mock_run):
        """Test priority string to flag conversion."""
        mock_run.return_value = Mock(returncode=0)
        
        skill = AppleRemindersSkill()
        
        self.assertEqual(skill._priority_to_flag("high"), "--priority high")
        self.assertEqual(skill._priority_to_flag("medium"), "--priority medium")
        self.assertEqual(skill._priority_to_flag("low"), "--priority low")
        self.assertEqual(skill._priority_to_flag("none"), "--priority none")
        self.assertIsNone(skill._priority_to_flag("invalid"))
        self.assertIsNone(skill._priority_to_flag(None))
    
    @patch('apple_reminders.subprocess.run')
    def test_command_failure_handling(self, mock_run):
        """Test handling of command failures."""
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # __init__ check
                return Mock(returncode=0)
            else:  # list_reminder_lists should fail
                raise subprocess.CalledProcessError(
                    returncode=1,
                    cmd=['remindctl', 'list'],
                    stderr="Permission denied"
                )
        
        mock_run.side_effect = side_effect
        
        skill = AppleRemindersSkill()
        
        with self.assertRaises(RuntimeError) as context:
            skill.list_reminder_lists()
        
        self.assertIn('Permission denied', str(context.exception))


class TestAppleRemindersTools(unittest.TestCase):
    """Test cases for AppleRemindersTools class."""
    
    @patch('tools.AppleRemindersSkill')
    def test_get_available_lists_formatted(self, mock_skill_class):
        """Test formatted list output."""
        mock_skill = Mock()
        mock_skill.list_reminder_lists.return_value = [
            {"name": "Personal", "count": 5},
            {"name": "Work", "count": 3}
        ]
        mock_skill_class.return_value = mock_skill
        
        tools = AppleRemindersTools()
        result = tools.get_available_lists()
        
        self.assertIn("Personal", result)
        self.assertIn("Work", result)
        self.assertIn("5 reminders", result)
        self.assertIn("3 reminders", result)
    
    @patch('tools.AppleRemindersSkill')
    def test_get_todays_tasks_formatted(self, mock_skill_class):
        """Test formatted today's tasks output."""
        mock_skill = Mock()
        mock_skill.list_reminders.return_value = [
            {"id": "1", "title": "Task 1", "priority": "high", "due": "2:00 PM"},
            {"id": "2", "title": "Task 2", "priority": "none", "due": ""}
        ]
        mock_skill_class.return_value = mock_skill
        
        tools = AppleRemindersTools()
        result = tools.get_todays_tasks()
        
        self.assertIn("Today's Tasks", result)
        self.assertIn("Task 1", result)
        self.assertIn("Task 2", result)
        self.assertIn("[1]", result)
    
    @patch('tools.AppleRemindersSkill')
    def test_get_overdue_tasks_formatted(self, mock_skill_class):
        """Test formatted overdue tasks output."""
        mock_skill = Mock()
        mock_skill.get_overdue_reminders.return_value = [
            {"id": "1", "title": "Late Task", "due": "2026-01-01", "list": "Work"}
        ]
        mock_skill_class.return_value = mock_skill
        
        tools = AppleRemindersTools()
        result = tools.get_overdue_tasks()
        
        self.assertIn("Overdue Tasks", result)
        self.assertIn("Late Task", result)
        self.assertIn("[Work]", result)
    
    @patch('tools.AppleRemindersSkill')
    def test_create_task_formatted(self, mock_skill_class):
        """Test formatted task creation output."""
        mock_skill = Mock()
        mock_skill.create_reminder.return_value = {
            "id": "new123",
            "list": "Personal"
        }
        mock_skill_class.return_value = mock_skill
        
        tools = AppleRemindersTools()
        result = tools.create_task(
            title="Buy groceries",
            when="tomorrow",
            priority="medium"
        )
        
        self.assertIn("Created task", result)
        self.assertIn("Buy groceries", result)
        self.assertIn("new123", result)
    
    @patch('tools.AppleRemindersSkill')
    def test_complete_task_by_id(self, mock_skill_class):
        """Test completing task by ID."""
        mock_skill = Mock()
        mock_skill.complete_reminder.return_value = {"completed": ["abc123"]}
        mock_skill_class.return_value = mock_skill
        
        tools = AppleRemindersTools()
        result = tools.complete_task("abc123")
        
        self.assertIn("Completed", result)
        self.assertIn("abc123", result)
    
    @patch('tools.AppleRemindersSkill')
    def test_complete_task_by_search(self, mock_skill_class):
        """Test completing task by searching for name."""
        mock_skill = Mock()
        # First call (complete) fails, then get_all_reminders succeeds
        mock_skill.complete_reminder.side_effect = [
            RuntimeError("Not found"),
            {"completed": ["123"]}
        ]
        mock_skill.get_all_reminders.return_value = [
            {"id": "123", "title": "Buy milk"}
        ]
        mock_skill_class.return_value = mock_skill
        
        tools = AppleRemindersTools()
        result = tools.complete_task("milk")
        
        self.assertIn("Completed", result)
        self.assertIn("Buy milk", result)
    
    @patch('tools.AppleRemindersSkill')
    def test_complete_task_multiple_matches(self, mock_skill_class):
        """Test handling multiple matches when completing."""
        mock_skill = Mock()
        # First complete_reminder call fails (as ID lookup), then get_all_reminders succeeds
        mock_skill.complete_reminder.side_effect = RuntimeError("Not found")
        mock_skill.get_all_reminders.return_value = [
            {"id": "1", "title": "Buy milk"},
            {"id": "2", "title": "Buy almond milk"}
        ]
        mock_skill_class.return_value = mock_skill
        
        tools = AppleRemindersTools()
        result = tools.complete_task("milk")
        
        self.assertIn("Multiple matches", result)
        self.assertIn("[1]", result)
        self.assertIn("[2]", result)
    
    @patch('tools.AppleRemindersSkill')
    def test_search_tasks(self, mock_skill_class):
        """Test searching for tasks."""
        mock_skill = Mock()
        mock_skill.get_all_reminders.return_value = [
            {"id": "1", "title": "Meeting with John", "completed": False, "due": "3:00 PM", "list": "Work"},
            {"id": "2", "title": "Buy groceries", "completed": True, "due": "", "list": "Personal"}
        ]
        mock_skill_class.return_value = mock_skill
        
        tools = AppleRemindersTools()
        result = tools.search_tasks("meeting")
        
        self.assertIn("Search Results", result)
        self.assertIn("Meeting with John", result)
        self.assertIn("⬜", result)  # Not completed
    
    @patch('tools.AppleRemindersSkill')
    def test_search_tasks_no_results(self, mock_skill_class):
        """Test search with no results."""
        mock_skill = Mock()
        mock_skill.get_all_reminders.return_value = [
            {"id": "1", "title": "Task 1", "completed": False, "due": "", "list": ""}
        ]
        mock_skill_class.return_value = mock_skill
        
        tools = AppleRemindersTools()
        result = tools.search_tasks("nonexistent")
        
        self.assertIn("No tasks found", result)
    
    @patch('tools.AppleRemindersSkill')
    def test_task_summary(self, mock_skill_class):
        """Test task summary generation."""
        mock_skill = Mock()
        mock_skill.list_reminder_lists.return_value = [
            {"name": "Personal", "count": 5},
            {"name": "Work", "count": 3}
        ]
        mock_skill.get_overdue_reminders.return_value = [{"id": "1"}]
        mock_skill.list_reminders.return_value = [{"id": "2"}, {"id": "3"}]
        mock_skill.get_upcoming_reminders.return_value = [{"id": "4"}]
        mock_skill_class.return_value = mock_skill
        
        tools = AppleRemindersTools()
        result = tools.get_task_summary()
        
        self.assertIn("Task Summary", result)
        self.assertIn("Lists: 2", result)
        self.assertIn("Today's tasks: 2", result)
        self.assertIn("Overdue: 1", result)
        self.assertIn("Upcoming: 1", result)
        self.assertIn("You have overdue tasks", result)
    
    @patch('tools.AppleRemindersSkill')
    def test_error_handling_formatted(self, mock_skill_class):
        """Test error handling returns formatted message."""
        mock_skill = Mock()
        mock_skill.list_reminder_lists.side_effect = Exception("Connection failed")
        mock_skill_class.return_value = mock_skill
        
        tools = AppleRemindersTools()
        result = tools.get_available_lists()
        
        self.assertIn("❌ Error", result)
        self.assertIn("Connection failed", result)


class TestIntegrationScenarios(unittest.TestCase):
    """Integration-style tests for common workflows."""
    
    @patch('apple_reminders.subprocess.run')
    def test_full_workflow(self, mock_run):
        """Test a complete workflow: create, list, complete, delete."""
        # Setup mock responses for different calls - using a counter approach
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # __init__ check
                return Mock(returncode=0)
            elif call_count[0] == 2:  # create_reminder
                return Mock(returncode=0, stdout=json.dumps({"id": "task123", "title": "Test Task"}), stderr='')
            elif call_count[0] == 3:  # list_reminders
                return Mock(returncode=0, stdout=json.dumps([{"id": "task123", "title": "Test Task", "completed": False}]), stderr='')
            elif call_count[0] == 4:  # complete_reminder
                return Mock(returncode=0, stdout=json.dumps({"completed": ["task123"]}), stderr='')
            elif call_count[0] == 5:  # delete_reminder
                return Mock(returncode=0, stdout=json.dumps({"deleted": True}), stderr='')
            return Mock(returncode=0, stdout='{}', stderr='')
        
        mock_run.side_effect = side_effect
        
        skill = AppleRemindersSkill()
        
        # Create
        created = skill.create_reminder("Test Task")
        self.assertEqual(created['id'], 'task123')
        
        # List
        reminders = skill.list_reminders()
        self.assertEqual(len(reminders), 1)
        
        # Complete
        completed = skill.complete_reminder('task123')
        self.assertIn('completed', completed)
        
        # Delete
        deleted = skill.delete_reminder('task123', force=True)
        self.assertTrue(deleted['deleted'])
    
    @patch('apple_reminders.subprocess.run')
    def test_list_management_workflow(self, mock_run):
        """Test list creation, rename, and deletion workflow."""
        # Setup mock responses using counter approach
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # __init__ check
                return Mock(returncode=0)
            elif call_count[0] == 2:  # create_list
                return Mock(returncode=0, stdout=json.dumps({"name": "Projects", "created": True}), stderr='')
            elif call_count[0] == 3:  # rename_list
                return Mock(returncode=0, stdout=json.dumps({"old_name": "Projects", "new_name": "Active Projects"}), stderr='')
            elif call_count[0] == 4:  # delete_list
                return Mock(returncode=0, stdout=json.dumps({"deleted": True}), stderr='')
            return Mock(returncode=0, stdout='{}', stderr='')
        
        mock_run.side_effect = side_effect
        
        skill = AppleRemindersSkill()
        
        # Create
        created = skill.create_list("Projects")
        self.assertEqual(created['name'], 'Projects')
        
        # Rename
        renamed = skill.rename_list("Projects", "Active Projects")
        self.assertEqual(renamed['new_name'], 'Active Projects')
        
        # Delete
        deleted = skill.delete_list("Active Projects", force=True)
        self.assertTrue(deleted['deleted'])


if __name__ == '__main__':
    # Create a test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAppleRemindersSkill))
    suite.addTests(loader.loadTestsFromTestCase(TestAppleRemindersTools))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationScenarios))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)
