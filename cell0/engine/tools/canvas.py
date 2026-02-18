"""
Canvas Tool for Cell 0 OS Agents
Provides high-level interface for rendering UI via A2UI protocol
"""
import asyncio
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime
import logging

from gui.canvas_components import (
    Component, ComponentType, CanvasState, A2UIMessage,
    ComponentStyle, ComponentEvent,
    text, image, button, input_field, textarea, select,
    checkbox, radio, form, chart, container, grid, card,
    modal, progress, badge, divider, header, footer, navbar,
    hstack, vstack, center,
    line_chart_data, bar_chart_data, pie_chart_data, dataset,
    ChartType
)
from gui.canvas_server import CanvasService, CanvasServer

logger = logging.getLogger("cell0.tools.canvas")


class CanvasTool:
    """
    High-level tool for agents to create and manage Canvas UIs
    
    Usage:
        canvas = CanvasTool()
        await canvas.connect()
        
        # Create a simple UI
        await canvas.render(
            canvas.card("My Card",
                canvas.text("Hello World"),
                canvas.button("Click Me", on_click="handle_click")
            )
        )
    """
    
    def __init__(self, canvas_id: Optional[str] = None, 
                 server: Optional[CanvasServer] = None,
                 auto_connect: bool = True):
        self.canvas_id = canvas_id or f"agent_canvas_{datetime.utcnow().timestamp()}"
        self.server = server
        self._service: Optional[CanvasService] = None
        self._session: Optional[CanvasState] = None
        self._handlers: Dict[str, Callable] = {}
        self._connected = False
        
        if auto_connect:
            asyncio.create_task(self.connect())
    
    async def connect(self) -> bool:
        """Connect to the Canvas server"""
        try:
            if self.server:
                # Use existing server
                self._session = self.server.create_canvas(self.canvas_id)
                self._connected = True
            else:
                # Start our own service
                self._service = CanvasService(
                    host="0.0.0.0",
                    ws_port=18802,
                    http_port=18802
                )
                await self._service.start()
                self._session = self._service.create_canvas(self.canvas_id)
                self._connected = True
                
                # Register pending handlers
                for handler_id, callback in self._handlers.items():
                    self._service.register_handler(handler_id, callback)
            
            logger.info(f"Canvas connected: {self.canvas_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to canvas: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the Canvas server"""
        if self._service:
            await self._service.stop()
            self._service = None
        self._connected = False
        logger.info(f"Canvas disconnected: {self.canvas_id}")
    
    # =================================================================
    # Rendering Methods
    # =================================================================
    
    async def render(self, component: Component) -> bool:
        """Render a component to the canvas"""
        if not self._connected:
            logger.warning("Canvas not connected, attempting to connect...")
            await self.connect()
        
        if self.server:
            return await self.server.render(self.canvas_id, component)
        elif self._service:
            return await self._service.render(self.canvas_id, component)
        
        return False
    
    async def update(self, component_id: str, **props) -> bool:
        """Update a specific component"""
        if self.server:
            return await self.server.update_component(self.canvas_id, component_id, **props)
        elif self._service:
            return await self._service.update_component(self.canvas_id, component_id, **props)
        return False
    
    async def clear(self):
        """Clear the canvas"""
        empty = container()
        await self.render(empty)
    
    # =================================================================
    # Component Builder Methods
    # =================================================================
    
    def text(self, content: str, **style) -> Component:
        """Create text component"""
        return text(content, **style)
    
    def image(self, src: str, alt: str = "", **style) -> Component:
        """Create image component"""
        return image(src, alt, **style)
    
    def button(self, label: str, on_click: Optional[str] = None,
               variant: str = "primary", **style) -> Component:
        """Create button component"""
        btn = button(label, variant=variant, **style)
        if on_click:
            btn.add_event(ComponentEvent(type="click", handler=on_click))
        return btn
    
    def input(self, name: str, placeholder: str = "",
              input_type: str = "text", value: str = "",
              on_input: Optional[str] = None, **style) -> Component:
        """Create input field"""
        inp = input_field(name, placeholder, input_type, value, **style)
        if on_input:
            inp.add_event(ComponentEvent(type="input", handler=on_input))
        return inp
    
    def textarea(self, name: str, placeholder: str = "",
                 value: str = "", rows: int = 4,
                 on_input: Optional[str] = None, **style) -> Component:
        """Create textarea"""
        ta = textarea(name, placeholder, value, rows, **style)
        if on_input:
            ta.add_event(ComponentEvent(type="input", handler=on_input))
        return ta
    
    def select(self, name: str, options: List[Dict[str, str]],
               value: str = "", on_change: Optional[str] = None,
               **style) -> Component:
        """Create select dropdown"""
        sel = select(name, options, value, **style)
        if on_change:
            sel.add_event(ComponentEvent(type="change", handler=on_change))
        return sel
    
    def checkbox(self, name: str, label: str, checked: bool = False,
                 on_change: Optional[str] = None, **style) -> Component:
        """Create checkbox"""
        cb = checkbox(name, label, checked, **style)
        if on_change:
            cb.add_event(ComponentEvent(type="change", handler=on_change))
        return cb
    
    def radio(self, name: str, options: List[Dict[str, str]],
              value: str = "", on_change: Optional[str] = None,
              **style) -> Component:
        """Create radio button group"""
        r = radio(name, options, value, **style)
        if on_change:
            r.add_event(ComponentEvent(type="change", handler=on_change))
        return r
    
    def form(self, name: str, on_submit: str, **style) -> Component:
        """Create form container"""
        return form(name, on_submit, **style)
    
    def container(self, *children: Component, **style) -> Component:
        """Create container with children"""
        cont = container(**style)
        for child in children:
            cont.add_child(child)
        return cont
    
    def card(self, title: Optional[str] = None, *children: Component, **style) -> Component:
        """Create card with children"""
        c = card(title, **style)
        for child in children:
            c.add_child(child)
        return c
    
    def grid(self, columns: int = 2, gap: str = "16px", 
             *children: Component, **style) -> Component:
        """Create grid layout"""
        g = grid(columns, gap, **style)
        for child in children:
            g.add_child(child)
        return g
    
    def modal(self, title: str, is_open: bool = False,
              on_close: Optional[str] = None, *children: Component, **style) -> Component:
        """Create modal with children"""
        m = modal(title, is_open, on_close, **style)
        for child in children:
            m.add_child(child)
        return m
    
    def progress(self, value: float, max_value: float = 100.0,
                 show_label: bool = True, **style) -> Component:
        """Create progress bar"""
        return progress(value, max_value, show_label, **style)
    
    def badge(self, content: str, variant: str = "default", **style) -> Component:
        """Create badge"""
        return badge(content, variant, **style)
    
    def divider(self, **style) -> Component:
        """Create divider"""
        return divider(**style)
    
    def header(self, title: str, subtitle: Optional[str] = None, **style) -> Component:
        """Create header"""
        return header(title, subtitle, **style)
    
    def footer(self, content: str, **style) -> Component:
        """Create footer"""
        return footer(content, **style)
    
    def navbar(self, items: List[Dict[str, Any]], 
               brand: Optional[str] = None,
               on_navigate: Optional[str] = None, **style) -> Component:
        """Create navigation bar"""
        return navbar(items, brand, on_navigate, **style)
    
    def hstack(self, *children: Component, gap: str = "16px",
               align: str = "center", **style) -> Component:
        """Create horizontal stack"""
        return hstack(*children, gap=gap, align=align, **style)
    
    def vstack(self, *children: Component, gap: str = "16px",
               align: str = "stretch", **style) -> Component:
        """Create vertical stack"""
        return vstack(*children, gap=gap, align=align, **style)
    
    def center(self, child: Component, **style) -> Component:
        """Center a component"""
        return center(child, **style)
    
    # =================================================================
    # Chart Components
    # =================================================================
    
    def line_chart(self, labels: List[str], datasets: List[Dict],
                   options: Optional[Dict] = None, **style) -> Component:
        """Create line chart"""
        data = line_chart_data(labels, datasets)
        return chart(ChartType.LINE, data, options, **style)
    
    def bar_chart(self, labels: List[str], datasets: List[Dict],
                  options: Optional[Dict] = None, **style) -> Component:
        """Create bar chart"""
        data = bar_chart_data(labels, datasets)
        return chart(ChartType.BAR, data, options, **style)
    
    def pie_chart(self, labels: List[str], data: List[float],
                  colors: Optional[List[str]] = None,
                  options: Optional[Dict] = None, **style) -> Component:
        """Create pie chart"""
        chart_data = pie_chart_data(labels, data, colors)
        return chart(ChartType.PIE, chart_data, options, **style)
    
    def dataset(self, label: str, data: List[float], 
                color: Optional[str] = None) -> Dict:
        """Create chart dataset"""
        return dataset(label, data, color)
    
    # =================================================================
    # Event Handling
    # =================================================================
    
    def on(self, handler_id: str, callback: Callable):
        """Register an event handler"""
        self._handlers[handler_id] = callback
        
        if self._connected:
            if self.server:
                self.server.register_handler(handler_id, callback)
            elif self._service:
                self._service.register_handler(handler_id, callback)
        
        return self
    
    def off(self, handler_id: str):
        """Unregister an event handler"""
        if handler_id in self._handlers:
            del self._handlers[handler_id]
        return self
    
    # =================================================================
    # Data Management
    # =================================================================
    
    def set_data(self, key: str, value: Any):
        """Store data in canvas state"""
        if self._session:
            self._session.set_data(key, value)
        return self
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get data from canvas state"""
        if self._session:
            return self._session.get_data(key, default)
        return default
    
    # =================================================================
    # Screenshots
    # =================================================================
    
    async def screenshot(self, format: str = "png", 
                         quality: float = 0.9) -> Optional[str]:
        """Request a screenshot from the canvas"""
        if self.server:
            return await self.server.request_screenshot(
                self.canvas_id, format=format, quality=quality
            )
        elif self._service:
            return await self._service.request_screenshot(
                self.canvas_id, format=format, quality=quality
            )
        return None
    
    # =================================================================
    # Utility Methods
    # =================================================================
    
    def get_url(self) -> str:
        """Get the canvas URL"""
        return f"http://localhost:18802/canvas/{self.canvas_id}"
    
    def get_ws_url(self) -> str:
        """Get the WebSocket URL"""
        return f"ws://localhost:18802/canvas/{self.canvas_id}"
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to canvas"""
        return self._connected
    
    def get_stats(self) -> Dict[str, Any]:
        """Get canvas statistics"""
        if self._service:
            return self._service.get_stats()
        elif self.server:
            return self.server.get_stats()
        return {}


# =============================================================================
# Quick UI Builders
# =============================================================================

class QuickUI:
    """Quick UI builders for common patterns"""
    
    @staticmethod
    def alert(message: str, type: str = "info") -> Component:
        """Create an alert/notification"""
        colors = {
            "info": "#e0f2fe",
            "success": "#dcfce7",
            "warning": "#fef3c7",
            "error": "#fee2e2"
        }
        text_colors = {
            "info": "#075985",
            "success": "#166534",
            "warning": "#92400e",
            "error": "#991b1b"
        }
        
        return container(
            background_color=colors.get(type, colors["info"]),
            color=text_colors.get(type, text_colors["info"]),
            padding="12px 16px",
            border_radius="8px",
            margin="8px 0"
        ).add_child(text(message))
    
    @staticmethod
    def confirmation_dialog(title: str, message: str,
                           confirm_handler: str, 
                           cancel_handler: Optional[str] = None) -> Component:
        """Create a confirmation dialog"""
        return modal(title, True, cancel_handler or "close_modal",
            text(message),
            hstack(
                button("Cancel", cancel_handler or "close_modal", "secondary"),
                button("Confirm", confirm_handler, "primary"),
                gap="8px",
                justify_content="flex-end"
            )
        )
    
    @staticmethod
    def data_table(headers: List[str], rows: List[List[str]], **style) -> Component:
        """Create a data table"""
        # This is a simplified table - full implementation would be more complex
        table = container(**style)
        
        # Header row
        header_row = container(
            display="flex",
            border_bottom="2px solid #e0e0e0",
            font_weight="600"
        )
        for header in headers:
            header_row.add_child(
                container(
                    flex="1",
                    padding="12px"
                ).add_child(text(header))
            )
        table.add_child(header_row)
        
        # Data rows
        for row in rows:
            row_container = container(
                display="flex",
                border_bottom="1px solid #e0e0e0"
            )
            for cell in row:
                row_container.add_child(
                    container(
                        flex="1",
                        padding="12px"
                    ).add_child(text(cell))
                )
            table.add_child(row_container)
        
        return table
    
    @staticmethod
    def metric_card(title: str, value: str, 
                    change: Optional[str] = None,
                    change_positive: bool = True) -> Component:
        """Create a metric/KPI card"""
        c = card(title,
            text(value, font_size="32px", font_weight="700", margin="8px 0")
        )
        
        if change:
            change_color = "#22c55e" if change_positive else "#ef4444"
            c.add_child(
                text(change, color=change_color, font_size="14px")
            )
        
        return c
    
    @staticmethod
    def search_bar(placeholder: str = "Search...",
                   on_search: Optional[str] = None) -> Component:
        """Create a search bar"""
        return hstack(
            input_field("search", placeholder, "search"),
            button("Search", on_search, "primary"),
            gap="8px"
        )
    
    @staticmethod
    def tabs(tabs: List[Dict[str, Any]], 
             active_tab: str,
             on_change: Optional[str] = None) -> Component:
        """Create tabs"""
        container_el = container(
            border_bottom="1px solid #e0e0e0",
            display="flex",
            gap="4px"
        )
        
        for tab in tabs:
            is_active = tab["id"] == active_tab
            tab_el = button(
                tab["label"],
                f"{on_change}:{tab['id']}" if on_change else None,
                "secondary" if not is_active else "primary"
            )
            tab_el.set_style(
                border_bottom="2px solid " + ("#6366f1" if is_active else "transparent"),
                border_radius="0",
                background_color="transparent" if not is_active else "#f5f5f5"
            )
            container_el.add_child(tab_el)
        
        return container_el


# =============================================================================
# Decorator for Event Handlers
# =============================================================================

def canvas_handler(canvas_tool: CanvasTool):
    """Decorator to register canvas event handlers"""
    def decorator(handler_id: str):
        def wrapper(func: Callable):
            canvas_tool.on(handler_id, func)
            return func
        return wrapper
    return decorator


# =============================================================================
# Export common components
# =============================================================================

__all__ = [
    "CanvasTool",
    "QuickUI",
    "canvas_handler",
    "Component",
    "ComponentType",
    "ComponentStyle",
    "ComponentEvent",
    "ChartType",
    "text",
    "image", 
    "button",
    "input_field",
    "textarea",
    "select",
    "checkbox",
    "radio",
    "form",
    "chart",
    "container",
    "grid",
    "card",
    "modal",
    "progress",
    "badge",
    "divider",
    "header",
    "footer",
    "navbar",
    "hstack",
    "vstack",
    "center"
]
