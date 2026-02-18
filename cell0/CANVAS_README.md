# Cell 0 Canvas / A2UI System

A live visual workspace where agents can render UI components in real-time via the Agent-to-UI (A2UI) protocol.

## Overview

The Canvas system provides a WebSocket-based real-time UI rendering platform that allows agents to:

- Build dynamic user interfaces with code
- Update components in real-time
- Handle user interactions (clicks, inputs, etc.)
- Render charts and visualizations
- Capture screenshots
- Support mobile-responsive designs

## Architecture

```
┌─────────────────┐     WebSocket      ┌─────────────────┐
│   Agent Tool    │ ◄────────────────► │  Canvas Server  │
│  (Python API)   │    A2UI Protocol   │   (Port 18802)  │
└─────────────────┘                    └────────┬────────┘
                                                │
                                                │ HTTP
                                                ▼
                                        ┌─────────────────┐
                                        │  HTML/JS Client │
                                        │  (Browser)      │
                                        └─────────────────┘
```

## Quick Start

### 1. Start the Canvas Server

```python
from gui.canvas_server import CanvasService

service = CanvasService(host="0.0.0.0", ws_port=18802)
await service.start()
```

### 2. Open the Canvas in Browser

Navigate to: `http://localhost:18802/canvas/{canvas_id}`

### 3. Render UI from Agent

```python
from engine.tools.canvas import CanvasTool

canvas = CanvasTool(canvas_id="my_canvas")
await canvas.connect()

# Build UI
await canvas.render(
    canvas.card("Welcome",
        canvas.text("Hello from Agent!"),
        canvas.button("Click Me", on_click="handle_click")
    )
)

# Register event handler
canvas.on("handle_click", lambda data: print("Clicked!"))
```

## Components

### Basic Components

| Component | Factory Function | Description |
|-----------|------------------|-------------|
| Text | `text(content)` | Static text display |
| Image | `image(src, alt)` | Image display |
| Button | `button(label, on_click)` | Clickable button |
| Input | `input(name, placeholder)` | Text input field |
| TextArea | `textarea(name)` | Multi-line text input |
| Select | `select(name, options)` | Dropdown selection |
| Checkbox | `checkbox(name, label)` | Checkbox input |
| Radio | `radio(name, options)` | Radio button group |

### Layout Components

| Component | Factory Function | Description |
|-----------|------------------|-------------|
| Container | `container(*children)` | Generic container |
| Card | `card(title, *children)` | Card with header |
| Grid | `grid(columns, *children)` | CSS Grid layout |
| HStack | `hstack(*children)` | Horizontal flex layout |
| VStack | `vstack(*children)` | Vertical flex layout |
| Center | `center(child)` | Centered content |

### Display Components

| Component | Factory Function | Description |
|-----------|------------------|-------------|
| Chart | `line_chart()`, `bar_chart()`, `pie_chart()` | Data visualization |
| Progress | `progress(value, max)` | Progress bar |
| Badge | `badge(content)` | Status badge |
| Header | `header(title, subtitle)` | Page header |
| Footer | `footer(content)` | Page footer |
| Navbar | `navbar(items)` | Navigation bar |
| Modal | `modal(title, is_open)` | Modal dialog |

## A2UI Protocol

### Message Types

```json
// Render - Send full component tree
{
  "type": "render",
  "timestamp": "2024-01-01T00:00:00Z",
  "payload": { /* component tree */ }
}

// Update - Update specific component
{
  "type": "update",
  "timestamp": "2024-01-01T00:00:00Z",
  "payload": {
    "componentId": "abc123",
    "props": { "content": "New text" }
  }
}

// Event - User interaction
{
  "type": "event",
  "timestamp": "2024-01-01T00:00:00Z",
  "payload": {
    "handlerId": "click_handler",
    "data": { "type": "click", "value": "" }
  }
}
```

### Event Flow

1. Agent renders UI with event handlers
2. User interacts with UI (clicks button, types input)
3. Browser sends event message via WebSocket
4. Server routes event to registered handler
5. Handler executes and optionally returns result
6. Agent can update UI based on result

## Examples

### Simple Form

```python
from engine.tools.canvas import CanvasTool

canvas = CanvasTool()

form = canvas.form("user_form", on_submit="submit_form",
    canvas.vstack(
        canvas.input("name", "Enter your name"),
        canvas.input("email", "Enter your email", input_type="email"),
        canvas.button("Submit", variant="primary")
    )
)

await canvas.render(form)

def handle_submit(data):
    print(f"Form submitted: {data}")
    return {"message": "Success!"}

canvas.on("submit_form", handle_submit)
```

### Dashboard with Charts

```python
# Create metrics cards
metrics = canvas.grid(3,
    canvas.metric_card("Revenue", "$12.5K", "+12%", True),
    canvas.metric_card("Users", "1,234", "+5%", True),
    canvas.metric_card("Active", "89%", "-2%", False)
)

# Create chart
sales_chart = canvas.line_chart(
    labels=["Jan", "Feb", "Mar", "Apr", "May"],
    datasets=[
        canvas.dataset("Sales", [10, 25, 20, 35, 40], "#6366f1"),
        canvas.dataset("Target", [15, 20, 25, 30, 35], "#22c55e")
    ]
)

# Layout dashboard
await canvas.render(
    canvas.vstack(
        canvas.header("Sales Dashboard", "Q1 2024"),
        metrics,
        canvas.card("Sales Trend", sales_chart)
    )
)
```

### Real-time Updates

```python
# Initial render
status = canvas.badge("Processing...", "warning")
await canvas.render(status)

# Later... update the badge
await canvas.update(status.id, 
    content="Complete!", 
    variant="success"
)
```

## Testing

Run the test suite:

```bash
cd /Users/yigremgetachewtamiru/.openclaw/workspace/cell0
python -m pytest tests/test_canvas.py -v
```

## API Reference

### CanvasTool

The main interface for agents to interact with the Canvas.

**Methods:**

- `connect()` - Connect to Canvas server
- `render(component)` - Render a component tree
- `update(component_id, **props)` - Update a component
- `clear()` - Clear the canvas
- `on(handler_id, callback)` - Register event handler
- `off(handler_id)` - Unregister event handler
- `screenshot()` - Request screenshot
- `set_data(key, value)` - Store data in canvas state
- `get_data(key)` - Retrieve data from canvas state

### CanvasServer

WebSocket server managing client connections and message routing.

**Methods:**

- `start()` - Start the server
- `stop()` - Stop the server
- `create_canvas(canvas_id)` - Create new canvas session
- `delete_canvas(canvas_id)` - Delete canvas session
- `register_handler(handler_id, callback)` - Register global handler
- `broadcast_to_canvas(canvas_id, message)` - Broadcast to all clients

## File Structure

```
cell0/
├── gui/
│   ├── __init__.py
│   ├── canvas_components.py    # Component library
│   ├── canvas_server.py        # WebSocket server
│   ├── canvas_templates/
│   │   └── canvas.html         # UI template
│   └── requirements.txt
├── engine/
│   └── tools/
│       ├── __init__.py
│       └── canvas.py           # Agent tool interface
└── tests/
    ├── __init__.py
    └── test_canvas.py          # Test suite
```

## License

Cell 0 OS - Sovereign Edge Model Operating System
