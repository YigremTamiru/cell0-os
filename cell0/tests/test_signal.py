"""
Tests for Signal Integration in Cell 0 OS

This module contains comprehensive tests for the Signal bot integration,
covering messaging, groups, reactions, and all supported features.

Run tests:
    pytest tests/test_signal.py -v

Run with coverage:
    pytest tests/test_signal.py --cov=integrations.signal_bot --cov=engine.tools.signal -v
"""

import asyncio
import base64
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import yaml

# Import modules to test
try:
    from integrations.signal_bot import (
        SignalBot,
        SignalMessage,
        SignalAttachment,
        SignalGroup,
        MessageType,
        ReactionEmoji,
    )
    from engine.tools.signal import SignalTool
    SIGNAL_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import Signal modules: {e}")
    SIGNAL_AVAILABLE = False


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return {
        'signal_cli_url': 'http://localhost:8080',
        'phone_number': '+1234567890',
        'api_version': 'v1',
        'auto_receive': False,
        'message_cache_size': 100,
    }


@pytest.fixture
def mock_config_file(tmp_path, mock_config):
    """Create a temporary config file."""
    config_path = tmp_path / "signal_config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(mock_config, f)
    return str(config_path)


@pytest.fixture
def mock_attachment():
    """Create a mock attachment."""
    return SignalAttachment(
        filename="test.txt",
        content_type="text/plain",
        data=b"Test content",
        caption="Test caption"
    )


@pytest.fixture
def mock_message():
    """Create a mock Signal message."""
    return SignalMessage(
        id="1234567890",
        source="+0987654321",
        source_name="Test User",
        timestamp=1234567890,
        message_type=MessageType.TEXT,
        text="Hello, World!",
        raw_data={}
    )


# ==================== SignalAttachment Tests ====================

