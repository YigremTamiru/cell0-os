#!/usr/bin/env python3
"""
Tests for Apple Notes Skill

This module contains unit tests for the Apple Notes skill functionality.
Tests are designed to work without requiring actual Apple Notes data,
using mocking where appropriate.

Run with: python -m pytest tests/test_skill_apple_notes.py -v
Or: python tests/test_skill_apple_notes.py

Author: Cell 0 OS
Version: 1.0.0
"""

import unittest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "apple-notes"))

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

from tools import (
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
    success_response,
    error_response
)


class TestNote(unittest.TestCase):
    """Test Note dataclass"""
    
    def test_note_creation(self):
        """Test creating a Note object"""
        note = Note(title="Test Note", folder="Work", content="Test content")
        self.assertEqual(note.title, "Test Note")
        self.assertEqual(note.folder, "Work")
        self.assertEqual(note.content, "Test content")
    
    def test_note_to_dict(self):
        """Test Note conversion to dictionary"""
        note = Note(title="Test", content="Content")
        note_dict = note.to_dict()
        self.assertEqual(note_dict["title"], "Test")
        self.assertEqual(note_dict["content"], "Content")
        self.assertIsNone(note_dict["folder"])


class TestFolder(unittest.TestCase):
    """Test Folder dataclass"""
    
    def test_folder_creation(self):
        """Test creating a Folder object"""
        folder = Folder(name="Work", parent="Notes", is_nested=True)
        self.assertEqual(folder.name, "Work")
        self.assertEqual(folder.parent, "Notes")
        self.assertTrue(folder.is_nested)
    
    def test_folder_to_dict(self):
        """Test Folder conversion to dictionary"""
        folder = Folder(name="Personal")
        folder_dict = folder.to_dict()
        self.assertEqual(folder_dict["name"], "Personal")
        self.assertFalse(folder_dict["is_nested"])


