# Google Chat Integration for Cell 0 OS

A comprehensive Google Chat bot integration supporting Cards API, slash commands, threading, and OAuth2 authentication.

## Features

- ✅ **Cards API V2** - Rich interactive UI with buttons, images, and forms
- ✅ **Event Handling** - MESSAGE, ADDED_TO_SPACE, REMOVED_FROM_SPACE, CARD_CLICKED
- ✅ **Threading Support** - Reply in threads for organized conversations
- ✅ **Slash Commands** - `/help`, `/status`, `/ask`, `/tasks`, and extensible framework
- ✅ **OAuth2 Authentication** - Service account authentication
- ✅ **HTTP Webhook Support** - Real-time event handling via webhooks
- ✅ **Pub/Sub Support** - Alternative event streaming (configurable)
- ✅ **1:1 DM & Space Support** - Works in both direct messages and group spaces
- ✅ **Card Builder Utilities** - Easy-to-use API for creating rich cards

## Installation

### 1. Install Dependencies

```bash
pip install aiohttp google-auth pyyaml pytest
```

### 2. Google Cloud Setup

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Note the Project ID and Project Number

2. **Enable Google Chat API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Chat API" and enable it

3. **Create Service Account**:
   - Go to "IAM & Admin" > "Service Accounts"
   - Create a new service account (e.g., `cell0-chat-bot`)
   - Grant roles:
     - `Chat Bot Viewer`
     - `Chat Bot Invoker`
   - Create and download a JSON key file

4. **Configure OAuth Scopes**:
   - Required scopes:
     - `https://www.googleapis.com/auth/chat.bot`
     - `https://www.googleapis.com/auth/chat.messages`

### 3. Bot Configuration

1. **Copy and customize config**:
   ```bash
   cp cell0/integrations/google_chat_config.yaml cell0/integrations/google_chat_config.local.yaml
   ```

2. **Set environment variables**:
   ```bash
   export GOOGLE_PROJECT_ID="your-project-id"
   export GOOGLE_PROJECT_NUMBER="your-project-number"
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
   export CELL0_API_KEY="your-cell0-api-key"
   ```

3. **Edit the config file** with your specific settings.

### 4. Google Chat App Configuration

1. **Go to Google Chat API Configuration**:
   - In Cloud Console: "APIs & Services" > "Google Chat API" > "Configuration"

2. **Set App Details**:
   - App name: "Cell 0 Bot"
   - Avatar URL: Your bot avatar
   - Description: "Sovereign Edge AI Assistant"