@pytest.mark.skipif(not SIGNAL_AVAILABLE, reason="Signal modules not available")
class TestSignalAttachment:
    """Test cases for SignalAttachment class."""
    
    def test_from_file(self, tmp_path):
        """Test creating attachment from file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        attachment = SignalAttachment.from_file(str(test_file), "Test caption")
        
        assert attachment.filename == "test.txt"
        assert attachment.content_type == "text/plain"
        assert attachment.data == b"Test content"
        assert attachment.caption == "Test caption"
    
    def test_from_base64(self):
        """Test creating attachment from base64."""
        content = b"Test content"
        b64_data = base64.b64encode(content).decode('utf-8')
        
        attachment = SignalAttachment.from_base64(
            filename="test.bin",
            content_type="application/octet-stream",
            base64_data=b64_data
        )
        
        assert attachment.filename == "test.bin"
        assert attachment.content_type == "application/octet-stream"
        assert attachment.data == content
    
    def test_to_base64(self, mock_attachment):
        """Test converting attachment to base64."""
        b64 = mock_attachment.to_base64()
        expected = base64.b64encode(b"Test content").decode('utf-8')
        assert b64 == expected
    
    @pytest.mark.parametrize("extension,expected_type", [
        (".jpg", "image/jpeg"),
        (".jpeg", "image/jpeg"),
        (".png", "image/png"),
        (".gif", "image/gif"),
        (".mp4", "video/mp4"),
        (".pdf", "application/pdf"),
        (".unknown", "application/octet-stream"),
    ])
    def test_guess_content_type(self, extension, expected_type):
        """Test MIME type guessing from file extension."""
        result = SignalAttachment._guess_content_type(extension)
        assert result == expected_type


# ==================== SignalMessage Tests ====================

@pytest.mark.skipif(not SIGNAL_AVAILABLE, reason="Signal modules not available")
class TestSignalMessage:
    """Test cases for SignalMessage class."""
    
    def test_is_group_message(self, mock_message):
        """Test group message detection."""
        assert not mock_message.is_group_message
        
        group_message = SignalMessage(
            id="1",
            source="+1",
            group_id="group123",
            raw_data={}
        )
        assert group_message.is_group_message
    
    def test_is_reaction(self, mock_message):
        """Test reaction message detection."""
        assert not mock_message.is_reaction
        
        reaction_message = SignalMessage(
            id="1",
            source="+1",
            message_type=MessageType.REACTION,
            reaction_emoji="👍",
            raw_data={}
        )
        assert reaction_message.is_reaction
    
    def test_is_quote(self, mock_message):
        """Test quote message detection."""
        assert not mock_message.is_quote
        
        quote_message = SignalMessage(
            id="1",
            source="+1",
            quote_timestamp=1234567890,
            quote_author="+2",
            quote_text="Original message",
            raw_data={}
        )
        assert quote_message.is_quote


# ==================== SignalBot Tests ====================

@pytest.mark.skipif(not SIGNAL_AVAILABLE, reason="Signal modules not available")
class TestSignalBot:
    """Test cases for SignalBot class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_config_file):
        """Test bot initialization."""
        bot = SignalBot(mock_config_file)
        
        assert bot.config is not None
        assert bot.base_url == "http://localhost:8080"
        assert bot.phone_number == "+1234567890"
    
    @pytest.mark.asyncio
    async def test_load_config_default(self):
        """Test loading default configuration."""
        bot = SignalBot(config_path="/nonexistent/path.yaml")
        
        assert bot.config.get('signal_cli_url') == "http://localhost:8080"
        assert bot.config.get('api_version') == "v1"
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_config_file):
        """Test successful health check."""
        bot = SignalBot(mock_config_file)
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        with patch.object(bot, 'session') as mock_session:
            mock_session.get = AsyncMock(return_value=mock_response)
            
            result = await bot._health_check()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_config_file):
        """Test failed health check."""
        bot = SignalBot(mock_config_file)
        
        with patch.object(bot, 'session') as mock_session:
            mock_session.get = AsyncMock(side_effect=Exception("Connection failed"))
            
            result = await bot._health_check()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_message(self, mock_config_file):
        """Test sending a message."""
        bot = SignalBot(mock_config_file)
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={'timestamp': 1234567890})
        
        with patch.object(bot, 'session') as mock_session:
            mock_session.post = AsyncMock(return_value=mock_response)
            
            result = await bot.send_message("+0987654321", "Hello!")
            
            assert result['timestamp'] == 1234567890
            mock_session.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_with_attachments(self, mock_config_file, mock_attachment):
        """Test sending a message with attachments."""
        bot = SignalBot(mock_config_file)
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={'timestamp': 1234567890})
        
        with patch.object(bot, 'session') as mock_session:
            mock_session.post = AsyncMock(return_value=mock_response)
            
            result = await bot.send_message(
                "+0987654321",
                "Hello with attachment!",
                attachments=[mock_attachment]
            )
            
            assert result['timestamp'] == 1234567890
    
    @pytest.mark.asyncio
    async def test_send_reaction(self, mock_config_file):
        """Test sending a reaction."""
        bot = SignalBot(mock_config_file)
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={'success': True})
        
        with patch.object(bot, 'session') as mock_session:
            mock_session.post = AsyncMock(return_value=mock_response)
            
            result = await bot.send_reaction(
                "+0987654321",
                target_timestamp=1234567890,
                target_author="+0987654321",
                emoji="👍"
            )
            
            assert result['success'] is True
    
    @pytest.mark.asyncio
    async def test_reply_to_message(self, mock_config_file, mock_message):
        """Test replying to a message."""
        bot = SignalBot(mock_config_file)
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={'timestamp': 1234567891})
        
        with patch.object(bot, 'session') as mock_session:
            mock_session.post = AsyncMock(return_value=mock_response)
            
            result = await bot.reply_to_message(
                "+0987654321",
                mock_message,
                "This is a reply"
            )
            
            assert result['timestamp'] == 1234567891
    
    @pytest.mark.asyncio
    async def test_get_groups(self, mock_config_file):
        """Test getting groups list."""
        bot = SignalBot(mock_config_file)
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[
            {
                'id': 'group1',
                'name': 'Test Group',
                'members': ['+1', '+2'],
                'admins': ['+1'],
                'blocked': False,
                'muted': False,
                'messageExpirationTime': 0
            }
        ])
        
        with patch.object(bot, 'session') as mock_session:
            mock_session.get = AsyncMock(return_value=mock_response)
            
            groups = await bot.get_groups()
            
            assert len(groups) == 1
            assert groups[0].id == 'group1'
            assert groups[0].name == 'Test Group'
    
    @pytest.mark.asyncio
    async def test_parse_envelope_text_message(self, mock_config_file):
        """Test parsing a text message envelope."""
        bot = SignalBot(mock_config_file)
        
        envelope = {
            'source': '+0987654321',
            'sourceName': 'Test User',
            'timestamp': 1234567890,
            'dataMessage': {
                'message': 'Hello!',
                'attachments': []
            }
        }
        
        message = bot._parse_envelope(envelope)
        
        assert message is not None
        assert message.source == '+0987654321'
        assert message.text == 'Hello!'
        assert message.message_type == MessageType.TEXT
    
    @pytest.mark.asyncio
    async def test_parse_envelope_reaction(self, mock_config_file):
        """Test parsing a reaction envelope."""
        bot = SignalBot(mock_config_file)
        
        envelope = {
            'source': '+0987654321',
            'timestamp': 1234567890,
            'dataMessage': {
                'reaction': {
                    'emoji': '👍',
                    'targetAuthor': '+1234567890',
                    'targetTimestamp': 1234567880
                }
            }
        }
        
        message = bot._parse_envelope(envelope)
        
        assert message is not None
        assert message.is_reaction
        assert message.reaction_emoji == '👍'
    
    @pytest.mark.asyncio
    async def test_parse_envelope_group_message(self, mock_config_file):
        """Test parsing a group message envelope."""
        bot = SignalBot(mock_config_file)
        
        envelope = {
            'source': '+0987654321',
            'timestamp': 1234567890,
            'dataMessage': {
                'message': 'Hello group!',
                'groupInfo': {
                    'groupId': 'group123'
                }
            }
        }
        
        message = bot._parse_envelope(envelope)
        
        assert message is not None
        assert message.is_group_message
        assert message.group_id == 'group123'
    
    @pytest.mark.asyncio
    async def test_message_handler_registration(self, mock_config_file):
        """Test message handler registration."""
        bot = SignalBot(mock_config_file)
        
        @bot.on_message
        def handler(message):
            pass
        
        assert handler in bot.message_handlers
        
        bot.remove_handler(handler)
        assert handler not in bot.message_handlers
    
    @pytest.mark.asyncio
    async def test_message_cache(self, mock_config_file, mock_message):
        """Test message caching."""
        bot = SignalBot(mock_config_file)
        
        bot._cache_message(mock_message)
        
        cached = bot.get_cached_message(mock_message.source, mock_message.timestamp)
        assert cached == mock_message
    
    @pytest.mark.asyncio
    async def test_cache_size_limit(self, mock_config_file):
        """Test cache size limiting."""
        bot = SignalBot(mock_config_file)
        bot._cache_size = 5
        
        # Add more messages than cache size
        for i in range(10):
            msg = SignalMessage(
                id=str(i),
                source="+1",
                timestamp=i,
                raw_data={}
            )
            bot._cache_message(msg)
        
        # Cache should have been trimmed
        assert len(bot._message_cache) <= 5


