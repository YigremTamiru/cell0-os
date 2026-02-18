"""
Canvas Component Library for Cell 0 OS
Provides UI components for the A2UI (Agent-to-UI) protocol
"""
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import uuid
from datetime import datetime


class ComponentType(Enum):
    """Supported UI component types"""
    TEXT = "text"
    IMAGE = "image"
    BUTTON = "button"
    INPUT = "input"
    TEXTAREA = "textarea"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    FORM = "form"
    CHART = "chart"
    CONTAINER = "container"
    GRID = "grid"
    CARD = "card"
    MODAL = "modal"
    PROGRESS = "progress"
    BADGE = "badge"
    DIVIDER = "divider"
    HEADER = "header"
    FOOTER = "footer"
    NAVBAR = "navbar"


class ChartType(Enum):
    """Supported chart types"""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    DOUGHNUT = "doughnut"
    RADAR = "radar"
    POLAR = "polar"
    SCATTER = "scatter"
    BUBBLE = "bubble"


@dataclass
class ComponentStyle:
    """CSS styling for components"""
    # Layout
    width: Optional[str] = None
    height: Optional[str] = None
    padding: Optional[str] = None
    margin: Optional[str] = None
    display: Optional[str] = None
    position: Optional[str] = None
    top: Optional[str] = None
    left: Optional[str] = None
    right: Optional[str] = None
    bottom: Optional[str] = None
    z_index: Optional[int] = None
    
    # Flexbox/Grid
    flex_direction: Optional[str] = None
    justify_content: Optional[str] = None
    align_items: Optional[str] = None
    flex_wrap: Optional[str] = None
    gap: Optional[str] = None
    grid_template: Optional[str] = None
    
    # Appearance
    background_color: Optional[str] = None
    color: Optional[str] = None
    border: Optional[str] = None
    border_radius: Optional[str] = None
    border_color: Optional[str] = None
    border_width: Optional[str] = None
    box_shadow: Optional[str] = None
    opacity: Optional[float] = None
    
    # Typography
    font_size: Optional[str] = None
    font_weight: Optional[str] = None
    font_family: Optional[str] = None
    text_align: Optional[str] = None
    line_height: Optional[str] = None
    letter_spacing: Optional[str] = None
    
    # Effects
    transform: Optional[str] = None
    transition: Optional[str] = None
    animation: Optional[str] = None
    cursor: Optional[str] = None
    
    # Responsive
    media_queries: Optional[Dict[str, Dict[str, str]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                # Convert snake_case to camelCase for JS
                js_key = ''.join(word.capitalize() if i > 0 else word 
                               for i, word in enumerate(key.split('_')))
                result[js_key] = value
        return result


@dataclass
class ComponentEvent:
    """Event configuration for components"""
    type: str  # click, input, submit, change, focus, blur, etc.
    handler: str  # Handler identifier
    debounce: Optional[int] = None  # Debounce time in ms
    throttle: Optional[int] = None  # Throttle time in ms
    prevent_default: bool = False
    stop_propagation: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "handler": self.handler,
            "debounce": self.debounce,
            "throttle": self.throttle,
            "preventDefault": self.prevent_default,
            "stopPropagation": self.stop_propagation
        }


@dataclass
class Component:
    """Base component class"""
    type: ComponentType
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    props: Dict[str, Any] = field(default_factory=dict)
    style: ComponentStyle = field(default_factory=ComponentStyle)
    events: List[ComponentEvent] = field(default_factory=list)
    children: List['Component'] = field(default_factory=list)
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert component to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "props": self.props,
            "style": self.style.to_dict(),
            "events": [e.to_dict() for e in self.events],
            "children": [c.to_dict() for c in self.children],
            "parentId": self.parent_id,
            "metadata": self.metadata,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at
        }
    
    def add_child(self, child: 'Component') -> 'Component':
        """Add a child component"""
        child.parent_id = self.id
        self.children.append(child)
        self.updated_at = datetime.utcnow().isoformat()
        return self
    
    def add_event(self, event: ComponentEvent) -> 'Component':
        """Add an event handler"""
        self.events.append(event)
        self.updated_at = datetime.utcnow().isoformat()
        return self
    
    def set_style(self, **kwargs) -> 'Component':
        """Set style properties"""
        for key, value in kwargs.items():
            if hasattr(self.style, key):
                setattr(self.style, key, value)
        self.updated_at = datetime.utcnow().isoformat()
        return self
    
    def set_prop(self, key: str, value: Any) -> 'Component':
        """Set a property"""
        self.props[key] = value
        self.updated_at = datetime.utcnow().isoformat()
        return self


