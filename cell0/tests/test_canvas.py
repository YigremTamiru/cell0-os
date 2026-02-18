"""
Tests for Cell 0 Canvas/A2UI System
"""
import asyncio
import pytest
import json
import websockets
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import sys
sys.path.insert(0, '/Users/yigremgetachewtamiru/.openclaw/workspace/cell0')

from gui.canvas_components import (
    Component, ComponentType, ComponentStyle, ComponentEvent,
    CanvasState, A2UIMessage,
    text, image, button, input_field, textarea, select,
    checkbox, radio, form, chart, container, grid, card,
    modal, progress, badge, divider, header, footer, navbar,
    hstack, vstack, center,
    line_chart_data, bar_chart_data, pie_chart_data, dataset,
    ChartType
)

from gui.canvas_server import CanvasServer, CanvasConnection, CanvasService
from engine.tools.canvas import CanvasTool, QuickUI


# =============================================================================
# Component Tests
# =============================================================================

class TestComponent:
    """Test the Component class and factory functions"""
    
    def test_text_component(self):
        """Test text component creation"""
        t = text("Hello World", font_size="16px")
        assert t.type == ComponentType.TEXT
        assert t.props["content"] == "Hello World"
        assert t.style.font_size == "16px"
        assert t.id is not None
    
    def test_image_component(self):
        """Test image component creation"""
        img = image("https://example.com/image.png", "Alt text", width="100px")
        assert img.type == ComponentType.IMAGE
        assert img.props["src"] == "https://example.com/image.png"
        assert img.props["alt"] == "Alt text"
        assert img.style.width == "100px"
    
    def test_button_component(self):
        """Test button component creation"""
        btn = button("Click Me", handler="click_handler", variant="primary")
        assert btn.type == ComponentType.BUTTON
        assert btn.props["label"] == "Click Me"
        assert btn.props["variant"] == "primary"
        assert len(btn.events) == 1
        assert btn.events[0].type == "click"
        assert btn.events[0].handler == "click_handler"
    
    def test_input_component(self):
        """Test input component creation"""
        inp = input_field("username", "Enter username", "text", "", "input_handler")
        assert inp.type == ComponentType.INPUT
        assert inp.props["name"] == "username"
        assert inp.props["placeholder"] == "Enter username"
        assert inp.props["type"] == "text"
        assert len(inp.events) == 1
    
    def test_select_component(self):
        """Test select component creation"""
        options = [
            {"value": "a", "label": "Option A"},
            {"value": "b", "label": "Option B"}
        ]
        sel = select("choice", options, "a", "change_handler")
        assert sel.type == ComponentType.SELECT
        assert sel.props["name"] == "choice"
        assert len(sel.props["options"]) == 2
        assert sel.props["value"] == "a"
    
    def test_checkbox_component(self):
        """Test checkbox component creation"""
        cb = checkbox("agree", "I agree", True, "change_handler")
        assert cb.type == ComponentType.CHECKBOX
        assert cb.props["name"] == "agree"
        assert cb.props["label"] == "I agree"
        assert cb.props["checked"] == True
    
    def test_radio_component(self):
        """Test radio component creation"""
        options = [
            {"value": "small", "label": "Small"},
            {"value": "large", "label": "Large"}
        ]
        rad = radio("size", options, "small", "change_handler")
        assert rad.type == ComponentType.RADIO
        assert rad.props["name"] == "size"
        assert len(rad.props["options"]) == 2
    
    def test_chart_component(self):
        """Test chart component creation"""
        data = {
            "labels": ["Jan", "Feb", "Mar"],
            "datasets": [{"data": [10, 20, 30]}]
        }
        c = chart(ChartType.LINE, data)
        assert c.type == ComponentType.CHART
        assert c.props["chartType"] == "line"
        assert "labels" in c.props["data"]
    
    def test_container_with_children(self):
        """Test container with nested children"""
        cont = container(padding="20px")
        child1 = text("Child 1")
        child2 = text("Child 2")
        
        cont.add_child(child1)
        cont.add_child(child2)
        
        assert len(cont.children) == 2
        assert cont.children[0].props["content"] == "Child 1"
        assert cont.children[1].props["content"] == "Child 2"
        assert cont.style.padding == "20px"
    
    def test_card_component(self):
        """Test card component"""
        c = card("Card Title", background_color="#fff")
        assert c.type == ComponentType.CARD
        assert c.props["title"] == "Card Title"
        assert c.style.background_color == "#fff"
    
    def test_modal_component(self):
        """Test modal component"""
        m = modal("Confirm", True, "close_handler")
        assert m.type == ComponentType.MODAL
        assert m.props["title"] == "Confirm"
        assert m.props["isOpen"] == True
    
    def test_progress_component(self):
        """Test progress component"""
        p = progress(75, 100, True)
        assert p.type == ComponentType.PROGRESS
        assert p.props["value"] == 75
        assert p.props["max"] == 100
        assert p.props["showLabel"] == True
    
    def test_badge_component(self):
        """Test badge component"""
        b = badge("New", "success")
        assert b.type == ComponentType.BADGE
        assert b.props["content"] == "New"
        assert b.props["variant"] == "success"
    
    def test_header_component(self):
        """Test header component"""
        h = header("Page Title", "Subtitle here")
        assert h.type == ComponentType.HEADER
        assert h.props["title"] == "Page Title"
        assert h.props["subtitle"] == "Subtitle here"
    
    def test_footer_component(self):
        """Test footer component"""
        f = footer("© 2024 Cell 0")
        assert f.type == ComponentType.FOOTER
        assert f.props["content"] == "© 2024 Cell 0"
    
    def test_navbar_component(self):
        """Test navbar component"""
        items = [
            {"label": "Home", "href": "/"},
            {"label": "About", "href": "/about"}
        ]
        nav = navbar(items, "Brand", "nav_handler")
        assert nav.type == ComponentType.NAVBAR
        assert nav.props["brand"] == "Brand"
        assert len(nav.props["items"]) == 2
        assert len(nav.events) == 1
    
    def test_grid_layout(self):
        """Test grid layout"""
        g = grid(3, "20px")
        assert g.type == ComponentType.GRID
        assert g.style.display == "grid"
        assert "repeat(3, 1fr)" in g.style.grid_template
        assert g.style.gap == "20px"
    
    def test_hstack_layout(self):
        """Test horizontal stack"""
        child1 = text("A")
        child2 = text("B")
        stack = hstack(child1, child2, gap="10px", align="center")
        
        assert stack.type == ComponentType.CONTAINER
        assert stack.style.display == "flex"
        assert stack.style.flex_direction == "row"
        assert stack.style.gap == "10px"
        assert len(stack.children) == 2
    
    def test_vstack_layout(self):
        """Test vertical stack"""
        child1 = text("A")
        child2 = text("B")
        stack = vstack(child1, child2, gap="10px")
        
        assert stack.type == ComponentType.CONTAINER
        assert stack.style.display == "flex"
        assert stack.style.flex_direction == "column"
        assert len(stack.children) == 2
    
    def test_center_layout(self):
        """Test center layout"""
        child = text("Centered")
        centered = center(child)
        
        assert centered.type == ComponentType.CONTAINER
        assert centered.style.display == "flex"
        assert centered.style.justify_content == "center"
        assert centered.style.align_items == "center"
    
    def test_component_to_dict(self):
        """Test component serialization"""
        t = text("Test", font_size="14px")
        t.add_event(ComponentEvent("click", "handler"))
        
        data = t.to_dict()
        
        assert data["type"] == "text"
        assert data["props"]["content"] == "Test"
        assert "fontSize" in data["style"]
        assert len(data["events"]) == 1
        assert data["events"][0]["type"] == "click"
    
    def test_component_nested_to_dict(self):
        """Test nested component serialization"""
        parent = container()
        parent.add_child(text("Child"))
        
        data = parent.to_dict()
        
        assert len(data["children"]) == 1
        assert data["children"][0]["type"] == "text"