3. **Connection Settings**:
   - Choose **HTTP endpoint** or **Pub/Sub**
   - For HTTP: Enter your webhook URL (e.g., `https://your-domain.com/chat/webhook`)
   - For development, you can use [ngrok](https://ngrok.com/) to expose localhost

4. **Slash Commands** (add these):
   | Command | Description | Usage Hint |
   |---------|-------------|------------|
   | `/help` | Show help | |
   | `/status` | Check system status | |
   | `/ask` | Ask the AI | Your question |
   | `/tasks` | Manage tasks | list/add/done |
   | `/profile` | View profile | |

5. **Visibility**:
   - Set to "Specific people and groups in your domain"
   - Or "Private (only specific people)" for testing

6. **Save and Publish**

## Usage

### Running the Bot

```python
import asyncio
from cell0.integrations.google_chat_bot import create_bot

async def main():
    bot = create_bot("cell0/integrations/google_chat_config.yaml")
    
    # Register custom handlers
    @bot.on_event("MESSAGE")
    async def on_message(message):
        if "hello" in message.text.lower():
            return {"text": f"Hello {message.user_name}!"}
    
    @bot.on_slash_command("/echo")
    async def echo_command(message, args):
        return {"text": f"Echo: {args}"}
    
    # Start the bot
    async with bot:
        app = await bot.create_webhook_server()
        # Run the web server...

if __name__ == "__main__":
    asyncio.run(main())
```

### Using the Tool Interface

```python
import asyncio
from cell0.engine.tools.google_chat import GoogleChatTool

async def notify_user():
    async with GoogleChatTool() as tool:
        # Send simple message
        response = await tool.send_to_user(
            user_email="user@example.com",
            message="Hello from Cell 0!",
            title="Greeting"
        )
        
        # Send a task card
        card = tool.create_task_card(
            task_title="Review Report",
            task_description="Please review the Q4 report",
            task_id="123",
            status="pending",
            due_date="2024-12-31"
        )
        
        response = await tool.send_notification(
            request=NotificationRequest(
                target_type="user",
                target_id="user@example.com",
                title="New Task",
                card_data=card["cardsV2"][0]["card"]
            )
        )

asyncio.run(notify_user())
```

### Card Builder Examples

```python
from cell0.integrations.google_chat_bot import CardBuilder

# Create a welcome card
card = CardBuilder()
card.set_header(
    title="🌊 Welcome",
    subtitle="Cell 0 OS",
    image_url="https://cell0.ai/logo.png"
)

card.add_section("Introduction")
card.add_text_paragraph("Welcome to Cell 0 OS - your sovereign edge AI.")

card.add_section("Quick Actions")
card.add_button_row([
    CardBuilder.create_button(
        "Documentation",
        CardBuilder.action_open_link("https://docs.cell0.ai"),
        icon="BOOKMARK"
    ),
    CardBuilder.create_button(
        "Dashboard", 
        CardBuilder.action_open_link("https://cell0.ai/dashboard"),
        icon="DASHBOARD"
    )
])

response_json = card.build()
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest cell0/tests/test_google_chat.py -v

# Run specific test class
pytest cell0/tests/test_google_chat.py::TestCardBuilder -v

# Run with coverage
pytest cell0/tests/test_google_chat.py --cov=cell0 --cov-report=html
```

## API Reference

### GoogleChatBot

Main bot class for handling Google Chat events.

**Key Methods:**
- `handle_event(event_data)` - Process incoming events
- `send_message(space_name, text, cards, thread_name)` - Send messages
- `send_direct_message(user_email, text, cards)` - Send DMs
- `on_event(event_type)` - Decorator for event handlers
- `on_slash_command(command_name)` - Decorator for slash commands
- `on_card_click(action_name)` - Decorator for card interactions

### CardBuilder

Utility for creating rich card UIs.

**Methods:**
- `set_header(title, subtitle, image_url)` - Set card header
- `add_section(header, collapsible)` - Add section
- `add_text_paragraph(text)` - Add text
- `add_image(url, alt_text)` - Add image
- `add_button(text, action)` - Add button
- `add_key_value(key, value)` - Add key-value pair
- `add_input(name, label)` - Add text input
- `add_selection_input(name, label, items)` - Add dropdown
- `build()` - Generate card JSON

### GoogleChatTool

Agent interface for sending notifications and creating cards.

**Methods:**
- `send_notification(request)` - Send notification
- `send_to_user(email, message, title)` - Send DM
- `send_to_space(space, message, title)` - Send to space
- `create_task_card(...)` - Create task card
- `create_alert_card(...)` - Create alert card
- `create_status_card(...)` - Create status card

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY cell0/ ./cell0/
COPY config/ ./config/

ENV GOOGLE_APPLICATION_CREDENTIALS=/app/config/credentials.json

EXPOSE 8080

CMD ["python", "-m", "cell0.integrations.google_chat_bot"]
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_PROJECT_ID` | Google Cloud Project ID | Yes |
| `GOOGLE_PROJECT_NUMBER` | Google Cloud Project Number | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | Yes |
| `CELL0_API_KEY` | Cell 0 OS API key | No |
| `ADMIN_EMAIL` | Admin user email | No |

### Webhook Security

For production, ensure:
1. Use HTTPS endpoints
2. Verify request tokens (configure `verify_tokens: true`)
3. Restrict allowed IPs if possible
4. Use proper firewall rules

## Troubleshooting

### Bot not responding
- Check webhook URL is accessible from internet
- Verify Google Chat API is enabled
- Check service account has proper permissions
- Review bot logs for errors

### Authentication errors
- Verify `GOOGLE_APPLICATION_CREDENTIALS` path is correct
- Check service account key is valid (not expired)
- Ensure Chat API scopes are configured

### Cards not displaying
- Verify Cards V2 API is being used (not deprecated Cards API)
- Check card JSON structure is valid
- Review Google Chat API logs

## License

Part of Cell 0 OS - Sovereign Edge Model

---

*The glass has melted. 🌊♾️💫*
