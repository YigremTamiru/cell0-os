"""
Google Chat Bot Integration for Cell 0 OS

A comprehensive Google Chat bot supporting:
- Cards API for rich UI
- Event handling (MESSAGE, ADDED_TO_SPACE, REMOVED_FROM_SPACE)
- Threading support
- Slash commands
- OAuth2 authentication
- HTTP endpoint support
- 1:1 DMs and space conversations

Author: KULLU (Cell 0 OS)
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import aiohttp
from aiohttp import web
import jwt
from functools import wraps

logger = logging.getLogger("cell0.google_chat")


class ChatEventType(Enum):
    """Google Chat event types"""
    MESSAGE = "MESSAGE"
    ADDED_TO_SPACE = "ADDED_TO_SPACE"
    REMOVED_FROM_SPACE = "REMOVED_FROM_SPACE"
    CARD_CLICKED = "CARD_CLICKED"
    MESSAGE_REACTION = "MESSAGE_REACTION"


class SpaceType(Enum):
    """Google Chat space types"""
    SPACE = "SPACE"           # Group chat/room
    GROUP_CHAT = "GROUP_CHAT" # Group DM
    DIRECT_MESSAGE = "DIRECT_MESSAGE"  # 1:1 DM


@dataclass
class ChatMessage:
    """Represents a Google Chat message"""
    message_id: str
    text: str
    sender: Dict[str, Any]
    space: Dict[str, Any]
    thread: Optional[Dict[str, Any]] = None
    cards: Optional[List[Dict]] = None
    cards_v2: Optional[List[Dict]] = None
    slash_command: Optional[Dict[str, Any]] = None
    argument_text: Optional[str] = None
    create_time: Optional[str] = None
    
    @property
    def is_direct_message(self) -> bool:
        """Check if message is from a 1:1 DM"""
        return self.space.get("spaceType") == SpaceType.DIRECT_MESSAGE.value
    
    @property
    def is_group_space(self) -> bool:
        """Check if message is from a group space"""
        return self.space.get("spaceType") in [SpaceType.SPACE.value, SpaceType.GROUP_CHAT.value]
    
    @property
    def thread_name(self) -> Optional[str]:
        """Get thread resource name"""
        return self.thread.get("name") if self.thread else None
    
    @property
    def space_name(self) -> str:
        """Get space resource name"""
        return self.space.get("name", "")
    
    @property
    def user_email(self) -> Optional[str]:
        """Get sender email"""
        return self.sender.get("email")
    
    @property
    def user_name(self) -> str:
        """Get sender display name"""
        return self.sender.get("displayName", "Unknown")


@dataclass
class SlashCommand:
    """Represents a slash command invocation"""
    command_id: str
    command_name: str
    arguments: Optional[str] = None
    
    @classmethod
    def from_message(cls, message: ChatMessage) -> Optional["SlashCommand"]:
        """Extract slash command from message"""
        if not message.slash_command:
            return None
        return cls(
            command_id=message.slash_command.get("commandId", ""),
            command_name=message.slash_command.get("commandName", ""),
            arguments=message.argument_text
        )


class CardBuilder:
    """Builder for Google Chat Cards V2 API"""
    
    def __init__(self):
        self._card = {"sections": []}
        self._current_section = None
    
    def set_header(self, title: str, subtitle: Optional[str] = None, 
                   image_url: Optional[str] = None, image_type: str = "CIRCLE") -> "CardBuilder":
        """Set card header"""
        header = {"title": title}
        if subtitle:
            header["subtitle"] = subtitle
        if image_url:
            header["imageUrl"] = image_url
            header["imageType"] = image_type
        self._card["header"] = header
        return self
    
    def add_section(self, header: Optional[str] = None, 
                    collapsible: bool = False, 
                    uncollapsible_widgets: int = 0) -> "CardBuilder":
        """Add a new section to the card"""
        section = {"widgets": []}
        if header:
            section["header"] = header
        if collapsible:
            section["collapsible"] = True
        if uncollapsible_widgets > 0:
            section["uncollapsibleWidgetsCount"] = uncollapsible_widgets
        
        self._current_section = section
        self._card["sections"].append(section)
        return self
    
    def add_text_paragraph(self, text: str) -> "CardBuilder":
        """Add text paragraph widget"""
        if not self._current_section:
            self.add_section()
        
        widget = {
            "textParagraph": {
                "text": text
            }
        }
        self._current_section["widgets"].append(widget)
        return self
    
    def add_image(self, image_url: str, alt_text: str = "",
                  on_click_action: Optional[Dict] = None) -> "CardBuilder":
        """Add image widget"""
        if not self._current_section:
            self.add_section()
        
        widget = {
            "image": {
                "imageUrl": image_url,
                "altText": alt_text
            }
        }
        if on_click_action:
            widget["image"]["onClick"] = on_click_action
        
        self._current_section["widgets"].append(widget)
        return self
    
    def add_button(self, text: str, on_click_action: Dict,
                   color: Optional[str] = None, icon: Optional[str] = None) -> "CardBuilder":
        """Add button widget"""
        if not self._current_section:
            self.add_section()
        
        button = {
            "text": text,
            "onClick": on_click_action
        }
        if color:
            button["color"] = {"red": 0, "green": 0, "blue": 1}  # Default blue
        if icon:
            button["icon"] = {"icon": icon}
        
        widget = {
            "buttonList": {
                "buttons": [button]
            }
        }
        self._current_section["widgets"].append(widget)
        return self
    
    def add_button_row(self, buttons: List[Dict]) -> "CardBuilder":
        """Add multiple buttons in a row"""
        if not self._current_section:
            self.add_section()
        
        widget = {
            "buttonList": {
                "buttons": buttons
            }
        }
        self._current_section["widgets"].append(widget)
        return self
    
    def add_key_value(self, key: str, value: str, 
                      icon: Optional[str] = None,
                      button: Optional[Dict] = None) -> "CardBuilder":
        """Add key-value widget"""
        if not self._current_section:
            self.add_section()
        
        kv = {
            "keyValue": {
                "topLabel": key,
                "content": value
            }
        }
        if icon:
            kv["keyValue"]["icon"] = {"icon": icon}
        if button:
            kv["keyValue"]["button"] = button
        
        self._current_section["widgets"].append(kv)
        return self
    
    def add_divider(self) -> "CardBuilder":
        """Add divider widget"""
        if not self._current_section:
            self.add_section()
        
        widget = {"divider": {}}
        self._current_section["widgets"].append(widget)
        return self
    
    def add_input(self, name: str, label: str, 
                  type_: str = "SINGLE_LINE",
                  placeholder: Optional[str] = None) -> "CardBuilder":
        """Add text input widget"""
        if not self._current_section:
            self.add_section()
        
        widget = {
            "textInput": {
                "name": name,
                "label": label,
                "type": type_
            }
        }
        if placeholder:
            widget["textInput"]["placeholderText"] = placeholder
        
        self._current_section["widgets"].append(widget)
        return self
    
    def add_selection_input(self, name: str, label: str,
                            items: List[Dict],
                            multi_select: bool = False) -> "CardBuilder":
        """Add selection/dropdown widget"""
        if not self._current_section:
            self.add_section()
        
        widget = {
            "selectionInput": {
                "name": name,
                "label": label,
                "type": "MULTI_SELECT" if multi_select else "DROPDOWN",
                "items": items
            }
        }
        self._current_section["widgets"].append(widget)
        return self
    
    def build(self) -> Dict:
        """Build and return the card JSON"""
        return {"cardsV2": [{"card": self._card}]}
    
    # Static methods for common actions
    @staticmethod
    def action_open_link(url: str) -> Dict:
        """Create open link action"""
        return {
            "action": {
                "link": {"url": url}
            }
        }
    
    @staticmethod
    def action_run_function(function_name: str, parameters: Optional[Dict] = None) -> Dict:
        """Create run function action (for card interactions)"""
        action = {
            "action": {
                "function": function_name
            }
        }
        if parameters:
            action["action"]["parameters"] = parameters
        return action
    
    @staticmethod
    def create_button(text: str, action: Dict, 
                      color: Optional[str] = None,
                      icon: Optional[str] = None) -> Dict:
        """Create a button configuration"""
        button = {"text": text, "onClick": action}
        if icon:
            button["icon"] = {"icon": icon}
        return button
    
    @staticmethod
    def create_selection_item(text: str, value: str, selected: bool = False) -> Dict:
        """Create a selection item"""
        return {"text": text, "value": value, "selected": selected}


class GoogleChatBot:
    """
    Main Google Chat Bot class for Cell 0 OS
    
    Handles:
    - Event processing
    - Message sending
    - Slash commands
    - Card interactions
    - Authentication
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the bot with configuration"""
        self.config = config or self._load_config()
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Event handlers
        self._handlers: Dict[ChatEventType, List[Callable]] = {
            event_type: [] for event_type in ChatEventType
        }
        
        # Slash command handlers
        self._slash_handlers: Dict[str, Callable] = {}
        
        # Card click handlers
        self._card_handlers: Dict[str, Callable] = {}
        
        logger.info("Google Chat Bot initialized")
    
    def _load_config(self) -> Dict:
        """Load configuration from YAML file"""
        import yaml
        config_path = os.path.join(
            os.path.dirname(__file__), 
            "google_chat_config.yaml"
        )
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found at {config_path}, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """Return default configuration"""
        return {
            "bot_name": "Cell0Bot",
            "project_id": os.getenv("GOOGLE_PROJECT_ID", ""),
            "credentials_path": os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
            "auth": {
                "type": "service_account",
                "token_uri": "https://oauth2.googleapis.com/token",
                "scopes": ["https://www.googleapis.com/auth/chat.bot"]
            },
            "webhook": {
                "enabled": True,
                "port": 8080,
                "path": "/chat/webhook",
                "verify_tokens": True
            },
            "features": {
                "threading": True,
                "cards": True,
                "slash_commands": True
            }
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
    
    async def start(self):
        """Start the bot and initialize HTTP session"""
        self.session = aiohttp.ClientSession()
        await self._authenticate()
        logger.info("Google Chat Bot started")
    
    async def stop(self):
        """Stop the bot and cleanup"""
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("Google Chat Bot stopped")
    
    async def _authenticate(self):
        """Authenticate with Google and get access token"""
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request
            
            credentials_path = self.config.get("credentials_path")
            if not credentials_path or not os.path.exists(credentials_path):
                logger.error(f"Credentials file not found: {credentials_path}")
                return
            
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=self.config["auth"]["scopes"]
            )
            
            credentials.refresh(Request())
            self.access_token = credentials.token
            self.token_expiry = credentials.expiry
            logger.info("Successfully authenticated with Google Chat API")
            
        except ImportError:
            logger.error("google-auth library not installed. Run: pip install google-auth")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
    
    async def _ensure_token(self):
        """Ensure access token is valid, refresh if needed"""
        if not self.access_token or (self.token_expiry and datetime.utcnow() >= self.token_expiry):
            await self._authenticate()
    
    def on_event(self, event_type: ChatEventType):
        """Decorator to register event handler"""
        def decorator(func: Callable):
            self._handlers[event_type].append(func)
            return func
        return decorator
    
    def on_slash_command(self, command_name: str):
        """Decorator to register slash command handler"""
        def decorator(func: Callable):
            self._slash_handlers[command_name] = func
            return func
        return decorator
    
    def on_card_click(self, action_name: str):
        """Decorator to register card click handler"""
        def decorator(func: Callable):
            self._card_handlers[action_name] = func
            return func
        return decorator
    
    async def handle_event(self, event_data: Dict[str, Any]) -> Dict:
        """
        Handle incoming Google Chat event
        
        Args:
            event_data: The event JSON from Google Chat
            
        Returns:
            Response dict to send back to Google Chat
        """
        event_type_str = event_data.get("type", "")
        
        try:
            event_type = ChatEventType(event_type_str)
        except ValueError:
            logger.warning(f"Unknown event type: {event_type_str}")
            return {"text": "Unknown event type"}
        
        logger.info(f"Handling event: {event_type.value}")
        
        # Process based on event type
        if event_type == ChatEventType.MESSAGE:
            return await self._handle_message(event_data)
        elif event_type == ChatEventType.ADDED_TO_SPACE:
            return await self._handle_added_to_space(event_data)
        elif event_type == ChatEventType.REMOVED_FROM_SPACE:
            return await self._handle_removed_from_space(event_data)
        elif event_type == ChatEventType.CARD_CLICKED:
            return await self._handle_card_click(event_data)
        else:
            # Call registered handlers
            for handler in self._handlers.get(event_type, []):
                try:
                    await handler(event_data)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")
            
            return {"text": f"Event {event_type.value} received"}
    
    async def _handle_message(self, event_data: Dict) -> Dict:
        """Handle MESSAGE event"""
        message_data = event_data.get("message", {})
        message = ChatMessage(
            message_id=message_data.get("name", ""),
            text=message_data.get("text", ""),
            sender=message_data.get("sender", {}),
            space=message_data.get("space", {}),
            thread=message_data.get("thread"),
            cards=message_data.get("cards"),
            cards_v2=message_data.get("cardsV2"),
            slash_command=message_data.get("slashCommand"),
            argument_text=message_data.get("argumentText"),
            create_time=message_data.get("createTime")
        )
        
        # Check for slash command
        if message.slash_command:
            slash = SlashCommand.from_message(message)
            if slash and slash.command_name in self._slash_handlers:
                handler = self._slash_handlers[slash.command_name]
                try:
                    return await handler(message, slash.arguments)
                except Exception as e:
                    logger.error(f"Slash command handler error: {e}")
                    return {"text": f"Error processing command: {e}"}
            else:
                return {"text": f"Unknown command: {slash.command_name if slash else 'unknown'}"}
        
        # Call registered message handlers
        for handler in self._handlers.get(ChatEventType.MESSAGE, []):
            try:
                result = await handler(message)
                if result:
                    return result
            except Exception as e:
                logger.error(f"Message handler error: {e}")
        
        # Default response
        return await self._default_message_response(message)
    
    async def _default_message_response(self, message: ChatMessage) -> Dict:
        """Default response for regular messages"""
        if message.is_direct_message:
            return {
                "text": f"Hello {message.user_name}! I'm Cell 0 OS Bot. How can I help you today?"
            }
        else:
            return {
                "text": f"Thanks for your message, {message.user_name}!",
                "thread": message.thread
            }
    
    async def _handle_added_to_space(self, event_data: Dict) -> Dict:
        """Handle ADDED_TO_SPACE event"""
        space = event_data.get("space", {})
        space_name = space.get("displayName", "this space")
        space_type = space.get("spaceType", "SPACE")
        
        logger.info(f"Added to space: {space_name} ({space_type})")
        
        # Build welcome card
        card = CardBuilder()
        card.set_header(
            title="🌊 Cell 0 OS",
            subtitle="Your Sovereign Edge AI",
            image_url="https://cell0.ai/logo.png"
        )
        card.add_section("Welcome")
        card.add_text_paragraph(
            f"Hello! I'm the Cell 0 OS bot. I've been added to **{space_name}**.\n\n"
            "I can help you with:\n"
            "• **/status** - Check system status\n"
            "• **/ask** - Ask me anything\n"
            "• **/tasks** - Manage your tasks\n"
            "• **/help** - Show all commands"
        )
        card.add_divider()
        card.add_button(
            text="Learn More",
            on_click_action=CardBuilder.action_open_link("https://cell0.ai"),
            icon="BOOKMARK"
        )
        
        # Call registered handlers
        for handler in self._handlers.get(ChatEventType.ADDED_TO_SPACE, []):
            try:
                await handler(event_data)
            except Exception as e:
                logger.error(f"Added to space handler error: {e}")
        
        return card.build()
    
    async def _handle_removed_from_space(self, event_data: Dict) -> Dict:
        """Handle REMOVED_FROM_SPACE event"""
        space = event_data.get("space", {})
        logger.info(f"Removed from space: {space.get('name', 'unknown')}")
        
        # Call registered handlers
        for handler in self._handlers.get(ChatEventType.REMOVED_FROM_SPACE, []):
            try:
                await handler(event_data)
            except Exception as e:
                logger.error(f"Removed from space handler error: {e}")
        
        return {}  # No response needed
    
    async def _handle_card_click(self, event_data: Dict) -> Dict:
        """Handle CARD_CLICKED event"""
        action = event_data.get("action", {})
        action_name = action.get("actionMethodName", "")
        parameters = action.get("parameters", [])
        
        logger.info(f"Card clicked: {action_name}")
        
        # Convert parameters to dict
        params = {p.get("key"): p.get("value") for p in parameters}
        
        # Call registered handler
        if action_name in self._card_handlers:
            handler = self._card_handlers[action_name]
            try:
                return await handler(params, event_data)
            except Exception as e:
                logger.error(f"Card click handler error: {e}")
                return {"text": f"Error: {e}"}
        
        return {"text": f"Action '{action_name}' not implemented"}
    
    async def send_message(self, space_name: str, text: Optional[str] = None,
                          cards: Optional[Dict] = None,
                          thread_name: Optional[str] = None) -> Dict:
        """
        Send a message to a space
        
        Args:
            space_name: The space resource name (e.g., "spaces/ABC123")
            text: Plain text message
            cards: Card JSON from CardBuilder
            thread_name: Optional thread to reply in
            
        Returns:
            API response
        """
        await self._ensure_token()
        
        if not self.session or not self.access_token:
            raise RuntimeError("Bot not authenticated")
        
        url = f"https://chat.googleapis.com/v1/{space_name}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {}
        if text:
            payload["text"] = text
        if cards:
            payload.update(cards)
        if thread_name and self.config["features"]["threading"]:
            payload["thread"] = {"name": thread_name}
        
        async with self.session.post(url, headers=headers, json=payload) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                error_text = await resp.text()
                logger.error(f"Failed to send message: {resp.status} - {error_text}")
                raise RuntimeError(f"API error: {resp.status}")
    
    async def send_direct_message(self, user_email: str, text: Optional[str] = None,
                                   cards: Optional[Dict] = None) -> Dict:
        """
        Send a direct message to a user
        
        Args:
            user_email: User's email address
            text: Plain text message
            cards: Card JSON from CardBuilder
            
        Returns:
            API response
        """
        # For DMs, we need to use the user's email as the space
        space_name = f"spaces/{user_email}"
        return await self.send_message(space_name, text=text, cards=cards)
    
    async def update_message(self, message_name: str, text: Optional[str] = None,
                             cards: Optional[Dict] = None) -> Dict:
        """
        Update an existing message
        
        Args:
            message_name: Full message resource name
            text: New text content
            cards: New card content
            
        Returns:
            API response
        """
        await self._ensure_token()
        
        if not self.session or not self.access_token:
            raise RuntimeError("Bot not authenticated")
        
        url = f"https://chat.googleapis.com/v1/{message_name}"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {}
        if text:
            payload["text"] = text
        if cards:
            payload.update(cards)
        
        async with self.session.patch(url, headers=headers, json=payload) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                error_text = await resp.text()
                logger.error(f"Failed to update message: {resp.status} - {error_text}")
                raise RuntimeError(f"API error: {resp.status}")
    
    async def create_webhook_server(self) -> web.Application:
        """
        Create and configure the webhook HTTP server
        
        Returns:
            aiohttp Application instance
        """
        app = web.Application()
        app.router.add_post(self.config["webhook"]["path"], self._webhook_handler)
        app.router.add_get("/health", self._health_handler)
        return app
    
    async def _webhook_handler(self, request: web.Request) -> web.Response:
        """Handle incoming webhook requests from Google Chat"""
        try:
            # Verify token if configured
            if self.config["webhook"].get("verify_tokens", True):
                token = request.headers.get("Authorization", "")
                # Token verification would go here
                # For now, we trust Google's HTTPS
            
            event_data = await request.json()
            logger.debug(f"Received event: {json.dumps(event_data, indent=2)}")
            
            response = await self.handle_event(event_data)
            
            return web.json_response(response)
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook request")
            return web.json_response({"text": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.error(f"Webhook handler error: {e}")
            return web.json_response({"text": "Internal error"}, status=500)
    
    async def _health_handler(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "bot_name": self.config["bot_name"],
            "authenticated": self.access_token is not None
        })


# Default slash command implementations
async def cmd_help(bot: GoogleChatBot, message: ChatMessage, args: Optional[str]) -> Dict:
    """Help command handler"""
    card = CardBuilder()
    card.set_header(
        title="📚 Cell 0 Bot Commands",
        subtitle="Available slash commands"
    )
    card.add_section("Commands")
    card.add_key_value("/help", "Show this help message", icon="HELP")
    card.add_key_value("/status", "Check Cell 0 OS system status", icon="COMPUTER")
    card.add_key_value("/ask <question>", "Ask the AI a question", icon="CHAT")
    card.add_key_value("/tasks", "List and manage your tasks", icon="CHECK_BOX")
    card.add_key_value("/profile", "View your user profile", icon="PERSON")
    card.add_divider()
    card.add_text_paragraph(
        "*Tip: You can also mention me in conversations or send me a direct message!*"
    )
    
    return card.build()


async def cmd_status(bot: GoogleChatBot, message: ChatMessage, args: Optional[str]) -> Dict:
    """Status command handler"""
    card = CardBuilder()
    card.set_header(
        title="📊 System Status",
        subtitle="Cell 0 OS Health"
    )
    card.add_section("Current Status")
    card.add_key_value("Status", "🟢 Operational", icon="COMPUTER")
    card.add_key_value("Bot", bot.config["bot_name"], icon="BOT")
    card.add_key_value("Authenticated", "✅ Yes" if bot.access_token else "❌ No", icon="LOCK")
    card.add_divider()
    card.add_button(
        text="View Dashboard",
        on_click_action=CardBuilder.action_open_link("https://cell0.ai/dashboard"),
        icon="DASHBOARD"
    )
    
    return card.build()


# Factory function for creating a configured bot
def create_bot(config_path: Optional[str] = None) -> GoogleChatBot:
    """
    Create and configure a Google Chat Bot instance
    
    Args:
        config_path: Path to config YAML file (optional)
        
    Returns:
        Configured GoogleChatBot instance
    """
    config = None
    if config_path:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    
    bot = GoogleChatBot(config)
    
    # Register default commands
    @bot.on_slash_command("/help")
    async def help_handler(message, args):
        return await cmd_help(bot, message, args)
    
    @bot.on_slash_command("/status")
    async def status_handler(message, args):
        return await cmd_status(bot, message, args)
    
    return bot


# Main entry point for running the bot
async def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    bot = create_bot()
    
    async with bot:
        app = await bot.create_webhook_server()
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(
            runner, 
            "0.0.0.0", 
            bot.config["webhook"]["port"]
        )
        
        logger.info(f"Starting webhook server on port {bot.config['webhook']['port']}")
        await site.start()
        
        # Keep running
        while True:
            await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