# =============================================================================
# Component Factory Functions
# =============================================================================

def text(content: str, **style_kwargs) -> Component:
    """Create a text component"""
    return Component(
        type=ComponentType.TEXT,
        props={"content": content},
        style=ComponentStyle(**style_kwargs)
    )


def image(src: str, alt: str = "", **style_kwargs) -> Component:
    """Create an image component"""
    return Component(
        type=ComponentType.IMAGE,
        props={"src": src, "alt": alt},
        style=ComponentStyle(**style_kwargs)
    )


def button(label: str, handler: Optional[str] = None, 
           variant: str = "primary", **style_kwargs) -> Component:
    """Create a button component"""
    component = Component(
        type=ComponentType.BUTTON,
        props={"label": label, "variant": variant},
        style=ComponentStyle(**style_kwargs)
    )
    if handler:
        component.add_event(ComponentEvent(type="click", handler=handler))
    return component


def input_field(name: str, placeholder: str = "", 
                input_type: str = "text", value: str = "",
                handler: Optional[str] = None, **style_kwargs) -> Component:
    """Create an input field component"""
    component = Component(
        type=ComponentType.INPUT,
        props={
            "name": name,
            "placeholder": placeholder,
            "type": input_type,
            "value": value
        },
        style=ComponentStyle(**style_kwargs)
    )
    if handler:
        component.add_event(ComponentEvent(type="input", handler=handler))
    return component


def textarea(name: str, placeholder: str = "", 
             value: str = "", rows: int = 4,
             handler: Optional[str] = None, **style_kwargs) -> Component:
    """Create a textarea component"""
    component = Component(
        type=ComponentType.TEXTAREA,
        props={
            "name": name,
            "placeholder": placeholder,
            "value": value,
            "rows": rows
        },
        style=ComponentStyle(**style_kwargs)
    )
    if handler:
        component.add_event(ComponentEvent(type="input", handler=handler))
    return component


def select(name: str, options: List[Dict[str, str]], 
           value: str = "", handler: Optional[str] = None,
           **style_kwargs) -> Component:
    """Create a select dropdown component"""
    component = Component(
        type=ComponentType.SELECT,
        props={"name": name, "options": options, "value": value},
        style=ComponentStyle(**style_kwargs)
    )
    if handler:
        component.add_event(ComponentEvent(type="change", handler=handler))
    return component


def checkbox(name: str, label: str, checked: bool = False,
             handler: Optional[str] = None, **style_kwargs) -> Component:
    """Create a checkbox component"""
    component = Component(
        type=ComponentType.CHECKBOX,
        props={"name": name, "label": label, "checked": checked},
        style=ComponentStyle(**style_kwargs)
    )
    if handler:
        component.add_event(ComponentEvent(type="change", handler=handler))
    return component


def radio(name: str, options: List[Dict[str, str]], 
          value: str = "", handler: Optional[str] = None,
          **style_kwargs) -> Component:
    """Create a radio button group"""
    component = Component(
        type=ComponentType.RADIO,
        props={"name": name, "options": options, "value": value},
        style=ComponentStyle(**style_kwargs)
    )
    if handler:
        component.add_event(ComponentEvent(type="change", handler=handler))
    return component


def form(name: str, submit_handler: str, **style_kwargs) -> Component:
    """Create a form container"""
    component = Component(
        type=ComponentType.FORM,
        props={"name": name},
        style=ComponentStyle(**style_kwargs)
    )
    component.add_event(ComponentEvent(type="submit", handler=submit_handler))
    return component


def chart(chart_type: ChartType, data: Dict[str, Any], 
          options: Optional[Dict[str, Any]] = None, **style_kwargs) -> Component:
    """Create a chart component"""
    return Component(
        type=ComponentType.CHART,
        props={
            "chartType": chart_type.value,
            "data": data,
            "options": options or {}
        },
        style=ComponentStyle(**style_kwargs)
    )


def container(**style_kwargs) -> Component:
    """Create a container component"""
    return Component(
        type=ComponentType.CONTAINER,
        style=ComponentStyle(**style_kwargs)
    )


def grid(columns: int = 2, gap: str = "16px", **style_kwargs) -> Component:
    """Create a grid container"""
    style = ComponentStyle(
        display="grid",
        grid_template=f"repeat({columns}, 1fr)",
        gap=gap,
        **style_kwargs
    )
    return Component(
        type=ComponentType.GRID,
        style=style
    )


