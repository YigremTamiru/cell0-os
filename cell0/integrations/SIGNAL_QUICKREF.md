# Signal Integration Quick Reference

## Installation

```bash
cd /Users/yigremgetachewtamiru/.openclaw/workspace/cell0
./integrations/signal_setup.sh setup
```

## Configuration

Edit `.env.signal`:
```bash
SIGNAL_CLI_PHONE_NUMBER=+1234567890
SIGNAL_CLI_PORT=8080
```

## Start/Stop

```bash
# Start
./integrations/signal_setup.sh start

# Stop
./integrations/signal_setup.sh stop

# Status
./integrations/signal_setup.sh status
```

## Basic Usage

### Send a Message
```python
from integrations import SignalBot

async with SignalBot() as bot:
    await bot.send_message("+0987654321", "Hello!")
```

### Send a File
```python
from integrations import SignalBot, SignalAttachment

async with SignalBot() as bot:
    att = SignalAttachment.from_file("photo.jpg")
    await bot.send_attachment("+0987654321", att, "My photo")
```

### React to Message
```python
await bot.send_reaction(
    "+0987654321",
    target_timestamp=1234567890,
    target_author="+0987654321",
    emoji="👍"
)
```

### Reply to Message
```python
await bot.reply_to_message(
    "+0987654321",
    original_message,
    "This is my reply"
)
```

### Group Message
```python
await bot.send_group_message("group_id", "Hello everyone!")
```

### Message Handler
```python
@bot.on_message
def handle(msg):
    if msg.is_reaction:
        print(f"Reaction: {msg.reaction_emoji}")
    else:
        print(f"Message: {msg.text}")
```

## Agent Tool Usage

```python
from engine.tools.signal import SignalTool

tool = SignalTool()
await tool.initialize()

# Send message
await tool.send_message("+1234567890", "Hello from agent!")

# Send file
await tool.send_file("+1234567890", "/path/to/file.jpg")

# Get groups
groups = await tool.list_groups()

# Receive messages
messages = await tool.receive_messages()
```

## Docker Commands

```bash
# Build
docker-compose -f docker-compose.signal.yml build

# Start
docker-compose -f docker-compose.signal.yml up -d

# Logs
docker-compose -f docker-compose.signal.yml logs -f

# Register phone
curl -X POST http://localhost:8080/v1/register/+1234567890
curl -X POST http://localhost:8080/v1/register/+1234567890/verify \
  -d '{"verification_code": "123456"}'
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/health` | GET | Health check |
| `/v1/accounts` | GET | List accounts |
| `/v1/messages/{number}` | POST | Send message |
| `/v1/receive/{number}` | GET | Receive messages |
| `/v1/groups/{number}` | GET/POST | List/Create groups |
| `/v1/contacts/{number}` | GET | List contacts |

## Troubleshooting

**Connection refused**
```bash
docker-compose -f docker-compose.signal.yml ps
./integrations/signal_setup.sh logs
```

**Not registered**
```bash
./integrations/signal_setup.sh register
```

**Test connection**
```bash
./integrations/signal_setup.sh test
```

## File Structure

```
cell0/
├── integrations/
│   ├── signal_bot.py          # Main bot
│   ├── signal_config.yaml     # Configuration
│   ├── SIGNAL_README.md       # Full documentation
│   └── signal_setup.sh        # Setup script
├── engine/tools/
│   └── signal.py              # Agent tool
├── docker/signal-cli/
│   ├── Dockerfile
│   ├── docker-entrypoint.sh
│   └── healthcheck.sh
├── tests/
│   └── test_signal.py         # Test suite
└── docker-compose.signal.yml  # Docker compose
```

## Features

✅ Text messages  
✅ Attachments  
✅ Group chats  
✅ Reactions  
✅ Quote/reply  
✅ Link previews  
✅ Typing indicators  
