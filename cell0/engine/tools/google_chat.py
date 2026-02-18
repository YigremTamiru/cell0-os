"""
Google Chat Tool for Cell 0 OS Agents

Provides agent-level access to Google Chat functionality for:
- Sending notifications
- Querying conversations
- Managing bot interactions
- Card-based interactions

Author: KULLU (Cell 0 OS)
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime
import asyncio

# Import the bot classes
from cell0.integrations.google_chat_bot import (
    GoogleChatBot, 
    CardBuilder, 
    ChatMessage,
    ChatEventType
)

logger = logging.getLogger("cell0.tools.google_chat")


@dataclass
class NotificationRequest:
    """Request to send a notification"""
    target_type: str  # "user", "space", "thread"
    target_id: str
    message: Optional[str] = None
    title: Optional[str] = None
    priority: str = "normal"  # "low", "normal", "high", "urgent"
    card_data: Optional[Dict] = None
    actions: Optional[List[Dict]] = None


@dataclass
class NotificationResponse:
    """Response from sending a notification"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None


class GoogleChatTool:
    """
    Tool interface for Cell 0 agents to interact with Google Chat
    
    This provides a simplified API for agents to:
    - Send notifications to users/spaces
    - Create interactive cards
    - Query conversation history
    - Manage subscriptions
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Google Chat tool
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path or self._default_config_path()
        self._bot: Optional[GoogleChatBot] = None
        self._initialized = False
        
    def _default_config_path(self) -> str:
        """Get default config path"""
        return os.path.join(
            os.path.dirname(__file__), 
            "..", "..", "integrations", "google_chat_config.yaml"
        )
    
    async def initialize(self):
        """Initialize the tool and bot connection"""
        if self._initialized:
            return
            
        self._bot = GoogleChatBot()
        await self._bot.start()
        self._initialized = True
        logger.info("Google Chat tool initialized")
    
    async def shutdown(self):
        """Shutdown the tool"""
        if self._bot:
            await self._bot.stop()
            self._bot = None
        self._initialized = False
        logger.info("Google Chat tool shutdown")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.shutdown()
    
    # ========================================================================
    # Core Notification Methods
    # ========================================================================
    
    async def send_notification(
        self,
        request: NotificationRequest
    ) -> NotificationResponse:
        """
        Send a notification to a user, space, or thread
        
        Args:
            request: NotificationRequest with target and content
            
        Returns:
            NotificationResponse with result
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Build card if title or actions provided
            if request.title or request.actions:
                card = self._build_notification_card(request)
                cards = card.build()
            else:
                cards = None
            
            # Determine target
            if request.target_type == "user":
                result = await self._bot.send_direct_message(
                    user_email=request.target_id,
                    text=request.message,
                    cards=cards
                )
            elif request.target_type in ["space", "thread"]:
                thread = request.target_id if request.target_type == "thread" else None
                space = request.target_id if request.target_type == "space" else None
                
                # If thread, extract space name
                if thread and not space:
                    space = thread.split("/threads/")[0]
                
                result = await self._bot.send_message(
                    space_name=space,
                    text=request.message,
                    cards=cards,
                    thread_name=thread if request.target_type == "thread" else None
                )
            else:
                return NotificationResponse(
                    success=False,
                    error=f"Unknown target type: {request.target_type}"
                )
            
            return NotificationResponse(
                success=True,
                message_id=result.get("name"),
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return NotificationResponse(
                success=False,
                error=str(e)
            )
    
    async def send_to_user(
        self,
        user_email: str,
        message: str,
        title: Optional[str] = None,
        priority: str = "normal"
    ) -> NotificationResponse:
        """
        Send a direct message to a user
        
        Args:
            user_email: User's email address
            message: Message text
            title: Optional card title
            priority: Message priority
            
        Returns:
            NotificationResponse
        """
        request = NotificationRequest(
            target_type="user",
            target_id=user_email,
            message=message,
            title=title,
            priority=priority
        )
        return await self.send_notification(request)
    
    async def send_to_space(
        self,
        space_name: str,
        message: str,
        title: Optional[str] = None,
        thread_name: Optional[str] = None
    ) -> NotificationResponse:
        """
        Send a message to a space
        
        Args:
            space_name: Space resource name (e.g., "spaces/ABC123")
            message: Message text
            title: Optional card title
            thread_name: Optional thread to reply in
            
        Returns:
            NotificationResponse
        """
        request = NotificationRequest(
            target_type="thread" if thread_name else "space",
            target_id=thread_name or space_name,
            message=message,
            title=title
        )
        return await self.send_notification(request)
    
    # ========================================================================
    # Card Builders for Common Use Cases
    # ========================================================================
    
    def _build_notification_card(self, request: NotificationRequest) -> CardBuilder:
        """Build a notification card from request"""
        card = CardBuilder()
        
        # Header with priority indicator
        priority_emoji = {
            "low": "🔵",
            "normal": "⚪",
            "high": "🟡",
            "urgent": "🔴"
        }.get(request.priority, "⚪")
        
        title = request.title or "Notification"
        card.set_header(
            title=f"{priority_emoji} {title}",
            subtitle=f"Cell 0 OS • {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        # Message section
        if request.message:
            card.add_section()
            card.add_text_paragraph(request.message)
        
        # Custom card data
        if request.card_data:
            for section in request.card_data.get("sections", []):
                card.add_section(section.get("header"))
                for widget in section.get("widgets", []):
                    if "textParagraph" in widget:
                        card.add_text_paragraph(widget["textParagraph"]["text"])
                    elif "keyValue" in widget:
                        kv = widget["keyValue"]
                        card.add_key_value(
                            kv.get("topLabel", ""),
                            kv.get("content", ""),
                            icon=kv.get("icon", {}).get("icon")
                        )
        
        # Action buttons
        if request.actions:
            card.add_section("Actions")
            buttons = []
            for action in request.actions:
                btn = CardBuilder.create_button(
                    text=action.get("text", "Action"),
                    action=CardBuilder.action_open_link(action.get("url", "#")),
                    icon=action.get("icon")
                )
                buttons.append(btn)
            
            if buttons:
                card.add_button_row(buttons)
        
        return card
    
    def create_task_card(
        self,
        task_title: str,
        task_description: str,
        task_id: str,
        status: str = "pending",
        due_date: Optional[str] = None,
        assignee: Optional[str] = None
    ) -> Dict:
        """
        Create a task management card
        
        Args:
            task_title: Task title
            task_description: Task description
            task_id: Unique task ID
            status: Task status
            due_date: Optional due date
            assignee: Optional assignee
            
        Returns:
            Card JSON
        """
        card = CardBuilder()
        
        status_emoji = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "blocked": "🚫"
        }.get(status, "⏳")
        
        card.set_header(
            title=f"{status_emoji} {task_title}",
            subtitle=f"Task #{task_id}"
        )
        
        card.add_section("Details")
        card.add_text_paragraph(task_description)
        
        if due_date:
            card.add_key_value("Due Date", due_date, icon="EVENT")
        
        if assignee:
            card.add_key_value("Assignee", assignee, icon="PERSON")
        
        card.add_section("Actions")
        card.add_button_row([
            CardBuilder.create_button(
                "Mark Complete",
                CardBuilder.action_run_function("complete_task", {"task_id": task_id}),
                icon="CHECK_BOX"
            ),
            CardBuilder.create_button(
                "View Details",
                CardBuilder.action_open_link(f"https://cell0.ai/tasks/{task_id}"),
                icon="OPEN_IN_NEW"
            )
        ])
        
        return card.build()
    
    def create_alert_card(
        self,
        alert_title: str,
        alert_message: str,
        severity: str = "info",
        timestamp: Optional[str] = None,
        source: Optional[str] = None,
        actions: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Create an alert/notification card
        
        Args:
            alert_title: Alert title
            alert_message: Alert description
            severity: Alert severity (info, warning, error, critical)
            timestamp: Alert timestamp
            source: Alert source
            actions: List of action buttons
            
        Returns:
            Card JSON
        """
        card = CardBuilder()
        
        severity_config = {
            "info": ("ℹ️", "#2196F3"),
            "warning": ("⚠️", "#FF9800"),
            "error": ("❌", "#F44336"),
            "critical": ("🚨", "#D32F2F")
        }.get(severity, ("ℹ️", "#2196F3"))
        
        emoji = severity_config[0]
        
        card.set_header(
            title=f"{emoji} {alert_title}",
            subtitle=source or "Cell 0 OS Alert"
        )
        
        card.add_section()
        card.add_text_paragraph(alert_message)
        
        if timestamp:
            card.add_key_value("Time", timestamp, icon="SCHEDULE")
        
        if actions:
            card.add_section("Actions")
            buttons = [
                CardBuilder.create_button(
                    a.get("text", "Action"),
                    CardBuilder.action_open_link(a.get("url", "#")),
                    icon=a.get("icon")
                )
                for a in actions
            ]
            card.add_button_row(buttons)
        
        return card.build()
    
    def create_status_card(
        self,
        system_name: str,
        status: str,
        metrics: List[Dict],
        last_updated: Optional[str] = None
    ) -> Dict:
        """
        Create a system status card
        
        Args:
            system_name: Name of the system
            status: Overall status (operational, degraded, down)
            metrics: List of metric dicts with name, value, status
            last_updated: Last update timestamp
            
        Returns:
            Card JSON
        """
        card = CardBuilder()
        
        status_emoji = {
            "operational": "🟢",
            "degraded": "🟡",
            "down": "🔴",
            "maintenance": "🔵"
        }.get(status, "⚪")
        
        card.set_header(
            title=f"{status_emoji} {system_name}",
            subtitle=f"Status: {status.title()}"
        )
        
        card.add_section("Metrics")
        for metric in metrics:
            metric_status = metric.get("status", "normal")
            emoji = {"good": "✅", "warning": "⚠️", "critical": "❌"}.get(metric_status, "⚪")
            card.add_key_value(
                metric.get("name", ""),
                f"{emoji} {metric.get('value', '')}"
            )
        
        if last_updated:
            card.add_divider()
            card.add_text_paragraph(f"_Last updated: {last_updated}_")
        
        return card.build()
    
    # ========================================================================
    # Agent Integration Methods
    # ========================================================================
    
    async def notify_task_complete(
        self,
        user_email: str,
        task_name: str,
        task_result: Optional[str] = None
    ) -> NotificationResponse:
        """
        Notify user that a task is complete
        
        Args:
            user_email: User to notify
            task_name: Name of completed task
            task_result: Optional result summary
            
        Returns:
            NotificationResponse
        """
        message = f"✅ Task completed: **{task_name}**"
        if task_result:
            message += f"\n\n{task_result}"
        
        return await self.send_to_user(
            user_email=user_email,
            message=message,
            title="Task Complete"
        )
    
    async def notify_error(
        self,
        user_email: str,
        error_message: str,
        error_details: Optional[str] = None,
        action_url: Optional[str] = None
    ) -> NotificationResponse:
        """
        Notify user of an error
        
        Args:
            user_email: User to notify
            error_message: Error summary
            error_details: Detailed error info
            action_url: URL for more info/fix
            
        Returns:
            NotificationResponse
        """
        card = self.create_alert_card(
            alert_title="Error Occurred",
            alert_message=error_message,
            severity="error",
            actions=[{"text": "View Details", "url": action_url, "icon": "ERROR"}] if action_url else None
        )
        
        request = NotificationRequest(
            target_type="user",
            target_id=user_email,
            message=error_details,
            card_data=card.get("cardsV2", [{}])[0].get("card")
        )
        
        return await self.send_notification(request)
    
    async def request_user_input(
        self,
        user_email: str,
        prompt: str,
        input_type: str = "text",
        options: Optional[List[str]] = None
    ) -> NotificationResponse:
        """
        Request input from a user
        
        Args:
            user_email: User to request input from
            prompt: Prompt message
            input_type: Type of input (text, choice, confirm)
            options: Options for choice input
            
        Returns:
            NotificationResponse
        """
        card = CardBuilder()
        card.set_header(title="Input Required", subtitle="Cell 0 OS")
        card.add_section()
        card.add_text_paragraph(prompt)
        
        if input_type == "choice" and options:
            items = [CardBuilder.create_selection_item(opt, opt) for opt in options]
            card.add_selection_input("user_choice", "Select an option:", items)
        elif input_type == "confirm":
            card.add_button_row([
                CardBuilder.create_button(
                    "Yes",
                    CardBuilder.action_run_function("confirm", {"value": "yes"}),
                    icon="CHECK"
                ),
                CardBuilder.create_button(
                    "No",
                    CardBuilder.action_run_function("confirm", {"value": "no"}),
                    icon="CLOSE"
                )
            ])
        else:
            card.add_input("user_response", "Your response:")
        
        request = NotificationRequest(
            target_type="user",
            target_id=user_email,
            title="Input Required",
            card_data=card.build().get("cardsV2", [{}])[0].get("card")
        )
        
        return await self.send_notification(request)
    
    # ========================================================================
    # Query Methods
    # ========================================================================
    
    async def get_space_info(self, space_name: str) -> Optional[Dict]:
        """
        Get information about a space
        
        Args:
            space_name: Space resource name
            
        Returns:
            Space info dict or None
        """
        # This would make an API call to get space info
        # For now, return a placeholder
        logger.info(f"Getting space info for {space_name}")
        return {
            "name": space_name,
            "displayName": "Unknown",
            "spaceType": "SPACE"
        }
    
    async def list_spaces(self) -> List[Dict]:
        """
        List spaces the bot is a member of
        
        Returns:
            List of space dicts
        """
        # This would make an API call to list spaces
        logger.info("Listing spaces")
        return []


# Convenience functions for direct use
async def send_notification(
    target_type: str,
    target_id: str,
    message: str,
    title: Optional[str] = None,
    priority: str = "normal"
) -> NotificationResponse:
    """
    Send a notification (convenience function)
    
    Args:
        target_type: "user", "space", or "thread"
        target_id: Target identifier
        message: Message text
        title: Optional title
        priority: Message priority
        
    Returns:
        NotificationResponse
    """
    async with GoogleChatTool() as tool:
        request = NotificationRequest(
            target_type=target_type,
            target_id=target_id,
            message=message,
            title=title,
            priority=priority
        )
        return await tool.send_notification(request)


async def send_to_user(
    user_email: str,
    message: str,
    title: Optional[str] = None
) -> NotificationResponse:
    """Send direct message to user (convenience function)"""
    async with GoogleChatTool() as tool:
        return await tool.send_to_user(user_email, message, title)


async def send_to_space(
    space_name: str,
    message: str,
    title: Optional[str] = None
) -> NotificationResponse:
    """Send message to space (convenience function)"""
    async with GoogleChatTool() as tool:
        return await tool.send_to_space(space_name, message, title)


# Synchronous wrappers for non-async contexts
def send_notification_sync(*args, **kwargs) -> NotificationResponse:
    """Synchronous wrapper for send_notification"""
    return asyncio.run(send_notification(*args, **kwargs))


def send_to_user_sync(user_email: str, message: str, title: Optional[str] = None) -> NotificationResponse:
    """Synchronous wrapper for send_to_user"""
    return asyncio.run(send_to_user(user_email, message, title))


def send_to_space_sync(space_name: str, message: str, title: Optional[str] = None) -> NotificationResponse:
    """Synchronous wrapper for send_to_space"""
    return asyncio.run(send_to_space(space_name, message, title))
