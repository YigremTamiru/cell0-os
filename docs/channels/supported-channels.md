# Supported Communication Channels

Cell 0 OS natively supports an 11-Channel Router (`src/channels/adapter.ts`). You can communicate with the OS via your favorite messaging platform, and the Gateway will route your input (along with channel-specific metadata) directly into the Node<->Python bridge.

## Activating Channels

To activate a channel, launch the **Nerve Portal** UI (`http://127.0.0.1:18790`). Open the "Config" tab and input the necessary tokens for your preferred platform.

The Gateway handles the rest automatically.

---

### 1. Telegram
- **Integration**: `src/channels/telegram.ts`
- **Requirements**: A Telegram Bot Token from `@BotFather`.
- **Supported Capabilities**: Text, image ingestion, audio (STT via internal Voice node).

### 2. Discord
- **Integration**: `src/channels/discord.ts`
- **Requirements**: A Discord Developer Bot Application Token.
- **Supported Capabilities**: Live threads, multi-agent participant tagging, file attachments.

### 3. Slack
- **Integration**: `src/channels/slack.ts`
- **Requirements**: Slack API Token.
- **Supported Capabilities**: Workspace-wide integration, native routing to the `Productivity` Agent Domain.

### 4. WhatsApp
- **Integration**: `src/channels/whatsapp.ts`
- **Requirements**: Meta WhatsApp Business Cloud API Token.
- **Notes**: Supports seamless integration via Baileys if running the bridge natively.

### 5. Google Chat
- **Integration**: `src/channels/google-chat.ts`
- **Requirements**: Google Cloud Service Account JSON.
- **Notes**: Wraps `cell0/integrations/google_chat_bot.py`. Highly optimized for the "Project Nexus" Agent Specialist.

### 6. Signal
- **Integration**: `src/channels/signal.ts`
- **Requirements**: A dedicated Signal phone number.
- **Notes**: Wraps `cell0/integrations/signal_bot.py` via `signal-cli`. Highly recommended for encrypted communications.

### 7. Native iMessage & BlueBubbles
- **Integration**: `src/channels/imessage.ts` & `src/channels/bluebubbles.ts`
- **Notes**: iMessage only functions on macOS hosts. BlueBubbles can bridge iMessage traffic to a Linux Gateway.

### 8. Microsoft Teams
- **Integration**: `src/channels/msteams.ts`
- **Requirements**: Azure Bot Framework tokens.

### 9. Matrix
- **Integration**: `src/channels/matrix.ts`
- **Requirements**: Matrix Homeserver credential.

### 10. Native WebChat
- **Integration**: `src/channels/webchat.ts`
- **Requirements**: None. Native to the Nerve Portal.
- **Capabilities**: Low-latency WebSocket streaming, glassmorphism UI, unconstrained token generation.
