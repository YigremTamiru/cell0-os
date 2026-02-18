"""
Signal Bot Integration for Cell 0 OS

This module provides Signal messaging capabilities for Cell 0 OS,
using signal-cli-rest-api for communication with the Signal network.

Features:
- Send/receive text messages
- Send/receive attachments
- Group chat support
- Reaction support
- Quote/reply support
- Link preview handling

Author: Cell 0 OS
"""

import asyncio
import base64
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urljoin

import aiohttp
import yaml

# Configure logging
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Signal message types."""
    TEXT = "text"
    ATTACHMENT = "attachment"
    REACTION = "reaction"
    QUOTE = "quote"
    GROUP = "group"
    TYPING = "typing"
    RECEIPT = "receipt"


class ReactionEmoji(Enum):
    """Common Signal reaction emojis."""
    LIKE = "👍"
    DISLIKE = "👎"
    HEART = "❤️"
    LAUGH = "😂"
    WOW = "😮"
    SAD = "😢"
    ANGRY = "😠"


@dataclass
class SignalAttachment:
    """Represents a Signal attachment."""
    filename: str
    content_type: str
    data: bytes
    caption: Optional[str] = None
    
    @classmethod
    def from_file(cls, filepath: Union[str, Path], caption: Optional[str] = None) -> 'SignalAttachment':
        """Create attachment from file path."""
        filepath = Path(filepath)
        content_type = cls._guess_content_type(filepath.suffix)
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        return cls(
            filename=filepath.name,
            content_type=content_type,
            data=data,
            caption=caption
        )
    
    @classmethod
    def from_base64(cls, filename: str, content_type: str, base64_data: str, 
                    caption: Optional[str] = None) -> 'SignalAttachment':
        """Create attachment from base64 data."""
        data = base64.b64decode(base64_data)
        return cls(filename, content_type, data, caption)
    
    def to_base64(self) -> str:
        """Convert attachment to base64 string."""
        return base64.b64encode(self.data).decode('utf-8')
    
    @staticmethod
    def _guess_content_type(extension: str) -> str:
        """Guess MIME type from file extension."""
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mp3': 'audio/mpeg',
            '.ogg': 'audio/ogg',
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.json': 'application/json',
        }
        return mime_types.get(extension.lower(), 'application/octet-stream')


@dataclass
class SignalMessage:
    """Represents a Signal message."""
    id: str
    source: str  # Sender phone number
    source_name: Optional[str] = None
    timestamp: int = 0
    message_type: MessageType = MessageType.TEXT
    text: Optional[str] = None
    group_id: Optional[str] = None
    attachments: List[SignalAttachment] = field(default_factory=list)
    quote_timestamp: Optional[int] = None
    quote_author: Optional[str] = None
    quote_text: Optional[str] = None
    reaction_emoji: Optional[str] = None
    reaction_target_author: Optional[str] = None
    reaction_target_timestamp: Optional[int] = None
    is_read: bool = False
    is_delivered: bool = False
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_group_message(self) -> bool:
        """Check if this is a group message."""
        return self.group_id is not None
    
    @property
    def is_reaction(self) -> bool:
        """Check if this is a reaction message."""
        return self.message_type == MessageType.REACTION
    
    @property
    def is_quote(self) -> bool:
        """Check if this is a quote/reply message."""
        return self.quote_timestamp is not None


@dataclass
class SignalGroup:
    """Represents a Signal group."""
    id: str
    name: str
    members: List[str] = field(default_factory=list)
    admins: List[str] = field(default_factory=list)
    blocked: bool = False
    muted: bool = False
    message_expiration: int = 0  # Disappearing messages timer


class SignalBot:
    """
    Signal Bot for Cell 0 OS.
    
    Provides integration with Signal messaging via signal-cli-rest-api.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize Signal Bot with configuration."""
        self.config = self._load_config(config_path)
        self.base_url = self.config.get('signal_cli_url', 'http://localhost:8080')
        self.phone_number = self.config.get('phone_number', '')
        self.api_version = self.config.get('api_version', 'v1')
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.message_handlers: List[Callable[[SignalMessage], None]] = []
        self.receipt_handlers: List[Callable[[Dict], None]] = []
        self._receive_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Message cache for quote/reply support
        self._message_cache: Dict[str, SignalMessage] = {}
        self._cache_size = self.config.get('message_cache_size', 1000)
        
        logger.info(f"Signal Bot initialized for {self.phone_number}")
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from YAML file."""
        if config_path is None:
            # Try default locations
            default_paths = [
                'signal_config.yaml',
                '/Users/yigremgetachewtamiru/.openclaw/workspace/cell0/integrations/signal_config.yaml',
                '/etc/cell0/signal_config.yaml',
            ]
            for path in default_paths:
                if Path(path).exists():
                    config_path = path
                    break
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        
        # Return default configuration
        return {
            'signal_cli_url': 'http://localhost:8080',
            'phone_number': '',
            'api_version': 'v1',
            'auto_receive': True,
            'message_cache_size': 1000,
            'link_previews': True,
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
    
    async def start(self):
        """Start the Signal bot and create HTTP session."""
        if self.session is not None:
            return
        
        self.session = aiohttp.ClientSession(
            base_url=self.base_url,
            headers={'Content-Type': 'application/json'}
        )
        
        # Verify connection
        if not await self._health_check():
            raise ConnectionError("Cannot connect to signal-cli-rest-api")
        
        # Register message handlers
        if self.config.get('auto_receive', True):
            self._start_receive_loop()
        
        logger.info("Signal Bot started")
    
    async def stop(self):
        """Stop the Signal bot and cleanup."""
        self._running = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None
        
        if self.session:
            await self.session.close()
            self.session = None
        
        logger.info("Signal Bot stopped")
    
    async def _health_check(self) -> bool:
        """Check if signal-cli-rest-api is accessible."""
        try:
            async with self.session.get(f'/{self.api_version}/health') as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def _get_api_url(self, endpoint: str) -> str:
        """Build API URL for endpoint."""
        return f"/{self.api_version}/{endpoint}"
    
    # ==================== Message Sending ====================
    
    async def send_message(
        self,
        recipient: str,
        text: str,
        attachments: Optional[List[SignalAttachment]] = None,
        quote_timestamp: Optional[int] = None,
        quote_author: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a text message to a recipient.
        
        Args:
            recipient: Phone number or group ID
            text: Message text
            attachments: Optional list of attachments
            quote_timestamp: Timestamp of message being quoted
            quote_author: Author of message being quoted
            
        Returns:
            API response dictionary
        """
        url = self._get_api_url(f"messages/{self.phone_number}")
        
        payload = {
            'recipient': [recipient],
            'message': text,
        }
        
        # Handle quote/reply
        if quote_timestamp and quote_author:
            payload['quote'] = {
                'timestamp': quote_timestamp,
                'author': quote_author,
                'text': text[:100] if text else ''  # Preview of quoted text
            }
        
        # Handle attachments
        if attachments:
            payload['base64_attachments'] = [
                f"data:{att.content_type};base64,{att.to_base64()}"
                for att in attachments
            ]
        
        async with self.session.post(url, json=payload) as resp:
            if resp.status == 200:
                result = await resp.json()
                logger.info(f"Message sent to {recipient}")
                return result
            else:
                error_text = await resp.text()
                raise RuntimeError(f"Failed to send message: {error_text}")
    
    async def send_group_message(
        self,
        group_id: str,
        text: str,
        attachments: Optional[List[SignalAttachment]] = None
    ) -> Dict[str, Any]:
        """Send a message to a Signal group."""
        # Group messages use the same endpoint but with group ID as recipient
        return await self.send_message(group_id, text, attachments)
    
    async def send_attachment(
        self,
        recipient: str,
        attachment: SignalAttachment,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an attachment to a recipient.
        
        Args:
            recipient: Phone number or group ID
            attachment: SignalAttachment to send
            caption: Optional caption for the attachment
            
        Returns:
            API response dictionary
        """
        text = caption or attachment.caption or ""
        return await self.send_message(recipient, text, [attachment])
    
    async def send_reaction(
        self,
        recipient: str,
        target_timestamp: int,
        target_author: str,
        emoji: str
    ) -> Dict[str, Any]:
        """
        Send a reaction to a message.
        
        Args:
            recipient: Phone number or group ID of the conversation
            target_timestamp: Timestamp of the message being reacted to
            target_author: Phone number of the message author
            emoji: Emoji reaction (use ReactionEmoji for common ones)
            
        Returns:
            API response dictionary
        """
        url = self._get_api_url(f"messages/{self.phone_number}")
        
        payload = {
            'recipient': [recipient],
            'reaction': {
                'emoji': emoji,
                'target_timestamp': target_timestamp,
                'target_author': target_author,
                'is_removal': False
            }
        }
        
        async with self.session.post(url, json=payload) as resp:
            if resp.status == 200:
                result = await resp.json()
                logger.info(f"Reaction sent to {recipient}")
                return result
            else:
                error_text = await resp.text()
                raise RuntimeError(f"Failed to send reaction: {error_text}")
    
    async def remove_reaction(
        self,
        recipient: str,
        target_timestamp: int,
        target_author: str
    ) -> Dict[str, Any]:
        """Remove a previously sent reaction."""
        url = self._get_api_url(f"messages/{self.phone_number}")
        
        payload = {
            'recipient': [recipient],
            'reaction': {
                'emoji': '',
                'target_timestamp': target_timestamp,
                'target_author': target_author,
                'is_removal': True
            }
        }
        
        async with self.session.post(url, json=payload) as resp:
            return await resp.json()
    
    async def reply_to_message(
        self,
        recipient: str,
        original_message: SignalMessage,
        reply_text: str,
        attachments: Optional[List[SignalAttachment]] = None
    ) -> Dict[str, Any]:
        """
        Reply to a specific message with quote.
        
        Args:
            recipient: Phone number or group ID
            original_message: The message being replied to
            reply_text: Reply text
            attachments: Optional attachments
            
        Returns:
            API response dictionary
        """
        return await self.send_message(
            recipient=recipient,
            text=reply_text,
            attachments=attachments,
            quote_timestamp=original_message.timestamp,
            quote_author=original_message.source
        )
    
    async def send_typing_indicator(self, recipient: str, is_typing: bool = True):
        """Send typing indicator to recipient."""
        url = self._get_api_url(f"typing-indicator/{self.phone_number}")
        
        payload = {
            'recipient': recipient,
            'typing': is_typing
        }
        
        async with self.session.post(url, json=payload) as resp:
            return resp.status == 200
    
    # ==================== Message Receiving ====================
    
    def _start_receive_loop(self):
        """Start the message receive loop."""
        if self._receive_task is None or self._receive_task.done():
            self._running = True
            self._receive_task = asyncio.create_task(self._receive_loop())
    
    async def _receive_loop(self):
        """Background loop to receive messages."""
        while self._running:
            try:
                await self.receive_messages()
                await asyncio.sleep(1)  # Poll every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def receive_messages(self) -> List[SignalMessage]:
        """
        Receive pending messages from Signal.
        
        Returns:
            List of received SignalMessage objects
        """
        url = self._get_api_url(f"receive/{self.phone_number}")
        
        async with self.session.get(url) as resp:
            if resp.status != 200:
                logger.warning(f"Failed to receive messages: {resp.status}")
                return []
            
            data = await resp.json()
            messages = []
            
            for envelope in data.get('envelopes', []):
                message = self._parse_envelope(envelope)
                if message:
                    messages.append(message)
                    self._cache_message(message)
                    await self._dispatch_message(message)
            
            return messages
    
    def _parse_envelope(self, envelope: Dict[str, Any]) -> Optional[SignalMessage]:
        """Parse a Signal envelope into a SignalMessage."""
        try:
            data_message = envelope.get('dataMessage', {})
            sync_message = envelope.get('syncMessage', {})
            
            # Handle different message types
            if not data_message and not sync_message:
                return None
            
            message_data = data_message if data_message else sync_message.get('sent', {})
            
            # Determine message type
            message_type = MessageType.TEXT
            
            if 'reaction' in message_data:
                message_type = MessageType.REACTION
            elif 'attachments' in message_data and message_data['attachments']:
                message_type = MessageType.ATTACHMENT
            elif 'groupInfo' in message_data:
                message_type = MessageType.GROUP
            
            # Build message object
            message = SignalMessage(
                id=envelope.get('timestamp', str(datetime.now().timestamp())),
                source=envelope.get('source', 'unknown'),
                source_name=envelope.get('sourceName'),
                timestamp=envelope.get('timestamp', 0),
                message_type=message_type,
                text=message_data.get('message'),
                group_id=self._extract_group_id(message_data),
                attachments=self._parse_attachments(message_data.get('attachments', [])),
                quote_timestamp=message_data.get('quote', {}).get('timestamp'),
                quote_author=message_data.get('quote', {}).get('author'),
                quote_text=message_data.get('quote', {}).get('text'),
                reaction_emoji=message_data.get('reaction', {}).get('emoji'),
                reaction_target_author=message_data.get('reaction', {}).get('targetAuthor'),
                reaction_target_timestamp=message_data.get('reaction', {}).get('targetTimestamp'),
                raw_data=envelope
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Error parsing envelope: {e}")
            return None
    
    def _extract_group_id(self, message_data: Dict) -> Optional[str]:
        """Extract group ID from message data."""
        group_info = message_data.get('groupInfo', {})
        return group_info.get('groupId')
    
    def _parse_attachments(self, attachments_data: List[Dict]) -> List[SignalAttachment]:
        """Parse attachment data into SignalAttachment objects."""
        attachments = []
        for att_data in attachments_data:
            try:
                attachment = SignalAttachment.from_base64(
                    filename=att_data.get('filename', 'attachment'),
                    content_type=att_data.get('contentType', 'application/octet-stream'),
                    base64_data=att_data.get('data', '')
                )
                attachments.append(attachment)
            except Exception as e:
                logger.warning(f"Failed to parse attachment: {e}")
        return attachments
    
    def _cache_message(self, message: SignalMessage):
        """Cache message for quote/reply support."""
        cache_key = f"{message.source}:{message.timestamp}"
        self._message_cache[cache_key] = message
        
        # Trim cache if needed
        if len(self._message_cache) > self._cache_size:
            # Remove oldest messages
            sorted_keys = sorted(
                self._message_cache.keys(),
                key=lambda k: self._message_cache[k].timestamp
            )
            for key in sorted_keys[:len(sorted_keys) // 2]:
                del self._message_cache[key]
    
    async def _dispatch_message(self, message: SignalMessage):
        """Dispatch message to registered handlers."""
        for handler in self.message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
    
    def on_message(self, handler: Callable[[SignalMessage], None]):
        """Register a message handler."""
        self.message_handlers.append(handler)
        return handler
    
    def remove_handler(self, handler: Callable[[SignalMessage], None]):
        """Remove a message handler."""
        if handler in self.message_handlers:
            self.message_handlers.remove(handler)
    
    # ==================== Group Management ====================
    
    async def get_groups(self) -> List[SignalGroup]:
        """Get list of all Signal groups."""
        url = self._get_api_url(f"groups/{self.phone_number}")
        
        async with self.session.get(url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Failed to get groups: {resp.status}")
            
            data = await resp.json()
            groups = []
            
            for group_data in data:
                group = SignalGroup(
                    id=group_data.get('id', ''),
                    name=group_data.get('name', 'Unknown'),
                    members=group_data.get('members', []),
                    admins=group_data.get('admins', []),
                    blocked=group_data.get('blocked', False),
                    muted=group_data.get('muted', False),
                    message_expiration=group_data.get('messageExpirationTime', 0)
                )
                groups.append(group)
            
            return groups
    
    async def create_group(
        self,
        name: str,
        members: List[str],
        description: Optional[str] = None
    ) -> SignalGroup:
        """Create a new Signal group."""
        url = self._get_api_url(f"groups/{self.phone_number}")
        
        payload = {
            'name': name,
            'members': members,
        }
        
        if description:
            payload['description'] = description
        
        async with self.session.post(url, json=payload) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Failed to create group: {await resp.text()}")
            
            data = await resp.json()
            return SignalGroup(
                id=data.get('id', ''),
                name=name,
                members=members
            )
    
    async def update_group(
        self,
        group_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        add_members: Optional[List[str]] = None,
        remove_members: Optional[List[str]] = None
    ) -> bool:
        """Update group settings."""
        url = self._get_api_url(f"groups/{self.phone_number}/{group_id}")
        
        payload = {}
        if name:
            payload['name'] = name
        if description:
            payload['description'] = description
        if add_members:
            payload['add_members'] = add_members
        if remove_members:
            payload['remove_members'] = remove_members
        
        async with self.session.put(url, json=payload) as resp:
            return resp.status == 200
    
    async def leave_group(self, group_id: str) -> bool:
        """Leave a Signal group."""
        url = self._get_api_url(f"groups/{self.phone_number}/{group_id}")
        
        async with self.session.delete(url) as resp:
            return resp.status == 200
    
    # ==================== Link Previews ====================
    
    async def send_message_with_link_preview(
        self,
        recipient: str,
        text: str,
        url: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        image_attachment: Optional[SignalAttachment] = None
    ) -> Dict[str, Any]:
        """
        Send a message with link preview.
        
        Args:
            recipient: Phone number or group ID
            text: Message text (should contain the URL)
            url: URL for the preview
            title: Preview title
            description: Preview description
            image_attachment: Optional preview image
            
        Returns:
            API response dictionary
        """
        endpoint = self._get_api_url(f"messages/{self.phone_number}")
        
        payload = {
            'recipient': [recipient],
            'message': text,
            'preview': {
                'url': url,
                'title': title or url,
            }
        }
        
        if description:
            payload['preview']['description'] = description
        
        if image_attachment:
            payload['preview']['image'] = f"data:{image_attachment.content_type};base64,{image_attachment.to_base64()}"
        
        async with self.session.post(endpoint, json=payload) as resp:
            if resp.status == 200:
                result = await resp.json()
                logger.info(f"Message with preview sent to {recipient}")
                return result
            else:
                error_text = await resp.text()
                raise RuntimeError(f"Failed to send message with preview: {error_text}")
    
    # ==================== Account Management ====================
    
    async def register_account(self, voice_verification: bool = False) -> bool:
        """Register a new Signal account."""
        url = self._get_api_url(f"register/{self.phone_number}")
        
        payload = {'voice': voice_verification}
        
        async with self.session.post(url, json=payload) as resp:
            return resp.status == 200
    
    async def verify_account(self, verification_code: str) -> bool:
        """Verify Signal account with verification code."""
        url = self._get_api_url(f"register/{self.phone_number}/verify")
        
        payload = {'verification_code': verification_code}
        
        async with self.session.post(url, json=payload) as resp:
            return resp.status == 200
    
    async def set_profile(
        self,
        name: Optional[str] = None,
        about: Optional[str] = None,
        avatar_path: Optional[str] = None
    ) -> bool:
        """Update Signal profile."""
        url = self._get_api_url(f"profiles/{self.phone_number}")
        
        payload = {}
        if name:
            payload['name'] = name
        if about:
            payload['about'] = about
        if avatar_path:
            with open(avatar_path, 'rb') as f:
                payload['avatar'] = base64.b64encode(f.read()).decode('utf-8')
        
        async with self.session.put(url, json=payload) as resp:
            return resp.status == 200
    
    # ==================== Utility Methods ====================
    
    async def get_contacts(self) -> List[Dict[str, Any]]:
        """Get list of Signal contacts."""
        url = self._get_api_url(f"contacts/{self.phone_number}")
        
        async with self.session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            return []
    
    async def get_contact(self, number: str) -> Optional[Dict[str, Any]]:
        """Get specific contact information."""
        url = self._get_api_url(f"contacts/{self.phone_number}/{number}")
        
        async with self.session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            return None
    
    def get_cached_message(self, source: str, timestamp: int) -> Optional[SignalMessage]:
        """Get a message from the cache."""
        cache_key = f"{source}:{timestamp}"
        return self._message_cache.get(cache_key)


# ==================== Convenience Functions ====================

async def send_signal_message(
    recipient: str,
    text: str,
    config_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to send a Signal message.
    
    Args:
        recipient: Phone number or group ID
        text: Message text
        config_path: Path to configuration file
        
    Returns:
        API response dictionary
    """
    async with SignalBot(config_path) as bot:
        return await bot.send_message(recipient, text)


async def send_signal_file(
    recipient: str,
    filepath: str,
    caption: Optional[str] = None,
    config_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to send a file via Signal.
    
    Args:
        recipient: Phone number or group ID
        filepath: Path to file
        caption: Optional caption
        config_path: Path to configuration file
        
    Returns:
        API response dictionary
    """
    attachment = SignalAttachment.from_file(filepath, caption)
    async with SignalBot(config_path) as bot:
        return await bot.send_attachment(recipient, attachment, caption)


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Example: Send a message
        bot = SignalBot()
        await bot.start()
        
        try:
            # Send a text message
            result = await bot.send_message(
                recipient="+1234567890",
                text="Hello from Cell 0 OS!"
            )
            print(f"Message sent: {result}")
            
            # Register a message handler
            @bot.on_message
            def handle_message(message: SignalMessage):
                print(f"Received from {message.source}: {message.text}")
            
            # Keep running to receive messages
            await asyncio.sleep(60)
            
        finally:
            await bot.stop()
    
    asyncio.run(main())
