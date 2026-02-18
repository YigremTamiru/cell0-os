"""
Skill System Documentation for Cell 0 OS

The Cell 0 OS Skill System provides a dynamic plugin architecture for extending
the operating system's capabilities. Skills can register tools, CLI commands,
and event handlers.

## Quick Start

### 1. Create a New Skill

```bash
cell0ctl skill create my_skill --workspace
```

This creates a new skill template in your workspace skills directory.

### 2. Define Your Skill

Edit `skill.yaml`:

```yaml
id: my_skill
name: My Amazing Skill
version: 1.0.0
description: Does something amazing
author: Your Name
type: workspace

tools:
  - name: do_amazing_thing
    module: my_skill.tools
    function: do_thing
    description: Performs an amazing action
    parameters:
      input:
        type: string
        description: Input to process

commands:
  - name: amazing
    module: my_skill.cli
    function: run
    description: Run the amazing command
    aliases: [amz]

events:
  - event_type: skill.enabled
    module: my_skill.handlers
    function: on_enabled
    priority: 100
```

### 3. Implement Your Skill

Create `tools.py`:

```python
def do_thing(input: str = ""):
    \"\"\"Perform an amazing action\"\"\"
    return {"result": f"Processed: {input}"}
```

Create `cli.py`:

```python
def run(args):
    \"\"\"CLI entry point\"\"\"
    print("Running amazing command!")
    return 0
```

Create `handlers.py`:

```python
def on_enabled(event_data):
    \"\"\"Called when skill is enabled\"\"\"
    print(f"Skill enabled: {event_data['skill_id']}")
```

### 4. Install and Enable

```bash
# Install the skill
cell0ctl skill install ./my_skill --enable

# Or discover and enable separately
cell0ctl skill discover
cell0ctl skill enable workspace:my_skill
```

## Skill Types

### System Skills
Located in `/opt/cell0/skills/system/`
- Shipped with Cell 0 OS
- Core system functionality
- Protected from uninstall

### Workspace Skills  
Located in `~/.cell0/skills/`
- User-created skills
- Project-specific extensions
- Portable across workspaces

### Installed Skills
Located in `/opt/cell0/skills/installed/`
- Third-party skills
- Community extensions
- Managed by package manager

## Skill Lifecycle

```
DISCOVERED -> LOADED -> ENABLED
                 ↓         ↓
              DISABLED <-┘
                 ↓
              UNLOADED
```

States:
- **DISCOVERED**: Found on filesystem, not loaded
- **LOADED**: Module loaded into memory
- **ENABLED**: Active and functional
- **DISABLED**: Loaded but inactive
- **UNLOADED**: Removed from memory

## Manifest Reference

### Required Fields

- `id`: Unique identifier (alphanumeric + underscores/hyphens)
- `name`: Human-readable name
- `version`: Semantic version (e.g., "1.0.0")

### Optional Fields

- `description`: Brief description
- `author`: Author name
- `license`: License identifier (default: MIT)
- `homepage`: Project homepage URL
- `repository`: Source code repository URL
- `type`: Skill type (system/workspace/installed)

### Dependencies

```yaml
dependencies:
  - core_utils              # Any version
  - database>=2.0.0         # Minimum version
  - web_framework^1.0.0     # Compatible version (same major)
  - optional_lib>=3.0.0     # Optional dependency
```

### Tools

Tools are callable functions that the engine can invoke:

```yaml
tools:
  - name: tool_name
    module: skill_name.module
    function: function_name
    description: What it does
    parameters:          # JSON Schema style
      param1:
        type: string
        description: Parameter description
```

### Commands

CLI commands accessible via `cell0ctl`:

```yaml
commands:
  - name: command-name
    module: skill_name.cli
    function: handler
    description: Command description
    aliases: [alias1, alias2]
    arguments:
      - name: arg1
        required: true
        type: string
```

### Event Handlers

React to system events:

```yaml
events:
  - event_type: skill.loaded
    module: skill_name.handlers
    function: on_skill_loaded
    priority: 100          # Lower = higher priority
```

Standard events:
- `skill_system.initialized`: System startup
- `skill_system.shutdown`: System shutdown
- `skill.discovered`: New skill found
- `skill.loaded`: Skill loaded
- `skill.enabled`: Skill enabled
- `skill.disabled`: Skill disabled
- `skill.unloaded`: Skill unloaded
- `skill.reloaded`: Skill reloaded

## Python API

### Getting Started

```python
from cell0.engine.skills import get_manager, SkillStatus

manager = get_manager()

# List skills
skills = manager.list_skills()

# Filter by status
enabled = manager.list_skills(status=SkillStatus.ENABLED)

# Get skill info
skill = manager.get_skill("workspace:my_skill")
print(skill.name, skill.version)

# Enable a skill
await manager.enable_skill("workspace:my_skill")

# Disable a skill
await manager.disable_skill("workspace:my_skill")

# Reload a skill (useful during development)
await manager.reload_skill("workspace:my_skill")
```

### Accessing the Registry

```python
from cell0.engine.skills import get_registry

registry = get_registry()

# Get a tool
tool = registry.get_tool("my_tool")
result = tool(param="value")

# List all tools
tools = registry.list_tools()

# Get a command
cmd = registry.get_command("my-command")
exit_code = cmd(args)

# Emit events
results = await registry.emit_event("my.event", {"data": "value"})
```

### Skill Hooks

Your skill can implement lifecycle hooks:

```python
# __init__.py

def initialize():
    \"\"\"Called when skill is first loaded\"\"\"
    pass

def enable():
    \"\"\"Called when skill is enabled\"\"\"
    pass

def disable():
    \"\"\"Called when skill is disabled\"\"\"
    pass

def cleanup():
    \"\"\"Called when skill is unloaded\"\"\"
    pass
```

## CLI Commands

### List Skills
```bash
cell0ctl skill list                    # All skills
cell0ctl skill list --enabled          # Only enabled
cell0ctl skill list --disabled         # Only disabled
```

### Show Skill Info
```bash
cell0ctl skill info workspace:my_skill
```

### Enable/Disable
```bash
cell0ctl skill enable workspace:my_skill
cell0ctl skill disable workspace:my_skill
```

### Install/Uninstall
```bash
# Install from directory
cell0ctl skill install ./my_skill

# Install with specific type
cell0ctl skill install ./my_skill --workspace
cell0ctl skill install ./my_skill --system

# Install and enable
cell0ctl skill install ./my_skill --enable

# Uninstall
cell0ctl skill uninstall workspace:my_skill
```

### Create New Skill
```bash
cell0ctl skill create my_skill              # Create in workspace
cell0ctl skill create my_skill --system     # Create in system path
```

### System Stats
```bash
cell0ctl skill stats
cell0ctl skill stats --json
```

### Rediscover Skills
```bash
cell0ctl skill discover
```

## Best Practices

1. **Version your skills**: Use semantic versioning
2. **Document parameters**: Provide clear parameter descriptions
3. **Handle errors gracefully**: Skills shouldn't crash the system
4. **Use event handlers**: React to lifecycle events appropriately
5. **Test thoroughly**: Use the test framework provided
6. **Namespace carefully**: Avoid naming conflicts with other skills
7. **Clean up resources**: Implement cleanup() properly

## Troubleshooting

### Skill not discovered
- Ensure `skill.yaml` exists and is valid
- Check file permissions
- Run `cell0ctl skill discover` to refresh

### Import errors
- Check module paths in manifest
- Ensure Python files are valid
- Verify entry_point in skill.yaml

### Dependency issues
- Check version constraints
- Ensure dependencies are loaded first
- Use `cell0ctl skill info` to check status

## Examples

See `skills/examples/` for complete example skills demonstrating:
- Basic tool registration
- CLI command implementation
- Event handling
- Dependency management

## Contributing

To contribute skills to the Cell 0 OS ecosystem:

1. Create your skill following these guidelines
2. Test thoroughly
3. Submit to the Cell 0 Skills Repository
4. Include documentation and examples

---

For more information, visit the Cell 0 OS documentation.
"""
