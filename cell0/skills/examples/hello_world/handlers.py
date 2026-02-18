"""
Event handlers for Hello World skill

These functions respond to system events.
"""


def on_skill_enabled(event_data: dict):
    """
    Called when any skill is enabled.
    
    Args:
        event_data: Event data containing skill_id and other info
    """
    skill_id = event_data.get('skill_id', 'unknown')
    
    # Only log if it's not our own skill
    if skill_id != "workspace:hello_world":
        print(f"[Hello World] Noticed that {skill_id} was enabled")


def on_skill_disabled(event_data: dict):
    """
    Called when any skill is disabled.
    
    Args:
        event_data: Event data containing skill_id and other info
    """
    skill_id = event_data.get('skill_id', 'unknown')
    
    if skill_id != "workspace:hello_world":
        print(f"[Hello World] Noticed that {skill_id} was disabled")


def on_skill_loaded(event_data: dict):
    """
    Called when a skill is loaded.
    
    Args:
        event_data: Event data containing skill_id and manifest
    """
    skill_id = event_data.get('skill_id', 'unknown')
    manifest = event_data.get('manifest', {})
    
    print(f"[Hello World] Skill loaded: {manifest.get('name', skill_id)}")


def on_system_initialized(event_data: dict):
    """
    Called when the skill system is initialized.
    
    Args:
        event_data: Event data containing system info
    """
    print(f"[Hello World] Skill system initialized!")
    print(f"  Skills discovered: {event_data.get('skills_discovered', 0)}")
