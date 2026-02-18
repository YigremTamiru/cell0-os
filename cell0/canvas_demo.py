#!/usr/bin/env python3
"""
Cell 0 Canvas Demo
Demonstrates the A2UI system capabilities
"""
import asyncio
import logging
import sys
sys.path.insert(0, '/Users/yigremgetachewtamiru/.openclaw/workspace/cell0')

from gui.canvas_server import CanvasService
from engine.tools.canvas import CanvasTool, QuickUI
from gui.canvas_components import ComponentEvent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("cell0.demo")


async def demo_basic_ui():
    """Demo: Basic UI components"""
    print("\n🎨 Creating basic UI demo...")
    
    canvas = CanvasTool(canvas_id="demo_basic")
    await canvas.connect()
    
    ui = canvas.vstack(
        canvas.header("Basic Components Demo", "Testing all component types"),
        canvas.card("Text & Images",
            canvas.text("This is a text component"),
            canvas.image("https://via.placeholder.com/300x150", "Placeholder")
        ),
        canvas.card("Form Elements",
            canvas.input("username", "Enter username", on_input="on_username"),
            canvas.textarea("bio", "Tell us about yourself", rows=3),
            canvas.checkbox("newsletter", "Subscribe to newsletter", True),
            canvas.select("country", [
                {"value": "us", "label": "United States"},
                {"value": "uk", "label": "United Kingdom"},
                {"value": "jp", "label": "Japan"}
            ])
        ),
        canvas.card("Buttons",
            canvas.hstack(
                canvas.button("Primary", "btn_primary", "primary"),
                canvas.button("Secondary", "btn_secondary", "secondary"),
                canvas.button("Danger", "btn_danger", "error"),
                gap="8px"
            )
        ),
        gap="16px",
        padding="24px"
    )
    
    await canvas.render(ui)
    print(f"✅ Basic UI rendered at: {canvas.get_url()}")
    
    # Register handlers
    canvas.on("btn_primary", lambda d: logger.info("Primary button clicked!"))
    canvas.on("btn_secondary", lambda d: logger.info("Secondary button clicked!"))
    canvas.on("on_username", lambda d: logger.info(f"Username: {d.get('value')}"))
    
    return canvas


async def demo_layouts():
    """Demo: Layout components"""
    print("\n📐 Creating layout demo...")
    
    canvas = CanvasTool(canvas_id="demo_layouts")
    await canvas.connect()
    
    # Grid layout
    grid = canvas.grid(3, "16px",
        canvas.card("Card 1", canvas.text("Grid item 1")),
        canvas.card("Card 2", canvas.text("Grid item 2")),
        canvas.card("Card 3", canvas.text("Grid item 3")),
        canvas.card("Card 4", canvas.text("Grid item 4")),
        canvas.card("Card 5", canvas.text("Grid item 5")),
        canvas.card("Card 6", canvas.text("Grid item 6"))
    )
    
    # HStack and VStack
    stacks = canvas.vstack(
        canvas.text("Horizontal Stack:"),
        canvas.hstack(
            canvas.badge("Item 1", "primary"),
            canvas.badge("Item 2", "secondary"),
            canvas.badge("Item 3", "success"),
            gap="8px"
        ),
        canvas.text("Vertical Stack:"),
        canvas.vstack(
            canvas.text("Line 1"),
            canvas.text("Line 2"),
            canvas.text("Line 3"),
            gap="4px"
        ),
        gap="16px"
    )
    
    ui = canvas.vstack(
        canvas.header("Layout Demo", "Grid, HStack, VStack examples"),
        grid,
        canvas.divider(),
        stacks,
        gap="24px",
        padding="24px"
    )
    
    await canvas.render(ui)
    print(f"✅ Layout demo rendered at: {canvas.get_url()}")
    
    return canvas


async def demo_charts():
    """Demo: Chart components"""
    print("\n📊 Creating charts demo...")
    
    canvas = CanvasTool(canvas_id="demo_charts")
    await canvas.connect()
    
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    
    line_chart = canvas.line_chart(
        labels=months,
        datasets=[
            canvas.dataset("Revenue", [12000, 19000, 15000, 25000, 22000, 30000], "#6366f1"),
            canvas.dataset("Expenses", [8000, 12000, 10000, 14000, 13000, 16000], "#ef4444")
        ],
        options={"responsive": True}
    )
    
    bar_chart = canvas.bar_chart(
        labels=months,
        datasets=[
            canvas.dataset("Sales", [65, 59, 80, 81, 56, 95], "#22c55e")
        ]
    )
    
    pie_chart = canvas.pie_chart(
        labels=["Desktop", "Mobile", "Tablet"],
        data=[60, 30, 10],
        colors=["#6366f1", "#22c55e", "#f59e0b"]
    )
    
    ui = canvas.vstack(
        canvas.header("Charts Demo", "Data visualization with Chart.js"),
        canvas.grid(2, "24px",
            canvas.card("Revenue vs Expenses", line_chart),
            canvas.card("Sales by Month", bar_chart),
            canvas.card("Traffic Sources", pie_chart),
            canvas.card("Metrics", 
                canvas.vstack(
                    QuickUI.metric_card("Total Revenue", "$127K", "+15%", True),
                    QuickUI.metric_card("Active Users", "8,420", "+8%", True),
                    QuickUI.metric_card("Conversion", "3.2%", "-0.5%", False),
                    gap="16px"
                )
            )
        ),
        gap="24px",
        padding="24px"
    )
    
    await canvas.render(ui)
    print(f"✅ Charts demo rendered at: {canvas.get_url()}")
    
    return canvas