class TestAppleNotesSkill(unittest.TestCase):
    """Test AppleNotesSkill class"""
    
    @patch('apple_notes.subprocess.run')
    def test_check_memo_installed(self, mock_run):
        """Test memo installation check"""
        mock_run.return_value = Mock(returncode=0, stdout="1.0.0")
        skill = AppleNotesSkill()
        self.assertEqual(skill.memo_path, "memo")
    
    @patch('apple_notes.subprocess.run')
    def test_memo_not_installed(self, mock_run):
        """Test error when memo is not installed"""
        mock_run.side_effect = FileNotFoundError()
        with self.assertRaises(MemoNotInstalledError):
            AppleNotesSkill()
    
    @patch('apple_notes.subprocess.run')
    def test_list_notes(self, mock_run):
        """Test listing notes"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Note 1\nNote 2\nNote 3",
            stderr=""
        )
        
        skill = AppleNotesSkill()
        notes = skill.list_notes()
        
        self.assertEqual(len(notes), 3)
        self.assertEqual(notes[0].title, "Note 1")
        self.assertEqual(notes[1].title, "Note 2")
    
    @patch('apple_notes.subprocess.run')
    def test_list_notes_in_folder(self, mock_run):
        """Test listing notes in a specific folder"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Work Note 1\nWork Note 2",
            stderr=""
        )
        
        skill = AppleNotesSkill()
        notes = skill.list_notes(folder="Work")
        
        self.assertEqual(len(notes), 2)
        self.assertEqual(notes[0].folder, "Work")
    
    @patch('apple_notes.subprocess.run')
    def test_list_folders(self, mock_run):
        """Test listing folders"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Notes\n  Work\n  Personal\nArchive",
            stderr=""
        )
        
        skill = AppleNotesSkill()
        folders = skill.list_folders()
        
        self.assertGreater(len(folders), 0)
    
    @patch('apple_notes.subprocess.run')
    def test_search_notes(self, mock_run):
        """Test searching notes"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Work - Meeting Notes\nPersonal - Shopping List",
            stderr=""
        )
        
        skill = AppleNotesSkill()
        notes = skill.search_notes("meeting")
        
        self.assertEqual(len(notes), 2)
        self.assertEqual(notes[0].folder, "Work")
        self.assertEqual(notes[0].title, "Meeting Notes")
    
    @patch('apple_notes.subprocess.run')
    def test_delete_note(self, mock_run):
        """Test deleting a note"""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        skill = AppleNotesSkill()
        result = skill.delete_note("Test Note")
        
        self.assertTrue(result)
    
    @patch('apple_notes.subprocess.run')
    def test_export_notes(self, mock_run):
        """Test exporting notes"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Exported to Desktop",
            stderr=""
        )
        
        skill = AppleNotesSkill()
        path = skill.export_notes(format=ExportFormat.MARKDOWN)
        
        self.assertIn("Desktop", path)


class TestTools(unittest.TestCase):
    """Test agent tools"""
    
    def test_success_response(self):
        """Test success response format"""
        response = success_response(data={"test": "data"}, message="Success")
        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["test"], "data")
        self.assertEqual(response["message"], "Success")
        self.assertIsNone(response["error"])
    
    def test_error_response(self):
        """Test error response format"""
        response = error_response("Test error", "Something went wrong")
        self.assertFalse(response["success"])
        self.assertIsNone(response["data"])
        self.assertEqual(response["error"], "Test error")
        self.assertEqual(response["message"], "Something went wrong")
    
    @patch('tools.AppleNotesSkill')
    def test_list_notes_tool(self, mock_skill_class):
        """Test list_notes_tool"""
        mock_skill = Mock()
        mock_skill.list_notes.return_value = [
            Note(title="Note 1"),
            Note(title="Note 2")
        ]
        mock_skill_class.return_value = mock_skill
        
        result = list_notes_tool()
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["data"]), 2)
    
    @patch('tools.AppleNotesSkill')
    def test_list_folders_tool(self, mock_skill_class):
        """Test list_folders_tool"""
        mock_skill = Mock()
        mock_skill.list_folders.return_value = [
            Folder(name="Notes"),
            Folder(name="Work", parent="Notes", is_nested=True)
        ]
        mock_skill_class.return_value = mock_skill
        
        result = list_folders_tool()
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["data"]), 2)
    
    @patch('tools.AppleNotesSkill')
    def test_create_note_tool(self, mock_skill_class):
        """Test create_note_tool"""
        mock_skill = Mock()
        mock_skill.create_note.return_value = Note(
            title="New Note",
            content="Content",
            folder="Work"
        )
        mock_skill_class.return_value = mock_skill
        
        result = create_note_tool("New Note", "Content", "Work")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["title"], "New Note")
    
    @patch('tools.AppleNotesSkill')
    def test_search_notes_tool(self, mock_skill_class):
        """Test search_notes_tool"""
        mock_skill = Mock()
        mock_skill.search_notes.return_value = [
            Note(title="Meeting Notes"),
            Note(title="Meeting Agenda")
        ]
        mock_skill_class.return_value = mock_skill
        
        result = search_notes_tool("meeting")
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["data"]), 2)
        self.assertIn("meeting", result["message"].lower())
    
    @patch('tools.AppleNotesSkill')
    def test_get_stats_tool(self, mock_skill_class):
        """Test get_stats_tool"""
        mock_skill = Mock()
        mock_skill.get_note_count.return_value = 42
        mock_skill.get_folder_count.return_value = 5
        mock_skill_class.return_value = mock_skill
        
        result = get_stats_tool()
        
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["total_notes"], 42)
        self.assertEqual(result["data"]["total_folders"], 5)
    
    def test_execute_tool_valid(self):
        """Test execute_tool with valid tool name"""
        with patch('tools.AppleNotesSkill') as mock_skill_class:
            mock_skill = Mock()
            mock_skill.get_note_count.return_value = 5
            mock_skill.get_folder_count.return_value = 2
            mock_skill_class.return_value = mock_skill
            
            result = execute_tool("apple_notes_stats")
            self.assertTrue(result["success"])
            self.assertEqual(result["data"]["total_notes"], 5)
    
    def test_execute_tool_invalid(self):
        """Test execute_tool with invalid tool name"""
        result = execute_tool("invalid_tool")
        self.assertFalse(result["success"])
        self.assertIn("Unknown tool", result["error"])
    
    def test_get_available_tools(self):
        """Test getting available tools"""
        tools = get_available_tools()
        
        self.assertIn("apple_notes_list", tools)
        self.assertIn("apple_notes_create", tools)
        self.assertIn("apple_notes_search", tools)
        
        # Check tool structure
        for tool_name, tool_info in tools.items():
            self.assertIn("description", tool_info)
            self.assertIn("parameters", tool_info)


class TestExportFormat(unittest.TestCase):
    """Test ExportFormat enum"""
    
    def test_export_format_values(self):
        """Test export format enum values"""
        self.assertEqual(ExportFormat.HTML.value, "html")
        self.assertEqual(ExportFormat.MARKDOWN.value, "markdown")


class TestExceptions(unittest.TestCase):
    """Test custom exceptions"""
    
    def test_note_error(self):
        """Test NoteError exception"""
        with self.assertRaises(NoteError):
            raise NoteError("Test error")
    
    def test_note_not_found_error(self):
        """Test NoteNotFoundError exception"""
        with self.assertRaises(NoteNotFoundError):
            raise NoteNotFoundError("Note not found")
    
    def test_folder_not_found_error(self):
        """Test FolderNotFoundError exception"""
        with self.assertRaises(FolderNotFoundError):
            raise FolderNotFoundError("Folder not found")
    
    def test_memo_not_installed_error(self):
        """Test MemoNotInstalledError exception"""
        with self.assertRaises(MemoNotInstalledError):
            raise MemoNotInstalledError("Memo not installed")


class TestIntegration(unittest.TestCase):
    """Integration tests (may require memo CLI)"""
    
    @unittest.skipIf(
        os.environ.get("SKIP_INTEGRATION_TESTS"),
        "Skipping integration tests"
    )
    def test_skill_initialization(self):
        """Test skill can be initialized (requires memo installed)"""
        try:
            skill = AppleNotesSkill()
            self.assertIsNotNone(skill)
        except MemoNotInstalledError:
            self.skipTest("memo CLI not installed")


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestNote))
    suite.addTests(loader.loadTestsFromTestCase(TestFolder))
    suite.addTests(loader.loadTestsFromTestCase(TestAppleNotesSkill))
    suite.addTests(loader.loadTestsFromTestCase(TestTools))
    suite.addTests(loader.loadTestsFromTestCase(TestExportFormat))
    suite.addTests(loader.loadTestsFromTestCase(TestExceptions))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 60)
    print("Apple Notes Skill Tests")
    print("=" * 60)
    print()
    
    # Run with unittest framework
    success = run_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