# =============================================================================
# Chart Data Helper Tests
# =============================================================================

class TestChartData:
    """Test chart data helper functions"""
    
    def test_line_chart_data(self):
        """Test line chart data creation"""
        labels = ["Jan", "Feb", "Mar"]
        datasets = [
            {"label": "Sales", "data": [10, 20, 30]}
        ]
        data = line_chart_data(labels, datasets)
        
        assert data["labels"] == labels
        assert len(data["datasets"]) == 1
        assert data["datasets"][0]["label"] == "Sales"
    
    def test_bar_chart_data(self):
        """Test bar chart data creation"""
        labels = ["A", "B", "C"]
        datasets = [
            {"label": "Values", "data": [5, 10, 15]}
        ]
        data = bar_chart_data(labels, datasets)
        
        assert data["labels"] == labels
        assert len(data["datasets"]) == 1
    
    def test_pie_chart_data(self):
        """Test pie chart data creation"""
        labels = ["Red", "Blue", "Green"]
        values = [30, 40, 30]
        data = pie_chart_data(labels, values)
        
        assert data["labels"] == labels
        assert len(data["datasets"]) == 1
        assert data["datasets"][0]["data"] == values
        assert "backgroundColor" in data["datasets"][0]
    
    def test_pie_chart_with_custom_colors(self):
        """Test pie chart with custom colors"""
        labels = ["A", "B"]
        values = [50, 50]
        colors = ["#ff0000", "#00ff00"]
        data = pie_chart_data(labels, values, colors)
        
        assert data["datasets"][0]["backgroundColor"] == colors
    
    def test_dataset_creation(self):
        """Test dataset helper"""
        ds = dataset("Revenue", [100, 200, 300], "#6366f1")
        
        assert ds["label"] == "Revenue"
        assert ds["data"] == [100, 200, 300]
        assert ds["borderColor"] == "#6366f1"
        assert ds["backgroundColor"] == "#6366f140"  # With transparency