async def demo_interactive():
    """Demo: Interactive UI with state"""
    print("\n🎮 Creating interactive demo...")
    
    canvas = CanvasTool(canvas_id="demo_interactive")
    await canvas.connect()
    
    counter = canvas.card("Counter Example",
        canvas.hstack(
            canvas.button("-", "decrement", "secondary"),
            canvas.text("0", font_size="24px", font_weight="bold"),
            canvas.button("+", "increment", "primary"),
            gap="16px",
            align="center"
        )
    )
    
    todo_list = canvas.card("Todo List",
        canvas.vstack(
            canvas.hstack(
                canvas.input("new_todo", "Add new task..."),
                canvas.button("Add", "add_todo", "primary"),
                gap="8px"
            ),
            canvas.vstack(
                canvas.checkbox("todo_1", "Learn Canvas API", False),
                canvas.checkbox("todo_2", "Build awesome UI", True),
                canvas.checkbox("todo_3", "Deploy to production", False),
                gap="8px"
            ),
            gap="16px"
        )
    )
    
    progress_demo = canvas.card("Progress Demo",
        canvas.vstack(
            canvas.progress(0, 100, True),
            canvas.hstack(
                canvas.button("Start", "start_progress", "primary"),
                canvas.button("Reset", "reset_progress", "secondary"),
                gap="8px"
            ),
            gap="16px"
        )
    )
    
    ui = canvas.vstack(
        canvas.header("Interactive Demo", "State management and event handling"),
        counter,
        todo_list,
        progress_demo,
        gap="24px",
        padding="24px"
    )
    
    await canvas.render(ui)
    print(f"✅ Interactive demo rendered at: {canvas.get_url()}")
    
    # State management
    count = 0
    progress = 0
    
    def increment(data):
        nonlocal count
        count += 1
        asyncio.create_task(canvas.update(counter.children[0].children[1].id, content=str(count)))
        return {"count": count}
    
    def decrement(data):
        nonlocal count
        count -= 1
        asyncio.create_task(canvas.update(counter.children[0].children[1].id, content=str(count)))
        return {"count": count}
    
    async def start_progress(data):
        nonlocal progress
        for i in range(101):
            progress = i
            await canvas.update(progress_demo.children[0].children[0].id, value=progress)
            await asyncio.sleep(0.05)
    
    def reset_progress(data):
        nonlocal progress
        progress = 0
        asyncio.create_task(canvas.update(progress_demo.children[0].children[0].id, value=progress))
    
    canvas.on("increment", increment)
    canvas.on("decrement", decrement)
    canvas.on("start_progress", lambda d: asyncio.create_task(start_progress(d)))
    canvas.on("reset_progress", reset_progress)
    canvas.on("add_todo", lambda d: logger.info(f"Adding todo: {d}"))
    
    return canvas


async def demo_quick_ui():
    """Demo: QuickUI helpers"""
    print("\n⚡ Creating QuickUI demo...")
    
    canvas = CanvasTool(canvas_id="demo_quick_ui")
    await canvas.connect()
    
    ui = canvas.vstack(
        canvas.header("QuickUI Demo", "Pre-built UI patterns"),
        
        canvas.card("Alerts",
            QuickUI.alert("This is an info message", "info"),
            QuickUI.alert("Operation successful!", "success"),
            QuickUI.alert("Please review your input", "warning"),
            QuickUI.alert("An error occurred", "error"),
            gap="8px"
        ),
        
        canvas.card("Search",
            QuickUI.search_bar("Search products...", "search_handler")
        ),
        
        canvas.card("Data Table",
            QuickUI.data_table(
                headers=["Name", "Role", "Status"],
                rows=[
                    ["Alice", "Admin", "Active"],
                    ["Bob", "User", "Active"],
                    ["Carol", "User", "Inactive"]
                ]
            )
        ),
        
        canvas.card("Tabs",
            QuickUI.tabs([
                {"id": "tab1", "label": "Overview"},
                {"id": "tab2", "label": "Details"},
                {"id": "tab3", "label": "Settings"}
            ], "tab1", "tab_change")
        ),
        
        gap="24px",
        padding="24px"
    )
    
    await canvas.render(ui)
    print(f"✅ QuickUI demo rendered at: {canvas.get_url()}")
    
    canvas.on("search_handler", lambda d: logger.info(f"Search: {d}"))
    canvas.on("tab_change", lambda d: logger.info(f"Tab changed: {d}"))
    
    return canvas