# ==================== SignalTool Tests ====================

@pytest.mark.skipif(not SIGNAL_AVAILABLE, reason="Signal modules not available")
class TestSignalTool:
    """Test cases for SignalTool class."""
    
    @pytest.mark.asyncio
    async def test_tool_initialization(self, mock_config_file):
        """Test tool initialization."""
        tool = SignalTool(mock_config_file)
        
        assert tool.enabled == SIGNAL_AVAILABLE
        assert tool._config_path == mock_config_file
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_config_file):
        """Test successful message send."""
        tool = SignalTool(mock_config_file)
        
        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock(return_value={'timestamp': 1234567890})
        
        with patch.object(tool, '_bot', mock_bot):
            tool.enabled = True
            result = await tool.send_message("+0987654321", "Hello!")
            
            assert result['success'] is True
            assert result['timestamp'] == 1234567890
    
    @pytest.mark.asyncio
    async def test_send_message_disabled(self):
        """Test sending when tool is disabled."""
        tool = SignalTool()
        tool.enabled = False
        
        result = await tool.send_message("+0987654321", "Hello!")
        
        assert result['success'] is False
        assert 'not available' in result['error']
    
    @pytest.mark.asyncio
    async def test_send_file(self, mock_config_file, tmp_path):
        """Test sending a file."""
        tool = SignalTool(mock_config_file)
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        mock_bot = AsyncMock()
        mock_bot.send_attachment = AsyncMock(return_value={'timestamp': 1234567890})
        
        with patch.object(tool, '_bot', mock_bot):
            tool.enabled = True
            result = await tool.send_file("+0987654321", str(test_file), "Caption")
            
            assert result['success'] is True
    
    @pytest.mark.asyncio
    async def test_send_reaction(self, mock_config_file):
        """Test sending a reaction."""
        tool = SignalTool(mock_config_file)
        
        mock_bot = AsyncMock()
        mock_bot.send_reaction = AsyncMock(return_value={'success': True})
        
        with patch.object(tool, '_bot', mock_bot):
            tool.enabled = True
            result = await tool.send_reaction(
                "+0987654321",
                1234567890,
                "+0987654321",
                "👍"
            )
            
            assert result['success'] is True
    
    @pytest.mark.asyncio
    async def test_list_groups(self, mock_config_file):
        """Test listing groups."""
        tool = SignalTool(mock_config_file)
        
        mock_group = MagicMock()
        mock_group.id = 'group1'
        mock_group.name = 'Test Group'
        mock_group.members = ['+1', '+2']
        mock_group.admins = ['+1']
        mock_group.message_expiration = 0
        
        mock_bot = AsyncMock()
        mock_bot.get_groups = AsyncMock(return_value=[mock_group])
        
        with patch.object(tool, '_bot', mock_bot):
            tool.enabled = True
            groups = await tool.list_groups()
            
            assert len(groups) == 1
            assert groups[0]['id'] == 'group1'
    
    @pytest.mark.asyncio
    async def test_receive_messages(self, mock_config_file):
        """Test receiving messages."""
        tool = SignalTool(mock_config_file)
        
        mock_message = MagicMock()
        mock_message.id = '1'
        mock_message.source = '+0987654321'
        mock_message.source_name = 'Test'
        mock_message.text = 'Hello!'
        mock_message.timestamp = 1234567890
        mock_message.is_group_message = False
        mock_message.group_id = None
        mock_message.is_reaction = False
        mock_message.reaction_emoji = None
        mock_message.is_quote = False
        mock_message.quote_text = None
        mock_message.attachments = []
        
        mock_bot = AsyncMock()
        mock_bot.receive_messages = AsyncMock(return_value=[mock_message])
        
        with patch.object(tool, '_bot', mock_bot):
            tool.enabled = True
            messages = await tool.receive_messages()
            
            assert len(messages) == 1
            assert messages[0]['text'] == 'Hello!'
    
    @pytest.mark.asyncio
    async def test_get_capabilities(self, mock_config_file):
        """Test getting tool capabilities."""
        tool = SignalTool(mock_config_file)
        tool.enabled = True
        
        capabilities = tool.get_capabilities()
        
        assert 'messaging.signal.send' in capabilities
        assert 'messaging.signal.receive' in capabilities
        assert 'messaging.signal.groups' in capabilities