# =============================================================================
# CanvasState Tests
# =============================================================================

class TestCanvasState:
    """Test CanvasState management"""
    
    def test_canvas_state_creation(self):
        """Test canvas state initialization"""
        state = CanvasState("test_canvas")
        assert state.canvas_id == "test_canvas"
        assert state.root is None
        assert len(state.components) == 0
    
    def test_set_root_component(self):
        """Test setting root component"""
        state = CanvasState("test")
        root = container().add_child(text("Hello"))
        
        state.set_root(root)
        
        assert state.root == root
        assert len(state.components) == 2  # root + child
        assert state.components[root.id] == root
    
    def test_get_component(self):
        """Test getting component by ID"""
        state = CanvasState("test")
        root = container()
        child = text("Child")
        root.add_child(child)
        state.set_root(root)
        
        assert state.get_component(child.id) == child
        assert state.get_component("nonexistent") is None
    
    def test_update_component(self):
        """Test updating component properties"""
        state = CanvasState("test")
        t = text("Original")
        state.set_root(t)
        
        result = state.update_component(t.id, content="Updated")
        
        assert result == True
        assert t.props["content"] == "Updated"
    
    def test_update_component_style(self):
        """Test updating component style"""
        state = CanvasState("test")
        t = text("Test")
        state.set_root(t)
        
        result = state.update_component(t.id, style_font_size="20px")
        
        assert result == True
        assert t.style.font_size == "20px"
    
    def test_update_nonexistent_component(self):
        """Test updating non-existent component"""
        state = CanvasState("test")
        result = state.update_component("fake_id", content="Test")
        assert result == False
    
    def test_remove_component(self):
        """Test removing component"""
        state = CanvasState("test")
        t = text("Test")
        state.set_root(t)
        
        result = state.remove_component(t.id)
        
        assert result == True
        assert t.id not in state.components
    
    def test_data_store(self):
        """Test data store operations"""
        state = CanvasState("test")
        
        state.set_data("key1", "value1")
        state.set_data("key2", {"nested": "data"})
        
        assert state.get_data("key1") == "value1"
        assert state.get_data("key2") == {"nested": "data"}
        assert state.get_data("nonexistent", "default") == "default"
    
    def test_event_handler_registration(self):
        """Test event handler registration"""
        state = CanvasState("test")
        
        def handler(data):
            return {"result": "ok"}
        
        state.register_handler("test_handler", handler)
        
        assert "test_handler" in state.event_handlers
    
    def test_event_handling(self):
        """Test event handling"""
        state = CanvasState("test")
        
        def handler(data):
            return {"received": data}
        
        state.register_handler("my_handler", handler)
        result = state.handle_event("my_handler", {"value": 123})
        
        assert result == {"received": {"value": 123}}
    
    def test_handle_unknown_event(self):
        """Test handling unknown event"""
        state = CanvasState("test")
        result = state.handle_event("unknown", {})
        assert result is None
    
    def test_to_dict(self):
        """Test canvas state serialization"""
        state = CanvasState("test_canvas")
        root = text("Hello")
        state.set_root(root)
        
        data = state.to_dict()
        
        assert data["canvasId"] == "test_canvas"
        assert data["componentCount"] == 1
        assert data["root"] is not None


