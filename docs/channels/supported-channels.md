# Supported Communication Channels

Cell 0 OS natively supports a 10-Channel Router (`src/channels/adapter.ts`). You can communicate with the OS via your favorite messaging platform, and the Gateway will route your input (along with channel-specific metadata) directly into the Node<->Python bridge.

All 10 channels are **fully implemented** as of v1.3.0. None are stubs.

## Activating Channels

To activate a channel, launch the **Nerve Portal** UI (`http://127.0.0.1:18790`). Open the "Config" tab and input the necessary credentials for your preferred platform.

For QR-based channels (WhatsApp), run the `cell0 channels` CLI command or visit the Config tab to trigger the QR pairing flow. Scan the displayed QR code with your device to complete linking.

The Gateway handles the rest automatically. Port :18789 is used for WebSocket traffic and is auto-selected if the default is already in use.

---

## Channel Status Summary

| # | Channel | Status | Implementation Method |
|---|---------|--------|----------------------|
| 1 | WhatsApp | Implemented | Baileys Web QR |
| 2 | Telegram | Implemented | Native fetch (Bot API) |
| 3 | Discord | Implemented | WebSocket Gateway v10 |
| 4 | Slack | Implemented | Socket Mode |
| 5 | Signal | Implemented | signal-cli |
| 6 | Matrix | Implemented | Client-Server API |
| 7 | Google Chat | Implemented | Webhook |
| 8 | MS Teams | Implemented | Webhook |
| 9 | BlueBubbles/iMessage | Implemented | Local server REST + WebSocket |
| 10 | WebChat | Implemented | Browser-native WebSocket |

---

### 1. Telegram
- **Integration**: `src/channels/telegram.ts`
- **Implementation**: Native fetch against the Telegram Bot API (no third-party library dependency).
- **Requirements**: A Telegram Bot credential from `@BotFather`.
- **Supported Capabilities**: Text, image ingestion, audio (STT via internal Voice node).

### 2. Discord
- **Integration**: `src/channels/discord.ts`
- **Implementation**: WebSocket Gateway API v10 (direct connection, no wrapper library).
- **Requirements**: A Discord Developer Bot Application credential.
- **Supported Capabilities**: Live threads, multi-agent participant tagging, file attachments.

### 3. Slack
- **Integration**: `src/channels/slack.ts`
- **Implementation**: Slack Socket Mode — no public inbound port required.
- **Requirements**: Slack App with Socket Mode enabled; provide the App-level credential via the Config tab.
- **Supported Capabilities**: Workspace-wide integration, native routing to the `Productivity` Agent Domain.

### 4. WhatsApp
- **Integration**: `src/channels/whatsapp.ts`
- **Implementation**: Baileys Web QR — links as a secondary WhatsApp Web session; no Business API account required.
- **QR Pairing**: Run `cell0 channels` or open the Nerve Portal Config tab. A QR code will be displayed. Scan it with your WhatsApp mobile app (Linked Devices > Link a Device). Credentials are persisted to disk after first pairing.
- **Notes**: Uses `src/channels/setup/qr.ts` for the QR display and credential lifecycle. Supports seamless re-link on session expiry.

### 5. Google Chat
- **Integration**: `src/channels/google-chat.ts`
- **Implementation**: Webhook — messages are pushed to a registered Google Chat space endpoint.
- **Requirements**: Google Cloud Service Account JSON (configure path in Nerve Portal Config tab).
- **Notes**: Wraps `cell0/integrations/google_chat_bot.py`. Optimized for the "Project Nexus" Agent Specialist domain.

### 6. Signal
- **Integration**: `src/channels/signal.ts`
- **Implementation**: signal-cli subprocess bridge.
- **Requirements**: A dedicated Signal phone number registered with signal-cli.
- **Notes**: Wraps `cell0/integrations/signal_bot.py` via `signal-cli`. Recommended for end-to-end encrypted communications.

### 7. Native iMessage & BlueBubbles
- **Integration**: `src/channels/bluebubbles.ts`
- **Implementation**: Local server REST API + WebSocket (BlueBubbles server must be running on the same macOS host or reachable LAN).
- **Notes**: iMessage requires a macOS host. BlueBubbles can bridge iMessage traffic to a Linux Gateway instance.

### 8. Microsoft Teams
- **Integration**: `src/channels/msteams.ts`
- **Implementation**: Incoming Webhook — messages are routed through an Azure Bot Framework webhook endpoint.
- **Requirements**: Azure Bot Framework credential (configure via Nerve Portal Config tab).

### 9. Matrix
- **Integration**: `src/channels/matrix.ts`
- **Implementation**: Matrix Client-Server API (direct homeserver communication).
- **Requirements**: Matrix Homeserver URL and account credential (configure via Nerve Portal Config tab).

### 10. Native WebChat
- **Integration**: `src/channels/webchat.ts`
- **Implementation**: Browser-native WebSocket streaming via the Nerve Portal (:18790).
- **Requirements**: None. Native to the Nerve Portal — no external account needed.
- **Capabilities**: Low-latency WebSocket streaming, glassmorphism UI, unconstrained token generation.
