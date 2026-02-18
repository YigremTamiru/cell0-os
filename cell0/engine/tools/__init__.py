"""
Cell 0 OS - Engine Tools
Agent tool integrations
"""
from engine.tools.canvas import (
    CanvasTool,
    QuickUI,
    canvas_handler
)

from engine.tools.web_search_enhanced import (
    EnhancedWebSearch,
    SearchRequest,
    SearchResponse,
    SearchType,
    web_search,
    news_search,
    image_search,
    academic_search,
)

__all__ = [
    # Canvas
    "CanvasTool",
    "QuickUI",
    "canvas_handler",
    # Web Search Enhanced
    "EnhancedWebSearch",
    "SearchRequest",
    "SearchResponse",
    "SearchType",
    "web_search",
    "news_search",
    "image_search",
    "academic_search",
]