# =============================================================================
# A2UI Message Tests
# =============================================================================

class TestA2UIMessage:
    """Test A2UI protocol messages"""
    
    def test_render_message(self):
        """Test render message creation"""
        t = text("Hello")
        msg = A2UIMessage.render(t)
        
        assert msg["type"] == "render"
        assert "timestamp" in msg
        assert msg["payload"]["type"] == "text"
    
    def test_update_message(self):
        """Test update message creation"""
        msg = A2UIMessage.update("comp_123", content="New text", color="red")
        
        assert msg["type"] == "update"
        assert msg["payload"]["componentId"] == "comp_123"
        assert msg["payload"]["props"]["content"] == "New text"
    
    def test_event_message(self):
        """Test event message creation"""
        event_data = {"type": "click", "value": "test"}
        msg = A2UIMessage.event("handler_123", event_data)
        
        assert msg["type"] == "event"
        assert msg["payload"]["handlerId"] == "handler_123"
        assert msg["payload"]["data"] == event_data
    
    def test_state_update_message(self):
        """Test state update message"""
        data = {"key": "value"}
        msg = A2UIMessage.state_update(data)
        
        assert msg["type"] == "state_update"
        assert msg["payload"] == data
    
    def test_screenshot_message(self):
        """Test screenshot message"""
        msg = A2UIMessage.screenshot("base64data", "png")
        
        assert msg["type"] == "screenshot"
        assert msg["payload"]["data"] == "base64data"
        assert msg["payload"]["format"] == "png"
    
    def test_error_message(self):
        """Test error message"""
        msg = A2UIMessage.error("Something went wrong", "ERR_001")
        
        assert msg["type"] == "error"
        assert msg["payload"]["message"] == "Something went wrong"
        assert msg["payload"]["code"] == "ERR_001"
    
    def test_ping_message(self):
        """Test ping message"""
        msg = A2UIMessage.ping()
        
        assert msg["type"] == "ping"
        assert "timestamp" in msg
    
    def test_pong_message(self):
        """Test pong message"""
        msg = A2UIMessage.pong()
        
        assert msg["type"] == "pong"
        assert "timestamp" in msg


# =============================================================================
# CanvasServer Tests
# =============================================================================