def card(title: Optional[str] = None, **style_kwargs) -> Component:
    """Create a card component"""
    return Component(
        type=ComponentType.CARD,
        props={"title": title},
        style=ComponentStyle(
            background_color="#ffffff",
            border_radius="8px",
            box_shadow="0 2px 8px rgba(0,0,0,0.1)",
            padding="16px",
            **style_kwargs
        )
    )


def modal(title: str, is_open: bool = False, 
          close_handler: Optional[str] = None, **style_kwargs) -> Component:
    """Create a modal component"""
    component = Component(
        type=ComponentType.MODAL,
        props={"title": title, "isOpen": is_open},
        style=ComponentStyle(
            position="fixed",
            top="0",
            left="0",
            right="0",
            bottom="0",
            background_color="rgba(0,0,0,0.5)",
            display="flex",
            justify_content="center",
            align_items="center",
            z_index=1000,
            **style_kwargs
        )
    )
    if close_handler:
        component.add_event(ComponentEvent(type="close", handler=close_handler))
    return component


def progress(value: float, max_value: float = 100.0, 
             show_label: bool = True, **style_kwargs) -> Component:
    """Create a progress bar"""
    return Component(
        type=ComponentType.PROGRESS,
        props={
            "value": value,
            "max": max_value,
            "showLabel": show_label
        },
        style=ComponentStyle(**style_kwargs)
    )


def badge(content: str, variant: str = "default", **style_kwargs) -> Component:
    """Create a badge component"""
    return Component(
        type=ComponentType.BADGE,
        props={"content": content, "variant": variant},
        style=ComponentStyle(**style_kwargs)
    )


def divider(**style_kwargs) -> Component:
    """Create a divider/horizontal rule"""
    return Component(
        type=ComponentType.DIVIDER,
        style=ComponentStyle(
            width="100%",
            height="1px",
            background_color="#e0e0e0",
            margin="16px 0",
            **style_kwargs
        )
    )


def header(title: str, subtitle: Optional[str] = None, **style_kwargs) -> Component:
    """Create a page header"""
    return Component(
        type=ComponentType.HEADER,
        props={"title": title, "subtitle": subtitle},
        style=ComponentStyle(
            padding="24px",
            border_bottom="1px solid #e0e0e0",
            **style_kwargs
        )
    )


def footer(content: str, **style_kwargs) -> Component:
    """Create a page footer"""
    return Component(
        type=ComponentType.FOOTER,
        props={"content": content},
        style=ComponentStyle(
            padding="16px",
            border_top="1px solid #e0e0e0",
            text_align="center",
            **style_kwargs
        )
    )


def navbar(items: List[Dict[str, Any]], brand: Optional[str] = None,
           handler: Optional[str] = None, **style_kwargs) -> Component:
    """Create a navigation bar"""
    component = Component(
        type=ComponentType.NAVBAR,
        props={"items": items, "brand": brand},
        style=ComponentStyle(
            display="flex",
            justify_content="space-between",
            align_items="center",
            padding="0 24px",
            height="64px",
            background_color="#ffffff",
            box_shadow="0 2px 4px rgba(0,0,0,0.1)",
            **style_kwargs
        )
    )
    if handler:
        component.add_event(ComponentEvent(type="navigate", handler=handler))
    return component


# =============================================================================
# Layout Builders
# =============================================================================

def hstack(*children: Component, gap: str = "16px", 
           align: str = "center", **style_kwargs) -> Component:
    """Create a horizontal stack layout"""
    component = Component(
        type=ComponentType.CONTAINER,
        style=ComponentStyle(
            display="flex",
            flex_direction="row",
            gap=gap,
            align_items=align,
            **style_kwargs
        )
    )
    for child in children:
        component.add_child(child)
    return component


def vstack(*children: Component, gap: str = "16px", 
           align: str = "stretch", **style_kwargs) -> Component:
    """Create a vertical stack layout"""
    component = Component(
        type=ComponentType.CONTAINER,
        style=ComponentStyle(
            display="flex",
            flex_direction="column",
            gap=gap,
            align_items=align,
            **style_kwargs
        )
    )
    for child in children:
        component.add_child(child)
    return component


def center(child: Component, **style_kwargs) -> Component:
    """Center a component"""
    component = Component(
        type=ComponentType.CONTAINER,
        style=ComponentStyle(
            display="flex",
            justify_content="center",
            align_items="center",
            width="100%",
            height="100%",
            **style_kwargs
        )
    )
    component.add_child(child)
    return component


# =============================================================================
# Chart Data Helpers
# =============================================================================

