"""
Cell 0 OS - Configuration Validation Module

Provides schema validation, environment-specific configurations, and hot-reload
support for Cell 0 OS configuration files.

Usage:
    from engine.config.validation import ConfigValidator, ConfigManager
    
    validator = ConfigValidator()
    result = validator.validate_file("config/tool_profiles.yaml")
    
    manager = ConfigManager()
    config = manager.load_config("tool_profiles")
"""

import os
import sys
import json
import yaml
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading
import time

try:
    from jsonschema import validate, ValidationError, Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

# Configure logging
logger = logging.getLogger("cell0.config")


class ConfigStatus(Enum):
    """Configuration validation status."""
    VALID = "valid"
    INVALID = "invalid"
    MISSING = "missing"
    DEPRECATED = "deprecated"


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    file_path: str
    status: ConfigStatus
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    schema_version: str = ""
    validated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    @property
    def is_valid(self) -> bool:
        return self.status == ConfigStatus.VALID and len(self.errors) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "status": self.status.value,
            "errors": self.errors,
            "warnings": self.warnings,
            "schema_version": self.schema_version,
            "validated_at": self.validated_at,
            "is_valid": self.is_valid
        }


class ConfigSchema:
    """JSON Schema definitions for Cell 0 configurations."""
    
    # Tool Profiles Schema
    TOOL_PROFILES_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["profiles"],
        "properties": {
            "profiles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "description"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "description": {"type": "string"},
                        "version": {"type": "string"},
                        "inherits": {"type": "string"},
                        "group_policies": {
                            "type": "object",
                            "patternProperties": {
                                "^group:": {
                                    "type": "object",
                                    "properties": {
                                        "permission": {"enum": ["ALLOW", "DENY"]},
                                        "risk_level": {"enum": ["low", "medium", "high", "critical"]},
                                        "rate_limit": {"type": "integer", "minimum": 1}
                                    }
                                }
                            }
                        },
                        "tool_policies": {
                            "type": "object",
                            "patternProperties": {
                                "^[a-z_]+$": {
                                    "type": "object",
                                    "properties": {
                                        "permission": {"enum": ["ALLOW", "DENY"]},
                                        "risk_level": {"enum": ["low", "medium", "high", "critical"]}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    # Signal Config Schema
    SIGNAL_CONFIG_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "signal_cli_url": {"type": "string", "format": "uri"},
            "phone_number": {"type": "string", "pattern": "^\\+?[0-9]+$"},
            "auto_receive": {"type": "boolean"},
            "receive_interval": {"type": "number", "minimum": 0.1, "maximum": 60},
            "rate_limits": {
                "type": "object",
                "properties": {
                    "messages_per_minute": {"type": "integer", "minimum": 1},
                    "attachments_per_minute": {"type": "integer", "minimum": 1}
                }
            },
            "storage": {
                "type": "object",
                "properties": {
                    "retention_days": {"type": "integer", "minimum": 1}
                }
            }
        }
    }
    
    # General App Config Schema
    APP_CONFIG_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "cell0": {
                "type": "object",
                "properties": {
                    "http_port": {"type": "integer", "minimum": 1024, "maximum": 65535},
                    "ws_port": {"type": "integer", "minimum": 1024, "maximum": 65535},
                    "log_level": {"enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
                    "max_workers": {"type": "integer", "minimum": 1, "maximum": 100},
                    "enable_metrics": {"type": "boolean"},
                    "enable_cors": {"type": "boolean"}
                }
            },
            "ollama": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri"},
                    "default_model": {"type": "string"},
                    "timeout": {"type": "integer", "minimum": 1}
                }
            }
        }
    }
    
    # Mapping of config names to schemas
    SCHEMAS = {
        "tool_profiles": TOOL_PROFILES_SCHEMA,
        "signal_config": SIGNAL_CONFIG_SCHEMA,
        "app_config": APP_CONFIG_SCHEMA,
        "google_chat_config": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "credentials_path": {"type": "string"}
            }
        }
    }