@pytest.mark.asyncio
class TestCanvasServer:
    """Test CanvasServer functionality"""
    
    async def test_server_initialization(self):
        """Test server initialization"""
        server = CanvasServer(host="127.0.0.1", port=18802)
        assert server.host == "127.0.0.1"
        assert server.port == 18802
        assert len(server.clients) == 0
        assert len(server.sessions) == 0
    
    async def test_create_canvas(self):
        """Test canvas creation"""
        server = CanvasServer()
        session = server.create_canvas("test_canvas")
        
        assert "test_canvas" in server.sessions
        assert session.canvas_id == "test_canvas"
    
    async def test_get_canvas(self):
        """Test getting canvas session"""
        server = CanvasServer()
        server.create_canvas("test_canvas")
        
        session = server.get_canvas("test_canvas")
        assert session is not None
        assert session.canvas_id == "test_canvas"
        
        nonexistent = server.get_canvas("nonexistent")
        assert nonexistent is None
    
    async def test_delete_canvas(self):
        """Test canvas deletion"""
        server = CanvasServer()
        server.create_canvas("test_canvas")
        
        result = server.delete_canvas("test_canvas")
        
        assert result == True
        assert "test_canvas" not in server.sessions
    
    async def test_delete_nonexistent_canvas(self):
        """Test deleting non-existent canvas"""
        server = CanvasServer()
        result = server.delete_canvas("nonexistent")
        assert result == False
    
    async def test_register_handler(self):
        """Test handler registration"""
        server = CanvasServer()
        
        def handler(data):
            return "ok"
        
        server.register_handler("test_handler", handler)
        
        assert "test_handler" in server._global_handlers
    
    async def test_unregister_handler(self):
        """Test handler unregistration"""
        server = CanvasServer()
        server.register_handler("test_handler", lambda x: x)
        
        result = server.unregister_handler("test_handler")
        
        assert result == True
        assert "test_handler" not in server._global_handlers
    
    async def test_get_stats(self):
        """Test getting server stats"""
        server = CanvasServer()
        server.create_canvas("test")
        
        stats = server.get_stats()
        
        assert "connectedClients" in stats
        assert "activeCanvases" in stats
        assert stats["activeCanvases"] == 1


# =============================================================================
# CanvasTool Tests
# =============================================================================

@pytest.mark.asyncio
class TestCanvasTool:
    """Test CanvasTool functionality"""
    
    async def test_canvas_tool_initialization(self):
        """Test tool initialization"""
        tool = CanvasTool(canvas_id="test_tool", auto_connect=False)
        assert tool.canvas_id == "test_tool"
        assert tool._connected == False
    
    async def test_component_builders(self):
        """Test component builder methods"""
        tool = CanvasTool(auto_connect=False)
        
        # Test text
        t = tool.text("Hello")
        assert t.type == ComponentType.TEXT
        
        # Test button
        b = tool.button("Click", on_click="handler")
        assert b.type == ComponentType.BUTTON
        assert len(b.events) == 1
        
        # Test input
        i = tool.input("name", on_input="handler")
        assert i.type == ComponentType.INPUT
        
        # Test card
        c = tool.card("Title", tool.text("Content"))
        assert c.type == ComponentType.CARD
        assert len(c.children) == 1
    
    async def test_layout_builders(self):
        """Test layout builder methods"""
        tool = CanvasTool(auto_connect=False)
        
        # Test hstack
        hs = tool.hstack(tool.text("A"), tool.text("B"))
        assert hs.style.display == "flex"
        assert hs.style.flex_direction == "row"
        
        # Test vstack
        vs = tool.vstack(tool.text("A"), tool.text("B"))
        assert vs.style.flex_direction == "column"
    
    async def test_chart_builders(self):
        """Test chart builder methods"""
        tool = CanvasTool(auto_connect=False)
        
        line = tool.line_chart(
            ["Jan", "Feb"],
            [tool.dataset("Sales", [10, 20])]
        )
        assert line.type == ComponentType.CHART
        assert line.props["chartType"] == "line"
    
    def test_handler_registration(self):
        """Test event handler registration"""
        tool = CanvasTool(auto_connect=False)
        
        def handler(data):
            return "result"
        
        tool.on("my_handler", handler)
        
        assert "my_handler" in tool._handlers
    
    def test_handler_unregistration(self):
        """Test event handler unregistration"""
        tool = CanvasTool(auto_connect=False)
        tool.on("handler", lambda x: x)
        
        tool.off("handler")
        
        assert "handler" not in tool._handlers
    
    def test_get_url(self):
        """Test URL generation"""
        tool = CanvasTool(canvas_id="my_canvas", auto_connect=False)
        
        assert tool.get_url() == "http://localhost:18802/canvas/my_canvas"
        assert tool.get_ws_url() == "ws://localhost:18802/canvas/my_canvas"


