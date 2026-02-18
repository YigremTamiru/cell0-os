"""
Tests for Google Chat Integration

Tests cover:
- Bot initialization and configuration
- Event handling (MESSAGE, ADDED_TO_SPACE, REMOVED_FROM_SPACE)
- Card builder functionality
- Slash command handling
- Tool interface
- Message sending

Author: KULLU (Cell 0 OS)
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cell0.integrations.google_chat_bot import (
    GoogleChatBot,
    CardBuilder,
    ChatMessage,
    ChatEventType,
    SlashCommand,
    SpaceType,
    create_bot
)

from cell0.engine.tools.google_chat import (
    GoogleChatTool,
    NotificationRequest,
    NotificationResponse,
    send_notification,
    send_to_user,
    send_to_space
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_config():
    """Provide mock configuration"""
    return {
        "bot_name": "TestBot",
        "project_id": "test-project",
        "credentials_path": "/fake/path/credentials.json",
        "auth": {
            "type": "service_account",
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": ["https://www.googleapis.com/auth/chat.bot"]
        },
        "webhook": {
            "enabled": True,
            "port": 8080,
            "path": "/chat/webhook",
            "verify_tokens": False
        },
        "features": {
            "threading": True,
            "cards": True,
            "slash_commands": True
        }
    }


@pytest.fixture
def sample_message_data():
    """Provide sample message event data"""
    return {
        "type": "MESSAGE",
        "message": {
            "name": "spaces/ABC123/messages/DEF456",
            "text": "Hello bot",
            "sender": {
                "name": "users/123",
                "displayName": "Test User",
                "email": "test@example.com"
            },
            "space": {
                "name": "spaces/ABC123",
                "displayName": "Test Space",
                "spaceType": "SPACE"
            },
            "thread": {
                "name": "spaces/ABC123/threads/XYZ789"
            },
            "createTime": "2024-01-01T00:00:00Z"
        }
    }


@pytest.fixture
def sample_dm_message_data():
    """Provide sample DM message event data"""
    return {
        "type": "MESSAGE",
        "message": {
            "name": "spaces/DEF456/messages/GHI789",
            "text": "Hello bot",
            "sender": {
                "name": "users/123",
                "displayName": "Test User",
                "email": "test@example.com"
            },
            "space": {
                "name": "spaces/DEF456",
                "spaceType": "DIRECT_MESSAGE"
            },
            "createTime": "2024-01-01T00:00:00Z"
        }
    }


@pytest.fixture
def sample_slash_command_data():
    """Provide sample slash command event data"""
    return {
        "type": "MESSAGE",
        "message": {
            "name": "spaces/ABC123/messages/DEF456",
            "text": "/help",
            "argumentText": "",
            "slashCommand": {
                "commandId": "1",
                "commandName": "/help",
                "triggersDialog": False
            },
            "sender": {
                "name": "users/123",
                "displayName": "Test User",
                "email": "test@example.com"
            },
            "space": {
                "name": "spaces/ABC123",
                "displayName": "Test Space",
                "spaceType": "SPACE"
            }
        }
    }


@pytest.fixture
def sample_added_to_space_data():
    """Provide sample added to space event data"""
    return {
        "type": "ADDED_TO_SPACE",
        "space": {
            "name": "spaces/ABC123",
            "displayName": "Test Space",
            "spaceType": "SPACE"
        },
        "user": {
            "name": "users/123",
            "displayName": "Test User",
            "email": "test@example.com"
        }
    }


@pytest.fixture
def sample_removed_from_space_data():
    """Provide sample removed from space event data"""
    return {
        "type": "REMOVED_FROM_SPACE",
        "space": {
            "name": "spaces/ABC123",
            "displayName": "Test Space",
            "spaceType": "SPACE"
        }
    }


@pytest.fixture
def sample_card_click_data():
    """Provide sample card click event data"""
    return {
        "type": "CARD_CLICKED",
        "action": {
            "actionMethodName": "complete_task",
            "parameters": [
                {"key": "task_id", "value": "123"}
            ]
        },
        "message": {
            "name": "spaces/ABC123/messages/DEF456"
        },
        "user": {
            "name": "users/123",
            "displayName": "Test User"
        }
    }


# ============================================================================
# CardBuilder Tests
# ============================================================================

class TestCardBuilder:
    """Test the CardBuilder class"""
    
    def test_card_builder_initialization(self):
        """Test CardBuilder initializes correctly"""
        builder = CardBuilder()
        card = builder.build()
        
        assert "cardsV2" in card
        assert len(card["cardsV2"]) == 1
        assert "card" in card["cardsV2"][0]
        assert "sections" in card["cardsV2"][0]["card"]
    
    def test_set_header(self):
        """Test setting card header"""
        builder = CardBuilder()
        builder.set_header(
            title="Test Title",
            subtitle="Test Subtitle",
            image_url="https://example.com/image.png"
        )
        
        card = builder.build()
        header = card["cardsV2"][0]["card"]["header"]
        
        assert header["title"] == "Test Title"
        assert header["subtitle"] == "Test Subtitle"
        assert header["imageUrl"] == "https://example.com/image.png"
    
    def test_add_section(self):
        """Test adding sections"""
        builder = CardBuilder()
        builder.add_section("Test Header", collapsible=True, uncollapsible_widgets=1)
        
        card = builder.build()
        sections = card["cardsV2"][0]["card"]["sections"]
        
        assert len(sections) == 1
        assert sections[0]["header"] == "Test Header"
        assert sections[0]["collapsible"] == True
        assert sections[0]["uncollapsibleWidgetsCount"] == 1
    
    def test_add_text_paragraph(self):
        """Test adding text paragraph widget"""
        builder = CardBuilder()
        builder.add_text_paragraph("Hello World")
        
        card = builder.build()
        widgets = card["cardsV2"][0]["card"]["sections"][0]["widgets"]
        
        assert len(widgets) == 1
        assert widgets[0]["textParagraph"]["text"] == "Hello World"
    
    def test_add_image(self):
        """Test adding image widget"""
        builder = CardBuilder()
        builder.add_image(
            image_url="https://example.com/image.png",
            alt_text="Test Image"
        )
        
        card = builder.build()
        widgets = card["cardsV2"][0]["card"]["sections"][0]["widgets"]
        
        assert widgets[0]["image"]["imageUrl"] == "https://example.com/image.png"
        assert widgets[0]["image"]["altText"] == "Test Image"
    
    def test_add_button(self):
        """Test adding button widget"""
        builder = CardBuilder()
        action = CardBuilder.action_open_link("https://example.com")
        builder.add_button("Click Me", action, icon="LINK")
        
        card = builder.build()
        widgets = card["cardsV2"][0]["card"]["sections"][0]["widgets"]
        
        assert widgets[0]["buttonList"]["buttons"][0]["text"] == "Click Me"
        assert "onClick" in widgets[0]["buttonList"]["buttons"][0]
    
    def test_add_button_row(self):
        """Test adding multiple buttons in a row"""
        builder = CardBuilder()
        buttons = [
            CardBuilder.create_button("Btn 1", CardBuilder.action_open_link("https://1.com")),
            CardBuilder.create_button("Btn 2", CardBuilder.action_open_link("https://2.com"))
        ]
        builder.add_button_row(buttons)
        
        card = builder.build()
        widgets = card["cardsV2"][0]["card"]["sections"][0]["widgets"]
        
        assert len(widgets[0]["buttonList"]["buttons"]) == 2
    
    def test_add_key_value(self):
        """Test adding key-value widget"""
        builder = CardBuilder()
        builder.add_key_value("Key", "Value", icon="PERSON")
        
        card = builder.build()
        widgets = card["cardsV2"][0]["card"]["sections"][0]["widgets"]
        
        assert widgets[0]["keyValue"]["topLabel"] == "Key"
        assert widgets[0]["keyValue"]["content"] == "Value"
    
    def test_add_divider(self):
        """Test adding divider widget"""
        builder = CardBuilder()
        builder.add_divider()
        
        card = builder.build()
        widgets = card["cardsV2"][0]["card"]["sections"][0]["widgets"]
        
        assert "divider" in widgets[0]
    
    def test_add_input(self):
        """Test adding text input widget"""
        builder = CardBuilder()
        builder.add_input("field_name", "Field Label", placeholder="Type here...")
        
        card = builder.build()
        widgets = card["cardsV2"][0]["card"]["sections"][0]["widgets"]
        
        assert widgets[0]["textInput"]["name"] == "field_name"
        assert widgets[0]["textInput"]["label"] == "Field Label"
        assert widgets[0]["textInput"]["placeholderText"] == "Type here..."
    
    def test_add_selection_input(self):
        """Test adding selection input widget"""
        builder = CardBuilder()
        items = [
            CardBuilder.create_selection_item("Option 1", "opt1"),
            CardBuilder.create_selection_item("Option 2", "opt2", selected=True)
        ]
        builder.add_selection_input("choice", "Select:", items)
        
        card = builder.build()
        widgets = card["cardsV2"][0]["card"]["sections"][0]["widgets"]
        
        assert widgets[0]["selectionInput"]["name"] == "choice"
        assert len(widgets[0]["selectionInput"]["items"]) == 2
    
    def test_static_action_methods(self):
        """Test static action helper methods"""
        link_action = CardBuilder.action_open_link("https://example.com")
        assert link_action["action"]["link"]["url"] == "https://example.com"
        
        func_action = CardBuilder.action_run_function("my_func", {"key": "value"})
        assert func_action["action"]["function"] == "my_func"
        assert func_action["action"]["parameters"]["key"] == "value"


# ============================================================================
# ChatMessage Tests
# ============================================================================

class TestChatMessage:
    """Test the ChatMessage dataclass"""
    
    def test_message_creation(self):
        """Test creating a ChatMessage"""
        message = ChatMessage(
            message_id="spaces/ABC/messages/DEF",
            text="Hello",
            sender={"name": "users/123", "email": "test@example.com"},
            space={"name": "spaces/ABC", "spaceType": "SPACE"},
            thread={"name": "spaces/ABC/threads/XYZ"}
        )
        
        assert message.message_id == "spaces/ABC/messages/DEF"
        assert message.text == "Hello"
        assert message.user_email == "test@example.com"
        assert message.space_name == "spaces/ABC"
        assert message.thread_name == "spaces/ABC/threads/XYZ"
        assert message.is_group_space == True
        assert message.is_direct_message == False
    
    def test_direct_message_detection(self):
        """Test DM detection"""
        dm_message = ChatMessage(
            message_id="spaces/DEF/messages/GHI",
            text="Hello",
            sender={"name": "users/123"},
            space={"name": "spaces/DEF", "spaceType": "DIRECT_MESSAGE"}
        )
        
        assert dm_message.is_direct_message == True
        assert dm_message.is_group_space == False


# ============================================================================
# SlashCommand Tests
# ============================================================================

class TestSlashCommand:
    """Test SlashCommand functionality"""
    
    def test_slash_command_extraction(self):
        """Test extracting slash command from message"""
        message = ChatMessage(
            message_id="test",
            text="/help",
            sender={},
            space={},
            slash_command={
                "commandId": "1",
                "commandName": "/help"
            },
            argument_text="topic"
        )
        
        slash = SlashCommand.from_message(message)
        
        assert slash is not None
        assert slash.command_id == "1"
        assert slash.command_name == "/help"
        assert slash.arguments == "topic"
    
    def test_no_slash_command(self):
        """Test message without slash command"""
        message = ChatMessage(
            message_id="test",
            text="Hello",
            sender={},
            space={}
        )
        
        slash = SlashCommand.from_message(message)
        
        assert slash is None


# ============================================================================
# GoogleChatBot Tests
# ============================================================================

class TestGoogleChatBot:
    """Test the main GoogleChatBot class"""
    
    @pytest.mark.asyncio
    async def test_bot_initialization(self, mock_config):
        """Test bot initializes correctly"""
        bot = GoogleChatBot(mock_config)
        
        assert bot.config["bot_name"] == "TestBot"
        assert ChatEventType.MESSAGE in bot._handlers
        assert len(bot._handlers[ChatEventType.MESSAGE]) == 0
    
    @pytest.mark.asyncio
    async def test_event_handler_registration(self, mock_config):
        """Test registering event handlers"""
        bot = GoogleChatBot(mock_config)
        
        @bot.on_event(ChatEventType.MESSAGE)
        async def handler(data):
            pass
        
        assert len(bot._handlers[ChatEventType.MESSAGE]) == 1
    
    @pytest.mark.asyncio
    async def test_slash_command_registration(self, mock_config):
        """Test registering slash command handlers"""
        bot = GoogleChatBot(mock_config)
        
        @bot.on_slash_command("/test")
        async def handler(message, args):
            return {"text": "Test"}
        
        assert "/test" in bot._slash_handlers
    
    @pytest.mark.asyncio
    async def test_card_click_registration(self, mock_config):
        """Test registering card click handlers"""
        bot = GoogleChatBot(mock_config)
        
        @bot.on_card_click("action_name")
        async def handler(params, event):
            return {"text": "Clicked"}
        
        assert "action_name" in bot._card_handlers
    
    @pytest.mark.asyncio
    async def test_handle_message_event(self, mock_config, sample_message_data):
        """Test handling MESSAGE event"""
        bot = GoogleChatBot(mock_config)
        
        handler_called = False
        
        @bot.on_event(ChatEventType.MESSAGE)
        async def message_handler(message):
            nonlocal handler_called
            handler_called = True
            assert isinstance(message, ChatMessage)
            assert message.text == "Hello bot"
        
        response = await bot.handle_event(sample_message_data)
        
        assert handler_called == True
        assert "text" in response
    
    @pytest.mark.asyncio
    async def test_handle_dm_message(self, mock_config, sample_dm_message_data):
        """Test handling direct message"""
        bot = GoogleChatBot(mock_config)
        
        response = await bot.handle_event(sample_dm_message_data)
        
        assert "text" in response
        assert "Hello" in response["text"]
    
    @pytest.mark.asyncio
    async def test_handle_slash_command(self, mock_config, sample_slash_command_data):
        """Test handling slash command"""
        bot = GoogleChatBot(mock_config)
        
        @bot.on_slash_command("/help")
        async def help_handler(message, args):
            return {"text": "Help message"}
        
        response = await bot.handle_event(sample_slash_command_data)
        
        assert response["text"] == "Help message"
    
    @pytest.mark.asyncio
    async def test_handle_unknown_slash_command(self, mock_config, sample_slash_command_data):
        """Test handling unknown slash command"""
        bot = GoogleChatBot(mock_config)
        
        # Change to unknown command
        sample_slash_command_data["message"]["slashCommand"]["commandName"] = "/unknown"
        
        response = await bot.handle_event(sample_slash_command_data)
        
        assert "Unknown command" in response["text"]
    
    @pytest.mark.asyncio
    async def test_handle_added_to_space(self, mock_config, sample_added_to_space_data):
        """Test handling ADDED_TO_SPACE event"""
        bot = GoogleChatBot(mock_config)
        
        handler_called = False
        
        @bot.on_event(ChatEventType.ADDED_TO_SPACE)
        async def added_handler(data):
            nonlocal handler_called
            handler_called = True
        
        response = await bot.handle_event(sample_added_to_space_data)
        
        assert handler_called == True
        assert "cardsV2" in response  # Should return welcome card
    
    @pytest.mark.asyncio
    async def test_handle_removed_from_space(self, mock_config, sample_removed_from_space_data):
        """Test handling REMOVED_FROM_SPACE event"""
        bot = GoogleChatBot(mock_config)
        
        handler_called = False
        
        @bot.on_event(ChatEventType.REMOVED_FROM_SPACE)
        async def removed_handler(data):
            nonlocal handler_called
            handler_called = True
        
        response = await bot.handle_event(sample_removed_from_space_data)
        
        assert handler_called == True
        assert response == {}  # No response expected
    
    @pytest.mark.asyncio
    async def test_handle_card_click(self, mock_config, sample_card_click_data):
        """Test handling CARD_CLICKED event"""
        bot = GoogleChatBot(mock_config)
        
        @bot.on_card_click("complete_task")
        async def click_handler(params, event):
            return {"text": f"Task {params.get('task_id')} completed"}
        
        response = await bot.handle_event(sample_card_click_data)
        
        assert "Task 123 completed" in response["text"]
    
    @pytest.mark.asyncio
    async def test_handle_unknown_card_click(self, mock_config, sample_card_click_data):
        """Test handling unknown card click action"""
        bot = GoogleChatBot(mock_config)
        
        sample_card_click_data["action"]["actionMethodName"] = "unknown_action"
        
        response = await bot.handle_event(sample_card_click_data)
        
        assert "not implemented" in response["text"]
    
    @pytest.mark.asyncio
    async def test_handle_unknown_event_type(self, mock_config):
        """Test handling unknown event type"""
        bot = GoogleChatBot(mock_config)
        
        response = await bot.handle_event({"type": "UNKNOWN_EVENT"})
        
        assert "Unknown event type" in response["text"]


# ============================================================================
# GoogleChatTool Tests
# ============================================================================

class TestGoogleChatTool:
    """Test the GoogleChatTool class"""
    
    @pytest.mark.asyncio
    async def test_tool_initialization(self):
        """Test tool initializes correctly"""
        tool = GoogleChatTool()
        
        assert tool._initialized == False
        assert tool._bot is None
    
    @pytest.mark.asyncio
    async def test_tool_context_manager(self):
        """Test tool context manager"""
        with patch('cell0.engine.tools.google_chat.GoogleChatBot') as MockBot:
            mock_bot = AsyncMock()
            MockBot.return_value = mock_bot
            
            async with GoogleChatTool() as tool:
                assert tool._initialized == True
    
    @pytest.mark.asyncio
    async def test_create_task_card(self):
        """Test creating task card"""
        tool = GoogleChatTool()
        
        card = tool.create_task_card(
            task_title="Test Task",
            task_description="Test Description",
            task_id="123",
            status="in_progress",
            due_date="2024-12-31",
            assignee="Test User"
        )
        
        assert "cardsV2" in card
        card_data = card["cardsV2"][0]["card"]
        assert "Test Task" in card_data["header"]["title"]
    
    @pytest.mark.asyncio
    async def test_create_alert_card(self):
        """Test creating alert card"""
        tool = GoogleChatTool()
        
        card = tool.create_alert_card(
            alert_title="Test Alert",
            alert_message="Test Message",
            severity="warning",
            actions=[{"text": "Action", "url": "https://example.com"}]
        )
        
        assert "cardsV2" in card
        card_data = card["cardsV2"][0]["card"]
        assert "⚠️" in card_data["header"]["title"]
    
    @pytest.mark.asyncio
    async def test_create_status_card(self):
        """Test creating status card"""
        tool = GoogleChatTool()
        
        metrics = [
            {"name": "CPU", "value": "50%", "status": "good"},
            {"name": "Memory", "value": "80%", "status": "warning"}
        ]
        
        card = tool.create_status_card(
            system_name="Test System",
            status="operational",
            metrics=metrics,
            last_updated="2024-01-01 00:00"
        )
        
        assert "cardsV2" in card
        card_data = card["cardsV2"][0]["card"]
        assert "🟢" in card_data["header"]["title"]


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestIntegration:
    """Integration tests requiring actual Google Chat API"""
    
    @pytest.mark.skip(reason="Requires real Google Chat API credentials")
    @pytest.mark.asyncio
    async def test_send_message_integration(self):
        """Test sending a real message (requires credentials)"""
        async with GoogleChatTool() as tool:
            response = await tool.send_to_user(
                user_email="test@example.com",
                message="Integration test message",
                title="Test"
            )
            
            assert response.success == True


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
