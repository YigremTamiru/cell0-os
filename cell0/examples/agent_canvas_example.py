#!/usr/bin/env python3
"""
Cell 0 Canvas - Agent Usage Example
Shows how agents can use the Canvas tool to render UIs
"""
import asyncio
import sys
sys.path.insert(0, '/Users/yigremgetachewtamiru/.openclaw/workspace/cell0')

from engine.tools.canvas import CanvasTool, QuickUI


async def agent_example():
    """
    Example showing how an agent uses Canvas to:
    1. Render a status dashboard
    2. Update components in real-time
    3. Handle user interactions
    """
    
    # Create a canvas for this agent session
    canvas = CanvasTool(canvas_id="agent_session_001")
    await canvas.connect()
    
    print(f"🎨 Canvas ready at: {canvas.get_url()}")
    
    # =========================================================================
    # Step 1: Render initial status UI
    # =========================================================================
    
    status_badge = canvas.badge("Initializing...", "warning")
    progress_bar = canvas.progress(0, 100, True)
    log_output = canvas.text("Starting task execution...", font_family="monospace")
    
    await canvas.render(
        canvas.vstack(
            canvas.header("Agent Task Monitor", "Session: agent_session_001"),
            canvas.card("Status",
                canvas.vstack(
                    canvas.hstack(
                        canvas.text("Status: "),
                        status_badge,
                        gap="8px"
                    ),
                    progress_bar,
                    gap="16px"
                )
            ),
            canvas.card("Activity Log",
                log_output
            ),
            canvas.card("Controls",
                canvas.hstack(
                    canvas.button("Pause", "pause_task", "secondary"),
                    canvas.button("Cancel", "cancel_task", "error"),
                    gap="8px"
                )
            ),
            gap="16px",
            padding="24px"
        )
    )
    
    print("✅ Initial UI rendered")
    
    # =========================================================================
    # Step 2: Simulate task progress with real-time updates
    # =========================================================================
    
    tasks = [
        "Analyzing input data...",
        "Loading knowledge base...",
        "Processing with LLM...",
        "Validating results...",
        "Generating output..."
    ]
    
    for i, task in enumerate(tasks):
        # Update progress
        progress = (i + 1) * 20
        await canvas.update(progress_bar.id, value=progress)
        
        # Update log
        await canvas.update(log_output.id, content=f"[{i+1}/{len(tasks)}] {task}")
        
        print(f"  📋 {task}")
        await asyncio.sleep(1)  # Simulate work
    
    # =========================================================================
    # Step 3: Update status to complete
    # =========================================================================
    
    await canvas.update(status_badge.id, 
        content="Complete",
        variant="success"
    )
    
    await canvas.update(log_output.id,
        content="✅ All tasks completed successfully!"
    )
    
    print("✅ Task complete!")
    
    # =========================================================================
    # Step 4: Add result display
    # =========================================================================
    
    await canvas.render(
        canvas.vstack(
            canvas.header("Agent Task Monitor", "Session: agent_session_001"),
            canvas.card("Status",
                canvas.vstack(
                    canvas.hstack(
                        canvas.text("Status: "),
                        canvas.badge("Complete", "success"),
                        gap="8px"
                    ),
                    canvas.progress(100, 100, True),
                    gap="16px"
                )
            ),
            canvas.card("Results",
                canvas.vstack(
                    QuickUI.alert("Task completed successfully!", "success"),
                    canvas.text("Output saved to: /tmp/agent_output.json"),
                    canvas.hstack(
                        canvas.button("View Output", "view_output", "primary"),
                        canvas.button("Download", "download", "secondary"),
                        canvas.button("New Task", "new_task", "secondary"),
                        gap="8px"
                    ),
                    gap="16px"
                )
            ),
            gap="16px",
            padding="24px"
        )
    )
    
    # =========================================================================
    # Step 5: Handle user interactions
    # =========================================================================
    
    def on_view_output(data):
        print("👤 User requested to view output")
        return {"action": "view", "file": "/tmp/agent_output.json"}
    
    def on_download(data):
        print("👤 User requested download")
        return {"action": "download", "file": "/tmp/agent_output.json"}
    
    def on_new_task(data):
        print("👤 User wants to start a new task")
        return {"action": "new_task"}
    
    canvas.on("view_output", on_view_output)
    canvas.on("download", on_download)
    canvas.on("new_task", on_new_task)
    
    print("\n👂 Listening for user interactions...")
    print("   (Open the URL above and click buttons)")
    
    # Keep running to handle events
    await asyncio.sleep(60)
    
    await canvas.disconnect()


async def form_example():
    """
    Example showing form handling
    """
    canvas = CanvasTool(canvas_id="agent_form_demo")
    await canvas.connect()
    
    print(f"📝 Form demo at: {canvas.get_url()}")
    
    # Render form
    await canvas.render(
        canvas.vstack(
            canvas.header("User Input Form", "Please provide the following information"),
            canvas.form("user_input", "submit_form",
                canvas.card("Personal Information",
                    canvas.vstack(
                        canvas.input("name", "Full Name", on_input="validate_name"),
                        canvas.input("email", "Email Address", "email", on_input="validate_email"),
                        canvas.select("role", [
                            {"value": "", "label": "Select Role"},
                            {"value": "admin", "label": "Administrator"},
                            {"value": "user", "label": "User"},
                            {"value": "guest", "label": "Guest"}
                        ], on_change="on_role_change"),
                        gap="16px"
                    )
                ),
                canvas.card("Preferences",
                    canvas.vstack(
                        canvas.checkbox("newsletter", "Subscribe to newsletter", True),
                        canvas.checkbox("notifications", "Enable notifications", False),
                        canvas.textarea("comments", "Additional comments", rows=3),
                        gap="16px"
                    )
                ),
                canvas.hstack(
                    canvas.button("Submit", None, "primary"),
                    canvas.button("Reset", "reset_form", "secondary"),
                    gap="8px"
                ),
                gap="16px"
            ),
            gap="24px",
            padding="24px"
        )
    )
    
    # Handle form submission
    def on_submit(data):
        print(f"📨 Form submitted: {data}")
        return {"status": "received", "fields": list(data.keys())}
    
    def on_validate_name(data):
        name = data.get("value", "")
        if len(name) < 2:
            return {"valid": False, "error": "Name too short"}
        return {"valid": True}
    
    canvas.on("submit_form", on_submit)
    canvas.on("validate_name", on_validate_name)
    
    print("👂 Waiting for form submissions...")
    await asyncio.sleep(60)
    
    await canvas.disconnect()


async def main():
    print("=" * 60)
    print("Cell 0 Canvas - Agent Usage Examples")
    print("=" * 60)
    
    print("\n1️⃣  Agent Task Monitor Example")
    print("-" * 40)
    await agent_example()
    
    print("\n2️⃣  Form Handling Example")
    print("-" * 40)
    await form_example()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nStopped by user")
