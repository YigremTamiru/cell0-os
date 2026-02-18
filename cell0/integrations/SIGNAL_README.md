# Signal Integration for Cell 0 OS

A complete Signal messaging integration for Cell 0 OS, built on signal-cli-rest-api.

## Features

- ✅ **Text Messages**: Send and receive plain text messages
- ✅ **Attachments**: Send and receive images, videos, documents, and more
- ✅ **Group Chats**: Create groups, send group messages, manage members
- ✅ **Reactions**: Send emoji reactions to messages (👍❤️😂 etc.)
- ✅ **Quote/Reply**: Reply to specific messages with context
- ✅ **Link Previews**: Rich previews for shared URLs
- ✅ **Typing Indicators**: Show when typing
- ✅ **Read Receipts**: Track message delivery and read status

## Quick Start

### 1. Start the Signal CLI Container

```bash
# Copy the example environment file
cp .env.signal.example .env.signal

# Edit with your phone number
nano .env.signal

# Start the container
docker-compose -f docker-compose.signal.yml up -d
```

### 2. Register Your Phone Number

**Option A: Register with SMS**
```bash
# Request verification code
curl -X POST http://localhost:8080/v1/register/+1234567890

# Verify with code received via SMS
curl -X POST http://localhost:8080/v1/register/+1234567890/verify \
  -H "Content-Type: application/json" \
  -d '{"verification_code": "123456"}'
```

**Option B: Link to Existing Device**
```bash
# Generate QR code for linking
docker-compose -f docker-compose.signal.yml run --rm signal-cli-register link

# Scan QR code with your Signal mobile app
```

### 3. Use the Signal Bot

```python
import asyncio
from integrations import SignalBot

async def main():
    async with SignalBot() as bot:
        # Send a message
        await bot.send_message("+0987654321", "Hello from Cell 0!")
        
        # Send a file
        await bot.send_attachment("+0987654321", 
            SignalAttachment.from_file("photo.jpg"))
        
        # Reply to a message
        await bot.reply_to_message("+0987654321", original_msg, "Thanks!")
        
        # Send a reaction
        await bot.send_reaction("+0987654321", msg_timestamp, msg_author, "👍")

asyncio.run(main())
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Cell 0 OS Agent                          │
├─────────────────────────────────────────────────────────────┤
│                   engine/tools/signal.py                    │
│              (Agent-facing tool interface)                  │
├─────────────────────────────────────────────────────────────┤
│                 integrations/signal_bot.py                  │
│              (Core Signal bot implementation)               │
├─────────────────────────────────────────────────────────────┤
│              signal-cli-rest-api (Docker)                   │
│          (REST API wrapper around signal-cli)               │
├─────────────────────────────────────────────────────────────┤
│                    Signal Network                           │
└─────────────────────────────────────────────────────────────┘
```

## API Reference

### SignalBot

Main bot class for Signal messaging.

```python
class SignalBot:
    async def send_message(
        self,
        recipient: str,           # Phone number or group ID
        text: str,                # Message text
        attachments: List[SignalAttachment] = None,
        quote_timestamp: int = None,
        quote_author: str = None
    ) -> Dict[str, Any]
    
    async def send_group_message(
        self,
        group_id: str,
        text: str,
        attachments: List[SignalAttachment] = None
    ) -> Dict[str, Any]
    
    async def send_reaction(
        self,
        recipient: str,
        target_timestamp: int,
        target_author: str,
        emoji: str
    ) -> Dict[str, Any]
    
    async def reply_to_message(
        self,
        recipient: str,
        original_message: SignalMessage,
        reply_text: str,
        attachments: List[SignalAttachment] = None
    ) -> Dict[str, Any]
    
    async def get_groups(self) -> List[SignalGroup]
    
    async def create_group(
        self,
        name: str,
        members: List[str],
        description: str = None
    ) -> SignalGroup
    
    def on_message(self, handler: Callable[[SignalMessage], None])
```

### SignalTool (Agent Interface)

Tool interface for Cell 0 agents.

```python
class SignalTool:
    async def send_message(
        self,
        recipient: str,
        text: str,
        attachments: List[str] = None,
        reply_to: Dict[str, Any] = None
    ) -> Dict[str, Any]
    
    async def send_file(
        self,
        recipient: str,
        filepath: str,
        caption: str = None
    ) -> Dict[str, Any]
    
    async def send_reaction(
        self,
        recipient: str,
        message_timestamp: int,
        message_author: str,
        emoji: str
    ) -> Dict[str, Any]
    
    async def list_groups(self) -> List[Dict[str, Any]]
    
    def on_message(self, handler: Callable[[Dict], None])
```

## Configuration

Edit `integrations/signal_config.yaml`:

```yaml
signal_cli_url: "http://localhost:8080"
phone_number: "+1234567890"
api_version: "v1"

auto_receive: true
message_cache_size: 1000
link_previews: true

# Feature toggles
features:
  reactions: true
  quotes: true
  group_management: true
  attachments: true
  link_previews: true
```

## Examples

### Basic Messaging

```python
from integrations import SignalBot

async with SignalBot() as bot:
    # Send text
    await bot.send_message("+1234567890", "Hello!")
    
    # Send with attachment
    await bot.send_message(
        "+1234567890",
        "Check this out!",
        attachments=[SignalAttachment.from_file("image.jpg")]
    )
```

### Group Messaging

```python
# Get groups
groups = await bot.get_groups()
for group in groups:
    print(f"{group.name}: {group.id}")

# Send to group
await bot.send_group_message("group_id", "Hello everyone!")

# Create new group
new_group = await bot.create_group(
    name="Cell 0 Team",
    members=["+1111111111", "+2222222222"],
    description="Cell 0 OS development team"
)
```

### Reactions and Replies

```python
# React to a message
await bot.send_reaction(
    recipient="+1234567890",
    target_timestamp=msg.timestamp,
    target_author=msg.source,
    emoji="👍"
)

# Reply with quote
await bot.reply_to_message(
    recipient="+1234567890",
    original_message=msg,
    reply_text="I agree!"
)
```

### Message Handling

```python
@bot.on_message
def handle_message(message):
    if message.is_reaction:
        print(f"Reaction: {message.reaction_emoji}")
    elif message.is_group_message:
        print(f"Group message in {message.group_id}: {message.text}")
    else:
        print(f"Direct message from {message.source}: {message.text}")
        
        # Reply
        asyncio.create_task(
            bot.send_message(message.source, "Received your message!")
        )
```

### Link Previews

```python
await bot.send_message_with_link_preview(
    recipient="+1234567890",
    text="Check out this project: https://github.com/cell0-os",
    url="https://github.com/cell0-os",
    title="Cell 0 OS",
    description="A sovereign AI operating system"
)
```

## Docker Commands

```bash
# Start Signal CLI
docker-compose -f docker-compose.signal.yml up -d

# View logs
docker-compose -f docker-compose.signal.yml logs -f

# Stop Signal CLI
docker-compose -f docker-compose.signal.yml down

# Backup configuration
docker-compose -f docker-compose.signal.yml --profile backup run --rm signal-cli-backup

# Register new number
docker-compose -f docker-compose.signal.yml --profile register run --rm signal-cli-register
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/test_signal.py -v

# Run with coverage
pytest tests/test_signal.py --cov=integrations.signal_bot --cov=engine.tools.signal -v

# Run integration tests (requires running signal-cli)
pytest tests/test_signal.py -m integration -v

# Run specific test class
pytest tests/test_signal.py::TestSignalBot -v
```

## Security Considerations

1. **Phone Number Privacy**: Your Signal phone number is visible to contacts
2. **Message Encryption**: End-to-end encryption provided by Signal protocol
3. **Storage**: Attachments are stored locally; configure retention policies
4. **Verification**: Always verify contact identities for sensitive communications
5. **Rate Limiting**: Respect Signal's rate limits to avoid account suspension

## Troubleshooting

### Connection Issues

```bash
# Check if signal-cli is running
curl http://localhost:8080/v1/health

# Check logs
docker-compose -f docker-compose.signal.yml logs
```

### Registration Issues

```bash
# Check registration status
curl http://localhost:8080/v1/accounts

# Re-register if needed
curl -X POST http://localhost:8080/v1/register/+1234567890
```

### Message Not Sending

- Verify phone number format (include country code: +1, +44, etc.)
- Check account is registered
- Verify recipient has Signal installed
- Check rate limits haven't been exceeded

## Integration with Cell 0 OS

### MCIC (Multi-Channel Integration Controller)

The Signal tool integrates with Cell 0's MCIC system:

```python
from engine.tools.signal import SignalTool

tool = SignalTool()
await tool.initialize()

# MCIC will automatically register capabilities:
# - messaging.signal.send
# - messaging.signal.receive
# - messaging.signal.groups
# - messaging.signal.reactions
```

### Event Bus

Signal messages are published to the Cell 0 event bus:

```python
# Agents can subscribe to Signal events
event_bus.subscribe("signal.message.received", handler)
event_bus.subscribe("signal.reaction.received", handler)
```

## License

Part of Cell 0 OS - See main LICENSE file

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

## Resources

- [Signal CLI REST API](https://github.com/bbernhard/signal-cli-rest-api)
- [Signal Protocol](https://signal.org/docs/)
- [Cell 0 OS Documentation](../docs/)