class ConfigValidator:
    """Validates Cell 0 configuration files against schemas."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path("config")
        self.schemas = ConfigSchema.SCHEMAS
        self._validator_cache: Dict[str, Any] = {}
        
        if JSONSCHEMA_AVAILABLE:
            # Pre-compile validators for performance
            for name, schema in self.schemas.items():
                self._validator_cache[name] = Draft7Validator(schema)
    
    def validate_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """
        Validate a configuration file.
        
        Args:
            file_path: Path to the configuration file
            
        Returns:
            ValidationResult with status and any errors/warnings
        """
        file_path = Path(file_path)
        
        # Check file exists
        if not file_path.exists():
            return ValidationResult(
                file_path=str(file_path),
                status=ConfigStatus.MISSING,
                errors=["File does not exist"]
            )
        
        # Load file
        try:
            config_data = self._load_file(file_path)
        except Exception as e:
            return ValidationResult(
                file_path=str(file_path),
                status=ConfigStatus.INVALID,
                errors=[f"Failed to load file: {e}"]
            )
        
        # Determine schema to use
        schema_name = self._detect_schema(file_path)
        
        # Validate
        return self.validate_data(config_data, schema_name, str(file_path))
    
    def validate_data(
        self,
        data: Dict[str, Any],
        schema_name: str,
        file_path: str = ""
    ) -> ValidationResult:
        """
        Validate configuration data against a schema.
        
        Args:
            data: Configuration data as dictionary
            schema_name: Name of the schema to validate against
            file_path: Optional file path for error reporting
            
        Returns:
            ValidationResult with validation status
        """
        if schema_name not in self.schemas:
            return ValidationResult(
                file_path=file_path,
                status=ConfigStatus.INVALID,
                errors=[f"Unknown schema: {schema_name}"],
                schema_version=schema_name
            )
        
        if not JSONSCHEMA_AVAILABLE:
            logger.warning("jsonschema not installed, using basic validation")
            return self._basic_validation(data, schema_name, file_path)
        
        # Use jsonschema for validation
        validator = self._validator_cache.get(schema_name)
        errors = []
        warnings = []
        
        for error in validator.iter_errors(data):
            error_msg = f"{error.message} at {'.'.join(str(p) for p in error.path)}"
            if error.validator in ["required", "type"]:
                errors.append(error_msg)
            else:
                warnings.append(error_msg)
        
        status = ConfigStatus.VALID if not errors else ConfigStatus.INVALID
        
        return ValidationResult(
            file_path=file_path,
            status=status,
            errors=errors,
            warnings=warnings,
            schema_version=schema_name
        )
    
    def validate_all(self) -> List[ValidationResult]:
        """Validate all configuration files in the config directory."""
        results = []
        
        if not self.config_dir.exists():
            logger.warning(f"Config directory not found: {self.config_dir}")
            return results
        
        for config_file in self.config_dir.glob("*.yaml"):
            result = self.validate_file(config_file)
            results.append(result)
        
        # Also check integration configs
        integrations_dir = Path("integrations")
        if integrations_dir.exists():
            for config_file in integrations_dir.glob("*.yaml"):
                result = self.validate_file(config_file)
                results.append(result)
        
        return results
    
    def _load_file(self, file_path: Path) -> Dict[str, Any]:
        """Load a configuration file."""
        content = file_path.read_text()
        
        if file_path.suffix in ['.yaml', '.yml']:
            return yaml.safe_load(content)
        elif file_path.suffix == '.json':
            return json.loads(content)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    def _detect_schema(self, file_path: Path) -> str:
        """Detect which schema to use for a file."""
        name = file_path.stem
        
        # Direct mapping
        if name in self.schemas:
            return name
        
        # Pattern matching
        if "tool" in name.lower() and "profile" in name.lower():
            return "tool_profiles"
        elif "signal" in name.lower():
            return "signal_config"
        elif "google" in name.lower() or "chat" in name.lower():
            return "google_chat_config"
        
        # Default
        return "app_config"
    
    def _basic_validation(
        self,
        data: Dict[str, Any],
        schema_name: str,
        file_path: str
    ) -> ValidationResult:
        """Basic validation without jsonschema (fallback)."""
        errors = []
        warnings = []
        
        # Check if data is dict
        if not isinstance(data, dict):
            errors.append("Configuration must be a dictionary/object")
        
        # Schema-specific checks
        if schema_name == "tool_profiles":
            if "profiles" not in data:
                errors.append("Missing required field: profiles")
            elif not isinstance(data.get("profiles"), list):
                errors.append("profiles must be a list")
        
        status = ConfigStatus.VALID if not errors else ConfigStatus.INVALID
        
        return ValidationResult(
            file_path=file_path,
            status=status,
            errors=errors,
            warnings=warnings,
            schema_version=schema_name
        )


class ConfigManager:
    """
    Manages configuration loading with environment-specific overrides
    and hot-reload support.
    """
    
    ENVIRONMENTS = ["development", "staging", "production"]
    
    def __init__(self, config_dir: Optional[Path] = None, environment: Optional[str] = None):
        self.config_dir = config_dir or Path("config")
        self.environment = environment or os.getenv("CELL0_ENV", "development")
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._file_hashes: Dict[str, str] = {}
        self._watchers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        self._watcher_thread: Optional[threading.Thread] = None
        self._stop_watching = threading.Event()
        
        # Environment-specific directory
        self.env_config_dir = self.config_dir / self.environment
    
    def load_config(
        self,
        name: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Load a configuration file with environment overrides.
        
        Args:
            name: Configuration name (without extension)
            use_cache: Whether to use cached config if available
            
        Returns:
            Configuration as dictionary
        """
        with self._lock:
            if use_cache and name in self._configs:
                return self._configs[name]
            
            # Load base config
            base_config = self._load_config_file(name)
            
            # Load environment-specific override
            env_config = self._load_config_file(name, env_specific=True)
            
            # Merge configurations
            merged = self._merge_configs(base_config or {}, env_config or {})
            
            # Apply environment variable overrides
            merged = self._apply_env_overrides(name, merged)
            
            # Cache result
            self._configs[name] = merged
            
            # Store file hash for change detection
            base_file = self._get_config_path(name)
            if base_file.exists():
                self._file_hashes[str(base_file)] = self._calculate_hash(base_file)
            
            return merged
    
    def reload_config(self, name: str) -> Dict[str, Any]:
        """Force reload a configuration from disk."""
        with self._lock:
            if name in self._configs:
                del self._configs[name]
        return self.load_config(name, use_cache=False)
    
    def reload_all(self) -> None:
        """Reload all configurations."""
        with self._lock:
            self._configs.clear()
            self._file_hashes.clear()
    
    def watch_config(self, name: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback to be called when a config changes.
        
        Args:
            name: Configuration name to watch
            callback: Function to call with new config when changed
        """
        with self._lock:
            if name not in self._watchers:
                self._watchers[name] = []
            self._watchers[name].append(callback)
        
        # Start watcher thread if not running
        self._start_watcher()
    
    def start_hot_reload(self, interval: float = 5.0) -> None:
        """
        Start hot-reload monitoring.
        
        Args:
            interval: Check interval in seconds
        """
        self._stop_watching.clear()
        
        def watch_loop():
            while not self._stop_watching.wait(interval):
                self._check_for_changes()
        
        self._watcher_thread = threading.Thread(target=watch_loop, daemon=True)
        self._watcher_thread.start()
        logger.info(f"Started config hot-reload (interval: {interval}s)")
    
    def stop_hot_reload(self) -> None:
        """Stop hot-reload monitoring."""
        self._stop_watching.set()
        if self._watcher_thread:
            self._watcher_thread.join(timeout=1.0)
    
    def get_active_configs(self) -> List[str]:
        """Get list of currently loaded configurations."""
        with self._lock:
            return list(self._configs.keys())
    
    def _load_config_file(
        self,
        name: str,
        env_specific: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Load a single configuration file."""
        if env_specific:
            file_path = self.env_config_dir / f"{name}.yaml"
        else:
            file_path = self.config_dir / f"{name}.yaml"
        
        if not file_path.exists():
            # Try .yml extension
            file_path = file_path.with_suffix('.yml')
            if not file_path.exists():
                return None
        
        try:
            content = file_path.read_text()
            return yaml.safe_load(content)
        except Exception as e:
            logger.error(f"Failed to load config {file_path}: {e}")
            return None
    
    def _get_config_path(self, name: str, env_specific: bool = False) -> Path:
        """Get the path to a config file."""
        if env_specific:
            return self.env_config_dir / f"{name}.yaml"
        return self.config_dir / f"{name}.yaml"
    
    def _merge_configs(
        self,
        base: Dict[str, Any],
        override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two configurations."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_env_overrides(
        self,
        name: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply environment variable overrides."""
        # Look for CELL0_{NAME}_{KEY} pattern
        prefix = f"CELL0_{name.upper()}_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Parse nested keys (e.g., CELL0_TOOL_PROFILES_LOGGING_LEVEL)
                config_key = key[len(prefix):].lower()
                
                # Handle nested paths (e.g., logging_level -> logging.level)
                if "_" in config_key:
                    parts = config_key.split("_")
                    target = config
                    for part in parts[:-1]:
                        if part not in target:
                            target[part] = {}
                        target = target[part]
                    target[parts[-1]] = self._parse_env_value(value)
                else:
                    config[config_key] = self._parse_env_value(value)
        
        return config
    
    def _parse_env_value(self, value: str) -> Union[str, int, float, bool]:
        """Parse environment variable value to appropriate type."""
        # Boolean
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        
        # Integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float
        try:
            return float(value)
        except ValueError:
            pass
        
        # String (default)
        return value
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file contents."""
        content = file_path.read_bytes()
        return hashlib.md5(content).hexdigest()
    
    def _check_for_changes(self) -> None:
        """Check for configuration file changes."""
        with self._lock:
            for config_name in list(self._configs.keys()):
                base_file = self._get_config_path(config_name)
                if not base_file.exists():
                    continue
                
                current_hash = self._calculate_hash(base_file)
                previous_hash = self._file_hashes.get(str(base_file))
                
                if current_hash != previous_hash:
                    logger.info(f"Config changed: {config_name}")
                    
                    # Reload config
                    del self._configs[config_name]
                    new_config = self.load_config(config_name, use_cache=False)
                    
                    # Notify watchers
                    if config_name in self._watchers:
                        for callback in self._watchers[config_name]:
                            try:
                                callback(new_config)
                            except Exception as e:
                                logger.error(f"Config watcher error: {e}")
    
    def _start_watcher(self) -> None:
        """Start the file watcher if not already running."""
        if self._watcher_thread is None or not self._watcher_thread.is_alive():
            self.start_hot_reload()


class ConfigEnvironment:
    """Helper for environment-specific configuration."""
    
    def __init__(self, environment: str):
        self.environment = environment
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    @property
    def is_staging(self) -> bool:
        return self.environment == "staging"
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    def get_defaults(self) -> Dict[str, Any]:
        """Get environment-specific defaults."""
        defaults = {
            "development": {
                "debug": True,
                "log_level": "DEBUG",
                "reload_on_change": True,
                "enable_metrics": False
            },
            "staging": {
                "debug": False,
                "log_level": "INFO",
                "reload_on_change": False,
                "enable_metrics": True
            },
            "production": {
                "debug": False,
                "log_level": "WARNING",
                "reload_on_change": False,
                "enable_metrics": True
            }
        }
        return defaults.get(self.environment, defaults["development"])


# Convenience functions
def validate_config(file_path: Union[str, Path]) -> ValidationResult:
    """Quick validation of a configuration file."""
    validator = ConfigValidator()
    return validator.validate_file(file_path)


def load_config(name: str, environment: Optional[str] = None) -> Dict[str, Any]:
    """Quick load of a configuration."""
    manager = ConfigManager(environment=environment)
    return manager.load_config(name)


# Example usage
if __name__ == "__main__":
    # Validate all configs
    validator = ConfigValidator()
    results = validator.validate_all()
    
    print("Configuration Validation Results:")
    print("=" * 60)
    for result in results:
        status_icon = "✅" if result.is_valid else "❌"
        print(f"{status_icon} {result.file_path}: {result.status.value}")
        for error in result.errors:
            print(f"   Error: {error}")
        for warning in result.warnings:
            print(f"   Warning: {warning}")
    
    # Load config with environment
    manager = ConfigManager(environment="production")
    config = manager.load_config("tool_profiles")
    print("\nLoaded tool_profiles config:")
    print(json.dumps(config, indent=2)[:500] + "...")