# =============================================================================
# QuickUI Tests
# =============================================================================

class TestQuickUI:
    """Test QuickUI helper functions"""
    
    def test_alert_info(self):
        """Test info alert"""
        alert = QuickUI.alert("Info message", "info")
        assert alert.type == ComponentType.CONTAINER
        assert alert.style.background_color == "#e0f2fe"
    
    def test_alert_success(self):
        """Test success alert"""
        alert = QuickUI.alert("Success!", "success")
        assert alert.style.background_color == "#dcfce7"
    
    def test_alert_error(self):
        """Test error alert"""
        alert = QuickUI.alert("Error!", "error")
        assert alert.style.background_color == "#fee2e2"
    
    def test_confirmation_dialog(self):
        """Test confirmation dialog"""
        dialog = QuickUI.confirmation_dialog(
            "Confirm",
            "Are you sure?",
            "confirm_handler",
            "cancel_handler"
        )
        assert dialog.type == ComponentType.MODAL
        assert dialog.props["title"] == "Confirm"
    
    def test_metric_card(self):
        """Test metric card"""
        card = QuickUI.metric_card("Revenue", "$10K", "+5%", True)
        assert card.type == ComponentType.CARD
        assert card.props["title"] == "Revenue"
    
    def test_search_bar(self):
        """Test search bar"""
        search = QuickUI.search_bar("Search...", "search_handler")
        assert search.type == ComponentType.CONTAINER
        assert search.style.display == "flex"


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
class TestIntegration:
    """Integration tests"""
    
    async def test_full_component_tree(self):
        """Test building a full component tree"""
        # Build a complex UI
        root = container(padding="24px").add_child(
            header("Dashboard", "Welcome back")
        ).add_child(
            grid(2, "16px").add_child(
                card("Metrics").add_child(
                    tool.text("Content here")
                )
            ).add_child(
                card("Chart").add_child(
                    chart(ChartType.LINE, {
                        "labels": ["A", "B"],
                        "datasets": [{"data": [1, 2]}]
                    })
                )
            )
        ).add_child(
            hstack(
                button("Save", "save_handler"),
                button("Cancel", "cancel_handler", "secondary"),
                gap="8px"
            )
        )
        
        # Verify structure
        assert root.type == ComponentType.CONTAINER
        assert len(root.children) == 3
        assert root.children[0].type == ComponentType.HEADER
        assert root.children[1].type == ComponentType.GRID
        assert root.children[2].type == ComponentType.CONTAINER
    
    async def test_canvas_state_with_events(self):
        """Test canvas state with event handlers"""
        state = CanvasState("test")
        
        # Create component with events
        btn = button("Click Me", "click_handler")
        state.set_root(btn)
        
        # Register handler
        events_received = []
        def handler(data):
            events_received.append(data)
            return {"ack": True}
        
        state.register_handler("click_handler", handler)
        
        # Simulate event
        result = state.handle_event("click_handler", {"type": "click"})
        
        assert len(events_received) == 1
        assert result == {"ack": True}


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