async def demo_dashboard():
    """Demo: Full dashboard example"""
    print("\n📈 Creating dashboard demo...")
    
    canvas = CanvasTool(canvas_id="demo_dashboard")
    await canvas.connect()
    
    # Navigation
    nav = canvas.navbar([
        {"label": "Dashboard", "href": "#"},
        {"label": "Analytics", "href": "#"},
        {"label": "Reports", "href": "#"},
        {"label": "Settings", "href": "#"}
    ], "Cell 0 Dashboard", "navigate")
    
    # KPI Cards
    kpis = canvas.grid(4, "16px",
        QuickUI.metric_card("Total Users", "12,345", "+12%", True),
        QuickUI.metric_card("Revenue", "$45.2K", "+8%", True),
        QuickUI.metric_card("Active Sessions", "1,234", "+23%", True),
        QuickUI.metric_card("Bounce Rate", "42%", "-5%", True)
    )
    
    # Main chart
    main_chart = canvas.line_chart(
        labels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        datasets=[
            canvas.dataset("This Week", [120, 190, 300, 500, 200, 300, 450], "#6366f1"),
            canvas.dataset("Last Week", [100, 150, 250, 400, 180, 280, 350], "#94a3b8")
        ],
        options={
            "responsive": True,
            "plugins": {"title": {"display": True, "text": "Traffic Overview"}}
        }
    )
    
    # Recent activity
    activity = canvas.card("Recent Activity",
        canvas.vstack(
            canvas.hstack(
                canvas.badge("New", "success"),
                canvas.text("User registration: alice@example.com"),
                canvas.text("2 min ago", color="#94a3b8"),
                justify_content="space-between"
            ),
            canvas.divider(),
            canvas.hstack(
                canvas.badge("Sale", "primary"),
                canvas.text("New order #1234 - $299"),
                canvas.text("15 min ago", color="#94a3b8"),
                justify_content="space-between"
            ),
            canvas.divider(),
            canvas.hstack(
                canvas.badge("Alert", "warning"),
                canvas.text("High server load detected"),
                canvas.text("1 hour ago", color="#94a3b8"),
                justify_content="space-between"
            ),
            gap="12px"
        )
    )
    
    ui = canvas.vstack(
        nav,
        canvas.vstack(
            canvas.header("Dashboard", "Real-time system overview"),
            kpis,
            canvas.grid(3, "24px",
                canvas.card("Traffic", main_chart),
                activity,
                canvas.card("Quick Actions",
                    canvas.vstack(
                        canvas.button("Generate Report", "generate_report", "primary"),
                        canvas.button("Export Data", "export_data", "secondary"),
                        canvas.button("System Settings", "settings", "secondary"),
                        gap="8px"
                    )
                )
            ),
            gap="24px",
            padding="24px"
        ),
        gap="0"
    )
    
    await canvas.render(ui)
    print(f"✅ Dashboard demo rendered at: {canvas.get_url()}")
    
    return canvas


async def main():
    """Run all demos"""
    print("🚀 Cell 0 Canvas Demo")
    print("=" * 50)
    
    # Start the Canvas service
    service = CanvasService(host="0.0.0.0", ws_port=18802, http_port=18802)
    await service.start()
    
    print(f"\n🌐 Canvas server started!")
    print(f"   WebSocket: ws://localhost:18802/canvas/{{id}}")
    print(f"   HTTP: http://localhost:18802/canvas/{{id}}")
    
    # Create demo canvases
    demos = []
    
    try:
        demos.append(await demo_basic_ui())
        demos.append(await demo_layouts())
        demos.append(await demo_charts())
        demos.append(await demo_interactive())
        demos.append(await demo_quick_ui())
        demos.append(await demo_dashboard())
        
        print("\n" + "=" * 50)
        print("✅ All demos created successfully!")
        print("\nOpen the following URLs in your browser:")
        for demo in demos:
            print(f"  📱 {demo.canvas_id}: {demo.get_url()}")
        
        print("\nPress Ctrl+C to stop the server...")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
    finally:
        for demo in demos:
            await demo.disconnect()
        await service.stop()
        print("✅ Server stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
