"""
Signal Tool for Cell 0 OS Agents

This module provides a standardized interface for agents to interact with Signal messaging.
It wraps the SignalBot functionality and exposes it through the Cell 0 tool system.

Usage:
    from engine.tools.signal import SignalTool
    
    tool = SignalTool()
    await tool.send_message("+1234567890", "Hello from agent!")
"""

import asyncio
import base64
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Try to import SignalBot, fallback to mock if not available
try:
    from integrations.signal_bot import SignalBot, SignalMessage, SignalAttachment, ReactionEmoji
    SIGNAL_AVAILABLE = True
except ImportError:
    SIGNAL_AVAILABLE = False
    # Define mock classes for type hints
    class SignalMessage:
        pass
    class SignalAttachment:
        pass
    class ReactionEmoji:
        LIKE = "👍"

logger = logging.getLogger(__name__)


class SignalTool:
    """
    Signal Tool for Cell 0 OS Agents.
    
    Provides a standardized interface for sending and receiving Signal messages,
    managing groups, and handling reactions/quotes.
    
    Attributes:
        bot: The underlying SignalBot instance
        enabled: Whether Signal integration is available
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Signal Tool.
        
        Args:
            config_path: Path to signal_config.yaml (optional)
        """
        self.enabled = SIGNAL_AVAILABLE
        self._bot: Optional[Any] = None
        self._config_path = config_path
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._handlers: List[callable] = []
        
        if not self.enabled:
            logger.warning("Signal bot not available. Install signal-cli-rest-api for full functionality.")
    
    async def initialize(self) -> bool:
        """
        Initialize the Signal connection.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            self._bot = SignalBot(self._config_path)
            await self._bot.start()
            
            # Register message handler
            self._bot.on_message(self._on_message)
            
            logger.info("Signal tool initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Signal tool: {e}")
            self.enabled = False
            return False
    
    async def shutdown(self):
        """Shutdown the Signal connection."""
        if self._bot:
            await self._bot.stop()
            self._bot = None
            logger.info("Signal tool shutdown")
    
    # ==================== Core Messaging ====================
    
    async def send_message(
        self,
        recipient: str,
        text: str,
        attachments: Optional[List[Union[str, Path]]] = None,
        reply_to: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message to a recipient.
        
        Args:
            recipient: Phone number (e.g., "+1234567890") or group ID
            text: Message text content
            attachments: Optional list of file paths to attach
            reply_to: Optional dict with 'timestamp' and 'author' for quoting
            
        Returns:
            Response dict with 'success' and 'timestamp' keys
            
        Example:
            >>> await tool.send_message("+1234567890", "Hello!")
            {'success': True, 'timestamp': 1234567890}
        """
        if not self.enabled:
            return {'success': False, 'error': 'Signal not available'}
        
        try:
            # Convert file paths to attachments
            signal_attachments = None
            if attachments:
                signal_attachments = [
                    SignalAttachment.from_file(str(path))
                    for path in attachments
                ]
            
            # Send the message
            result = await self._bot.send_message(
                recipient=recipient,
                text=text,
                attachments=signal_attachments,
                quote_timestamp=reply_to.get('timestamp') if reply_to else None,
                quote_author=reply_to.get('author') if reply_to else None
            )
            
            return {
                'success': True,
                'timestamp': result.get('timestamp'),
                'message_id': result.get('timestamp')
            }
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {'success': False, 'error': str(e)}
    
    async def send_file(
        self,
        recipient: str,
        filepath: Union[str, Path],
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a file to a recipient.
        
        Args:
            recipient: Phone number or group ID
            filepath: Path to file to send
            caption: Optional caption for the file
            
        Returns:
            Response dict with 'success' status
            
        Example:
            >>> await tool.send_file("+1234567890", "/path/to/photo.jpg", "My photo")
        """
        if not self.enabled:
            return {'success': False, 'error': 'Signal not available'}
        
        try:
            attachment = SignalAttachment.from_file(str(filepath), caption)
            result = await self._bot.send_attachment(recipient, attachment, caption)
            
            return {
                'success': True,
                'timestamp': result.get('timestamp')
            }
            
        except Exception as e:
            logger.error(f"Failed to send file: {e}")
            return {'success': False, 'error': str(e)}
    
    async def send_reaction(
        self,
        recipient: str,
        message_timestamp: int,
        message_author: str,
        emoji: str
    ) -> Dict[str, Any]:
        """
        Send a reaction to a message.
        
        Args:
            recipient: Phone number or group ID of the conversation
            message_timestamp: Timestamp of the message to react to
            message_author: Phone number of the message author
            emoji: Emoji reaction (e.g., "👍", "❤️", "😂")
            
        Returns:
            Response dict with 'success' status
            
        Example:
            >>> await tool.send_reaction("+1234567890", 1234567890, "+0987654321", "👍")
        """
        if not self.enabled:
            return {'success': False, 'error': 'Signal not available'}
        
        try:
            result = await self._bot.send_reaction(
                recipient=recipient,
                target_timestamp=message_timestamp,
                target_author=message_author,
                emoji=emoji
            )
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Failed to send reaction: {e}")
            return {'success': False, 'error': str(e)}
    
    async def reply_to_message(
        self,
        recipient: str,
        original_message: Dict[str, Any],
        reply_text: str,
        attachments: Optional[List[Union[str, Path]]] = None
    ) -> Dict[str, Any]:
        """
        Reply to a specific message with a quote.
        
        Args:
            recipient: Phone number or group ID
            original_message: Dict with 'timestamp' and 'source' keys
            reply_text: Reply text
            attachments: Optional file attachments
            
        Returns:
            Response dict with 'success' status
            
        Example:
            >>> await tool.reply_to_message(
            ...     "+1234567890",
            ...     {'timestamp': 1234567890, 'source': '+0987654321'},
            ...     "This is my reply"
            ... )
        """
        if not self.enabled:
            return {'success': False, 'error': 'Signal not available'}
        
        try:
            # Convert file paths to attachments
            signal_attachments = None
            if attachments:
                signal_attachments = [
                    SignalAttachment.from_file(str(path))
                    for path in attachments
                ]
            
            result = await self._bot.send_message(
                recipient=recipient,
                text=reply_text,
                attachments=signal_attachments,
                quote_timestamp=original_message.get('timestamp'),
                quote_author=original_message.get('source')
            )
            
            return {
                'success': True,
                'timestamp': result.get('timestamp')
            }
            
        except Exception as e:
            logger.error(f"Failed to reply: {e}")
            return {'success': False, 'error': str(e)}
    
    # ==================== Group Management ====================
    
    async def list_groups(self) -> List[Dict[str, Any]]:
        """
        List all joined Signal groups.
        
        Returns:
            List of group dicts with 'id', 'name', 'members' keys
            
        Example:
            >>> groups = await tool.list_groups()
            [{'id': 'group_id', 'name': 'My Group', 'members': ['+1...', '+2...']}, ...]
        """
        if not self.enabled:
            return []
        
        try:
            groups = await self._bot.get_groups()
            return [
                {
                    'id': g.id,
                    'name': g.name,
                    'members': g.members,
                    'admins': g.admins,
                    'message_expiration': g.message_expiration
                }
                for g in groups
            ]
            
        except Exception as e:
            logger.error(f"Failed to list groups: {e}")
            return []
    
    async def create_group(
        self,
        name: str,
        members: List[str],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Signal group.
        
        Args:
            name: Group name
            members: List of phone numbers to add
            description: Optional group description
            
        Returns:
            Response dict with 'success' and 'group_id' keys
        """
        if not self.enabled:
            return {'success': False, 'error': 'Signal not available'}
        
        try:
            group = await self._bot.create_group(name, members, description)
            return {
                'success': True,
                'group_id': group.id,
                'name': group.name
            }
            
        except Exception as e:
            logger.error(f"Failed to create group: {e}")
            return {'success': False, 'error': str(e)}
    
    async def send_group_message(
        self,
        group_id: str,
        text: str,
        attachments: Optional[List[Union[str, Path]]] = None
    ) -> Dict[str, Any]:
        """
        Send a message to a Signal group.
        
        Args:
            group_id: Signal group ID
            text: Message text
            attachments: Optional file attachments
            
        Returns:
            Response dict with 'success' status
        """
        return await self.send_message(group_id, text, attachments)
    
    # ==================== Message Receiving ====================
    
    async def receive_messages(self) -> List[Dict[str, Any]]:
        """
        Receive pending messages.
        
        Returns:
            List of message dicts
            
        Example:
            >>> messages = await tool.receive_messages()
            [{
                'id': '123',
                'source': '+1234567890',
                'text': 'Hello!',
                'timestamp': 1234567890,
                'is_group': False,
                'group_id': None
            }, ...]
        """
        if not self.enabled:
            return []
        
        try:
            messages = await self._bot.receive_messages()
            return [
                {
                    'id': m.id,
                    'source': m.source,
                    'source_name': m.source_name,
                    'text': m.text,
                    'timestamp': m.timestamp,
                    'is_group': m.is_group_message,
                    'group_id': m.group_id,
                    'is_reaction': m.is_reaction,
                    'reaction_emoji': m.reaction_emoji,
                    'is_quote': m.is_quote,
                    'quote_text': m.quote_text,
                    'attachments': [
                        {'filename': a.filename, 'size': len(a.data)}
                        for a in m.attachments
                    ]
                }
                for m in messages
            ]
            
        except Exception as e:
            logger.error(f"Failed to receive messages: {e}")
            return []
    
    def on_message(self, handler: callable):
        """
        Register a message handler callback.
        
        Args:
            handler: Async or sync function that takes a message dict
            
        Example:
            >>> @tool.on_message
            ... async def handle(msg):
            ...     print(f"Received: {msg['text']}")
        """
        self._handlers.append(handler)
    
    def _on_message(self, message: SignalMessage):
        """Internal message handler."""
        msg_dict = {
            'id': message.id,
            'source': message.source,
            'source_name': message.source_name,
            'text': message.text,
            'timestamp': message.timestamp,
            'is_group': message.is_group_message,
            'group_id': message.group_id,
            'is_reaction': message.is_reaction,
            'reaction_emoji': message.reaction_emoji,
            'is_quote': message.is_quote,
            'quote_text': message.quote_text,
        }
        
        for handler in self._handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(msg_dict))
                else:
                    handler(msg_dict)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
    
    # ==================== Utility Methods ====================
    
    async def get_contacts(self) -> List[Dict[str, Any]]:
        """
        Get list of Signal contacts.
        
        Returns:
            List of contact dicts with 'number' and 'name' keys
        """
        if not self.enabled:
            return []
        
        try:
            return await self._bot.get_contacts()
        except Exception as e:
            logger.error(f"Failed to get contacts: {e}")
            return []
    
    async def set_typing_indicator(
        self,
        recipient: str,
        is_typing: bool = True
    ) -> bool:
        """
        Send typing indicator to a recipient.
        
        Args:
            recipient: Phone number or group ID
            is_typing: True to show typing, False to stop
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        try:
            return await self._bot.send_typing_indicator(recipient, is_typing)
        except Exception as e:
            logger.error(f"Failed to send typing indicator: {e}")
            return False
    
    async def send_link_preview(
        self,
        recipient: str,
        text: str,
        url: str,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a message with link preview.
        
        Args:
            recipient: Phone number or group ID
            text: Message text (should contain URL)
            url: URL to preview
            title: Preview title
            description: Preview description
            
        Returns:
            Response dict with 'success' status
        """
        if not self.enabled:
            return {'success': False, 'error': 'Signal not available'}
        
        try:
            result = await self._bot.send_message_with_link_preview(
                recipient, text, url, title, description
            )
            return {'success': True}
        except Exception as e:
            logger.error(f"Failed to send link preview: {e}")
            return {'success': False, 'error': str(e)}
    
    # ==================== Cell 0 Integration ====================
    
    async def publish_to_event_bus(self, message: Dict[str, Any]):
        """
        Publish a message to the Cell 0 event bus.
        
        This integrates Signal messages with the Cell 0 OS event system,
        allowing agents to respond to Signal events.
        """
        # This would integrate with the Cell 0 event bus
        # Implementation depends on the event bus interface
        pass
    
    def get_capabilities(self) -> List[str]:
        """
        Get list of capabilities provided by this tool.
        
        Returns:
            List of capability tokens for SYPAS
        """
        if not self.enabled:
            return []
        
        return [
            'messaging.signal.send',
            'messaging.signal.receive',
            'messaging.signal.groups',
            'messaging.signal.attachments',
            'messaging.signal.reactions',
            'messaging.signal.quotes',
        ]


# ==================== Quick Functions ====================

async def quick_send(recipient: str, text: str) -> bool:
    """
    Quick function to send a Signal message without managing tool lifecycle.
    
    Args:
        recipient: Phone number or group ID
        text: Message text
        
    Returns:
        True if sent successfully
    """
    tool = SignalTool()
    if await tool.initialize():
        try:
            result = await tool.send_message(recipient, text)
            return result.get('success', False)
        finally:
            await tool.shutdown()
    return False


async def quick_send_file(recipient: str, filepath: str, caption: str = "") -> bool:
    """
    Quick function to send a file via Signal.
    
    Args:
        recipient: Phone number or group ID
        filepath: Path to file
        caption: Optional caption
        
    Returns:
        True if sent successfully
    """
    tool = SignalTool()
    if await tool.initialize():
        try:
            result = await tool.send_file(recipient, filepath, caption)
            return result.get('success', False)
        finally:
            await tool.shutdown()
    return False
