"""
Cell 0 OS - GUI Module
Canvas and A2UI System
"""
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

from gui.canvas_server import (
    CanvasServer,
    CanvasService,
    CanvasConnection
)

__all__ = [
    # Components
    "Component",
    "ComponentType", 
    "ComponentStyle",
    "ComponentEvent",
    "CanvasState",
    "A2UIMessage",
    "ChartType",
    # Component factories
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
    "center",
    # Chart helpers
    "line_chart_data",
    "bar_chart_data",
    "pie_chart_data",
    "dataset",
    # Server
    "CanvasServer",
    "CanvasService",
    "CanvasConnection"
]

__version__ = "1.0.0"
