# Cell 0 OS - Configuration Management

This module provides configuration validation, environment-specific overrides, and hot-reload support.

## Structure

```
config/
├── tool_profiles.yaml          # Base tool profiles
├── development/
│   └── app_config.yaml         # Dev overrides
├── staging/
│   └── app_config.yaml         # Staging overrides
└── production/
    └── app_config.yaml         # Production overrides
```

## Quick Start

### Loading Configuration

```python
from engine.config import ConfigManager

# Load with automatic environment detection
manager = ConfigManager()
config = manager.load_config("tool_profiles")

# Specify environment explicitly
manager = ConfigManager(environment="production")
config = manager.load_config("app_config")
```

### Validating Configuration

```python
from engine.config import ConfigValidator

validator = ConfigValidator()

# Validate single file
result = validator.validate_file("config/tool_profiles.yaml")
print(f"Valid: {result.is_valid}")
for error in result.errors:
    print(f"Error: {error}")

# Validate all configs
results = validator.validate_all()
for result in results:
    print(f"{result.file_path}: {result.status.value}")
```

### Hot Reload

```python
from engine.config import ConfigManager

manager = ConfigManager()

# Register callback for config changes
def on_config_change(new_config):
    print("Config updated!")
    # Reload settings
    
manager.watch_config("tool_profiles", on_config_change)

# Start hot-reload monitoring
manager.start_hot_reload(interval=5.0)

# Later: stop monitoring
manager.stop_hot_reload()
```

## Configuration Merging

Configurations are merged in this priority order (highest first):

1. Environment variables (`CELL0_{NAME}_{KEY}`)
2. Environment-specific config (`config/{env}/{name}.yaml`)
3. Base config (`config/{name}.yaml`)
4. Default values

### Example

Base config (`config/app_config.yaml`):
```yaml
logging:
  level: INFO
  format: simple
```

Production override (`config/production/app_config.yaml`):
```yaml
logging:
  level: WARNING
```

Environment variable:
```bash
export CELL0_APP_CONFIG_LOGGING_LEVEL=ERROR
```

Result:
```yaml
logging:
  level: ERROR  # From env var
  format: simple  # From base config
```

## Environment Variables

Set `CELL0_ENV` to control which environment config to load:

```bash
export CELL0_ENV=production  # Loads config/production/*.yaml
export CELL0_ENV=staging     # Loads config/staging/*.yaml
export CELL0_ENV=development # Loads config/development/*.yaml (default)
```

Override specific values with environment variables:

```bash
# Format: CELL0_{CONFIG_NAME}_{KEY_PATH}
export CELL0_APP_CONFIG_LOGGING_LEVEL=DEBUG
export CELL0_TOOL_PROFILES_DEFAULT_PROFILE=coding
export CELL0_OLLAMA_URL=http://custom-ollama:11434
```

## Validation Schemas

Built-in schemas for common configs:

- `tool_profiles`: Tool permission profiles
- `signal_config`: Signal integration settings
- `google_chat_config`: Google Chat settings
- `app_config`: General application settings

### Custom Validation

```python
from engine.config import ConfigValidator

validator = ConfigValidator()

# Define custom schema
my_schema = {
    "type": "object",
    "required": ["name"],
    "properties": {
        "name": {"type": "string"},
        "enabled": {"type": "boolean"}
    }
}

# Add to validator
validator.schemas["my_config"] = my_schema

# Validate
result = validator.validate_file("config/my_config.yaml")
```

## Production Usage

### Startup Validation

```python
# In your startup code
from engine.config import ConfigValidator

validator = ConfigValidator()
results = validator.validate_all()

errors = [r for r in results if not r.is_valid]
if errors:
    print("Configuration errors detected:")
    for error in errors:
        print(f"  {error.file_path}: {error.errors}")
    sys.exit(1)
```

### Runtime Reloading

```python
from engine.config import ConfigManager

manager = ConfigManager(environment="production")
config = manager.load_config("app_config")

# Reload on signal
import signal

def reload_config(signum, frame):
    print("Reloading configuration...")
    manager.reload_all()
    global config
    config = manager.load_config("app_config")

signal.signal(signal.SIGHUP, reload_config)
```

## API Reference

### ConfigManager

```python
class ConfigManager:
    def __init__(self, config_dir: Path = None, environment: str = None)
    def load_config(self, name: str, use_cache: bool = True) -> Dict[str, Any]
    def reload_config(self, name: str) -> Dict[str, Any]
    def reload_all(self) -> None
    def watch_config(self, name: str, callback: Callable) -> None
    def start_hot_reload(self, interval: float = 5.0) -> None
    def stop_hot_reload(self) -> None
```

### ConfigValidator

```python
class ConfigValidator:
    def __init__(self, config_dir: Path = None)
    def validate_file(self, file_path: Union[str, Path]) -> ValidationResult
    def validate_data(self, data: Dict, schema_name: str, file_path: str = "") -> ValidationResult
    def validate_all(self) -> List[ValidationResult]
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    file_path: str
    status: ConfigStatus  # VALID, INVALID, MISSING, DEPRECATED
    errors: List[str]
    warnings: List[str]
    is_valid: bool
```

## Troubleshooting

### Config not loading

Check file exists and is valid YAML:

```python
from engine.config import ConfigManager

manager = ConfigManager()
config = manager.load_config("my_config")
print(config)  # Should print dict or None
```

### Validation errors

Run standalone validation:

```bash
python -c "
from engine.config.validation import ConfigValidator
v = ConfigValidator()
r = v.validate_file('config/tool_profiles.yaml')
print(r.to_dict())
"
```

### Hot reload not working

Ensure file permissions allow reading:

```bash
ls -la config/
# Should be readable by the process user
```

---

*See also: [Environment Configurations](production/app_config.yaml)*