def line_chart_data(labels: List[str], datasets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create data for line chart"""
    return {"labels": labels, "datasets": datasets}


def bar_chart_data(labels: List[str], datasets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create data for bar chart"""
    return {"labels": labels, "datasets": datasets}


def pie_chart_data(labels: List[str], data: List[float], 
                   colors: Optional[List[str]] = None) -> Dict[str, Any]:
    """Create data for pie chart"""
    return {
        "labels": labels,
        "datasets": [{
            "data": data,
            "backgroundColor": colors or [
                "#FF6384", "#36A2EB", "#FFCE56", 
                "#4BC0C0", "#9966FF", "#FF9F40"
            ]
        }]
    }


def dataset(label: str, data: List[float], 
            color: Optional[str] = None) -> Dict[str, Any]:
    """Create a dataset for charts"""
    ds = {"label": label, "data": data}
    if color:
        ds["borderColor"] = color
        ds["backgroundColor"] = color + "40"  # Add transparency
    return ds


# =============================================================================
# Canvas State Manager
# =============================================================================

class CanvasState:
    """Manages the state of a canvas session"""
    
    def __init__(self, canvas_id: str):
        self.canvas_id = canvas_id
        self.root: Optional[Component] = None
        self.components: Dict[str, Component] = {}
        self.event_handlers: Dict[str, Callable] = {}
        self.data_store: Dict[str, Any] = {}
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()
    
    def set_root(self, component: Component) -> None:
        """Set the root component"""
        self.root = component
        self._index_components(component)
        self.updated_at = datetime.utcnow().isoformat()
    
    def _index_components(self, component: Component) -> None:
        """Index all components for quick lookup"""
        self.components[component.id] = component
        for child in component.children:
            self._index_components(child)
    
    def get_component(self, component_id: str) -> Optional[Component]:
        """Get a component by ID"""
        return self.components.get(component_id)
    
    def update_component(self, component_id: str, **props) -> bool:
        """Update component properties"""
        component = self.components.get(component_id)
        if component:
            for key, value in props.items():
                if key.startswith("style_"):
                    style_key = key[6:]
                    setattr(component.style, style_key, value)
                else:
                    component.props[key] = value
            component.updated_at = datetime.utcnow().isoformat()
            self.updated_at = datetime.utcnow().isoformat()
            return True
        return False
    
    def remove_component(self, component_id: str) -> bool:
        """Remove a component"""
        if component_id in self.components:
            del self.components[component_id]
            self.updated_at = datetime.utcnow().isoformat()
            return True
        return False
    
    def register_handler(self, handler_id: str, callback: Callable) -> None:
        """Register an event handler"""
        self.event_handlers[handler_id] = callback
    
    def handle_event(self, handler_id: str, event_data: Dict[str, Any]) -> Any:
        """Handle an event from the UI"""
        handler = self.event_handlers.get(handler_id)
        if handler:
            return handler(event_data)
        return None
    
    def set_data(self, key: str, value: Any) -> None:
        """Store data in the canvas state"""
        self.data_store[key] = value
        self.updated_at = datetime.utcnow().isoformat()
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get data from the canvas state"""
        return self.data_store.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert canvas state to dictionary"""
        return {
            "canvasId": self.canvas_id,
            "root": self.root.to_dict() if self.root else None,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "componentCount": len(self.components),
            "handlerCount": len(self.event_handlers)
        }


# =============================================================================
# A2UI Protocol Messages
# =============================================================================

class A2UIMessage:
    """A2UI Protocol message types"""
    
    @staticmethod
    def render(component: Component) -> Dict[str, Any]:
        """Create render message"""
        return {
            "type": "render",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": component.to_dict()
        }
    
    @staticmethod
    def update(component_id: str, **props) -> Dict[str, Any]:
        """Create update message"""
        return {
            "type": "update",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {"componentId": component_id, "props": props}
        }
    
    @staticmethod
    def event(handler_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create event message from UI"""
        return {
            "type": "event",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {"handlerId": handler_id, "data": event_data}
        }
    
    @staticmethod
    def state_update(data: Dict[str, Any]) -> Dict[str, Any]:
        """Create state update message"""
        return {
            "type": "state_update",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": data
        }
    
    @staticmethod
    def screenshot(data: str, format: str = "png") -> Dict[str, Any]:
        """Create screenshot response"""
        return {
            "type": "screenshot",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {"data": data, "format": format}
        }
    
    @staticmethod
    def error(message: str, code: Optional[str] = None) -> Dict[str, Any]:
        """Create error message"""
        return {
            "type": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {"message": message, "code": code}
        }
    
    @staticmethod
    def ping() -> Dict[str, Any]:
        """Create ping message"""
        return {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def pong() -> Dict[str, Any]:
        """Create pong message"""
        return {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        }
