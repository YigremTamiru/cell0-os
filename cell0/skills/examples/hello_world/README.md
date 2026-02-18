# Hello World Example Skill

This is a simple example skill demonstrating the Cell 0 OS skill system capabilities.

## What It Demonstrates

- **Skill Manifest**: Complete `skill.yaml` with all field types
- **Tools**: Registration of callable tools with parameters
- **CLI Commands**: Custom commands accessible via `cell0ctl`
- **Event Handlers**: Reacting to system lifecycle events
- **Multiple Languages**: Support for greetings in different languages

## Installation

```bash
# From the Cell 0 root directory
cell0ctl skill install ./skills/examples/hello_world --enable
```

## Usage

### Tools

Once enabled, other skills can use the tools:

```python
from cell0.engine.skills import get_registry

registry = get_registry()

# Call the hello tool
hello_tool = registry.get_tool("hello")
result = hello_tool(name="Alice", language="es")
print(result['message'])  # "¡Hola, Alice!"

# Call the goodbye tool
goodbye_tool = registry.get_tool("goodbye")
result = goodbye_tool(name="Bob")
print(result['message'])  # "Goodbye, Bob!"
```

### CLI Commands

```bash
# Say hello
cell0ctl hello
# Output: Hello, World!

cell0ctl hello --name Alice --language fr
# Output: Bonjour, Alice!

# Or use the alias
cell0ctl hi -n Bob -l es
# Output: ¡Hola, Bob!

# Say goodbye
cell0ctl goodbye
cell0ctl bye --name Alice
```

## Project Structure

```
hello_world/
├── skill.yaml      # Skill manifest
├── __init__.py     # Lifecycle hooks
├── tools.py        # Tool implementations
├── cli.py          # CLI command handlers
└── handlers.py     # Event handlers
```

## Extending

To extend this skill:

1. Add new tools to `tools.py`
2. Register them in `skill.yaml`
3. Add CLI commands in `cli.py`
4. Implement event handlers in `handlers.py`

## Learn More

See the full skill system documentation at:
`cell0/engine/skills/README.md`