# ==================== Integration Tests ====================

@pytest.mark.skipif(not SIGNAL_AVAILABLE, reason="Signal modules not available")
@pytest.mark.integration
class TestSignalIntegration:
    """Integration tests requiring running signal-cli-rest-api."""
    
    @pytest.mark.asyncio
    async def test_full_message_flow(self):
        """Test complete message send/receive flow."""
        # This test requires a running signal-cli-rest-api instance
        # and a valid registered phone number
        pytest.skip("Requires running signal-cli-rest-api")
    
    @pytest.mark.asyncio
    async def test_group_operations(self):
        """Test group creation and messaging."""
        pytest.skip("Requires running signal-cli-rest-api")
    
    @pytest.mark.asyncio
    async def test_attachment_send_receive(self):
        """Test sending and receiving attachments."""
        pytest.skip("Requires running signal-cli-rest-api")


# ==================== Mock/Offline Tests ====================

class TestSignalOffline:
    """Tests that don't require signal-cli-rest-api."""
    
    @pytest.mark.asyncio
    async def test_quick_send_disabled(self):
        """Test quick send when Signal is not available."""
        from engine.tools.signal import quick_send
        
        with patch('engine.tools.signal.SIGNAL_AVAILABLE', False):
            result = await quick_send("+1234567890", "Hello!")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_quick_send_file_disabled(self):
        """Test quick file send when Signal is not available."""
        from engine.tools.signal import quick_send_file
        
        with patch('engine.tools.signal.SIGNAL_AVAILABLE', False):
            result = await quick_send_file("+1234567890", "/path/to/file.txt")
            assert result is False


# ==================== Main ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
