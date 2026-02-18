"""
Tool Sandboxing for Cell 0 OS

Provides isolated execution environments for risky tools.
Supports Docker containers, restricted subprocesses, and gVisor.
"""
import os
import subprocess
import tempfile
import json
import threading
import time
import signal
import resource
import sys
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import shutil


class SandboxError(Exception):
    """Base exception for sandbox errors."""
    pass


class SandboxTimeoutError(SandboxError):
    """Raised when sandbox execution times out."""
    pass


class SandboxResourceError(SandboxError):
    """Raised when resource limits are exceeded."""
    pass


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    
    # Time limits
    timeout_seconds: int = 60
    cpu_time_limit: Optional[int] = None  # CPU seconds
    
    # Memory limits
    memory_limit_mb: int = 512
    
    # Network access
    network_access: bool = False
    allowed_hosts: List[str] = field(default_factory=list)
    
    # File system
    read_only_paths: List[str] = field(default_factory=list)
    read_write_paths: List[str] = field(default_factory=list)
    tmpfs_size_mb: int = 100
    
    # Process limits
    max_processes: int = 10
    max_open_files: int = 100
    
    # User/group (for container sandboxes)
    run_as_user: str = "nobody"
    run_as_group: str = "nogroup"
    
    # Environment variables
    env_vars: Dict[str, str] = field(default_factory=dict)
    inherit_env: bool = False
    
    # Container settings
    image: str = "alpine:latest"
    runtime: str = "docker"  # docker, podman, gvisor
    
    # Output capture
    capture_stdout: bool = True
    capture_stderr: bool = True
    max_output_size: int = 10 * 1024 * 1024  # 10MB
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'SandboxConfig':
        """Create config from dictionary."""
        return cls(
            timeout_seconds=config.get('timeout', 60),
            cpu_time_limit=config.get('cpu_limit'),
            memory_limit_mb=config.get('memory_limit', '512m').replace('m', '').replace('M', ''),
            network_access=config.get('network', False),
            allowed_hosts=config.get('allowed_hosts', []),
            runtime=config.get('runtime', 'docker')
        )


@dataclass
class SandboxResult:
    """Result of sandboxed execution."""
    
    return_code: int
    stdout: str
    stderr: str
    duration_ms: int
    
    # Resource usage
    memory_peak_mb: Optional[float] = None
    cpu_time_ms: Optional[int] = None
    
    # Status
    timed_out: bool = False
    killed: bool = False
    
    @property
    def success(self) -> bool:
        """Check if execution succeeded."""
        return self.return_code == 0 and not self.timed_out and not self.killed


class BaseSandboxSession:
    """Base class for sandbox sessions."""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.started_at: Optional[datetime] = None
        self.ended_at: Optional[datetime] = None
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def start(self):
        """Start sandbox session."""
        self.started_at = datetime.utcnow()
    
    def run(self, func: Callable, *args, **kwargs) -> Any:
        """Run a function in sandbox."""
        raise NotImplementedError
    
    def execute(self, command: List[str], cwd: Optional[str] = None) -> SandboxResult:
        """Execute a command in sandbox."""
        raise NotImplementedError
    
    def cleanup(self):
        """Clean up sandbox resources."""
        self.ended_at = datetime.utcnow()


class SubprocessSandbox(BaseSandboxSession):
    """
    Sandbox using subprocess with resource limits.
    Lightweight but less isolated than containers.
    """
    
    def __init__(self, config: SandboxConfig):
        super().__init__(config)
        self.process: Optional[subprocess.Popen] = None
        self._temp_dir: Optional[str] = None
    
    def start(self):
        """Start sandbox session."""
        super().start()
        # Create temp directory for sandbox
        self._temp_dir = tempfile.mkdtemp(prefix="cell0_sandbox_")
    
    def _apply_resource_limits(self):
        """Apply resource limits to child process."""
        # Memory limit (soft, hard)
        resource.setrlimit(
            resource.RLIMIT_AS,
            (self.config.memory_limit_mb * 1024 * 1024, -1)
        )
        
        # CPU time limit
        if self.config.cpu_time_limit:
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (self.config.cpu_time_limit, self.config.cpu_time_limit + 5)
            )
        
        # Process limit
        resource.setrlimit(
            resource.RLIMIT_NPROC,
            (self.config.max_processes, self.config.max_processes)
        )
        
        # File limit
        resource.setrlimit(
            resource.RLIMIT_NOFILE,
            (self.config.max_open_files, self.config.max_open_files)
        )
    
    def execute(self, command: List[str], cwd: Optional[str] = None) -> SandboxResult:
        """Execute command with resource limits."""
        start_time = time.time()
        
        # Prepare environment
        env = {}
        if self.config.inherit_env:
            env.update(os.environ)
        env.update(self.config.env_vars)
        
        # Create network restriction if needed
        if not self.config.network_access:
            # This is a basic restriction; use containers for proper isolation
            env['PYTHONHTTPSVERIFY'] = '1'
        
        try:
            self.process = subprocess.Popen(
                command,
                cwd=cwd or self._temp_dir,
                stdout=subprocess.PIPE if self.config.capture_stdout else None,
                stderr=subprocess.PIPE if self.config.capture_stderr else None,
                env=env,
                preexec_fn=self._apply_resource_limits
            )
            
            # Wait with timeout
            try:
                stdout, stderr = self.process.communicate(
                    timeout=self.config.timeout_seconds
                )
                duration_ms = int((time.time() - start_time) * 1000)
                
                return SandboxResult(
                    return_code=self.process.returncode,
                    stdout=stdout.decode('utf-8', errors='replace') if stdout else '',
                    stderr=stderr.decode('utf-8', errors='replace') if stderr else '',
                    duration_ms=duration_ms,
                    timed_out=False
                )
                
            except subprocess.TimeoutExpired:
                self.process.kill()
                stdout, stderr = self.process.communicate()
                duration_ms = int((time.time() - start_time) * 1000)
                
                return SandboxResult(
                    return_code=-1,
                    stdout=stdout.decode('utf-8', errors='replace') if stdout else '',
                    stderr=stderr.decode('utf-8', errors='replace') if stderr else '',
                    duration_ms=duration_ms,
                    timed_out=True
                )
        
        except Exception as e:
            return SandboxResult(
                return_code=-1,
                stdout='',
                stderr=str(e),
                duration_ms=int((time.time() - start_time) * 1000)
            )
    
    def run(self, func: Callable, *args, **kwargs) -> Any:
        """Run a Python function in subprocess sandbox."""
        # Serialize function and args
        import pickle
        import base64
        
        code = f"""
import pickle
import base64
import sys

func = pickle.loads(base64.b64decode('{base64.b64encode(pickle.dumps(func)).decode()}'))
args = pickle.loads(base64.b64decode('{base64.b64encode(pickle.dumps(args)).decode()}'))
kwargs = pickle.loads(base64.b64decode('{base64.b64encode(pickle.dumps(kwargs)).decode()}'))

try:
    result = func(*args, **kwargs)
    print("RESULT:" + base64.b64encode(pickle.dumps(result)).decode())
except Exception as e:
    print("ERROR:" + str(e), file=sys.stderr)
    sys.exit(1)
"""
        
        script_path = os.path.join(self._temp_dir, "sandbox_script.py")
        with open(script_path, 'w') as f:
            f.write(code)
        
        result = self.execute([sys.executable, script_path])
        
        if result.timed_out:
            raise SandboxTimeoutError("Function execution timed out")
        
        if result.return_code != 0:
            raise SandboxError(f"Function failed: {result.stderr}")
        
        # Parse result
        for line in result.stdout.split('\n'):
            if line.startswith('RESULT:'):
                return pickle.loads(base64.b64decode(line[7:]))
        
        return None
    
    def cleanup(self):
        """Clean up temporary resources."""
        super().cleanup()
        
        if self.process and self.process.poll() is None:
            self.process.kill()
            self.process.wait()
        
        if self._temp_dir and os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)


class DockerSandbox(BaseSandboxSession):
    """
    Sandbox using Docker containers.
    Provides strong isolation but requires Docker.
    """
    
    def __init__(self, config: SandboxConfig):
        super().__init__(config)
        self.container_id: Optional[str] = None
        self._client = None
    
    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        try:
            subprocess.run(
                ['docker', 'version'],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def start(self):
        """Start Docker sandbox."""
        super().start()
        
        if not self._check_docker():
            raise SandboxError("Docker not available")
    
    def _build_run_args(self, command: List[str], cwd: Optional[str] = None) -> List[str]:
        """Build docker run command arguments."""
        args = [
            'docker', 'run',
            '--rm',  # Remove after exit
            '--interactive',
            f'--memory={self.config.memory_limit_mb}m',
            f'--cpus=1.0',
            f'--pids-limit={self.config.max_processes}',
            f'--ulimit=nofile={self.config.max_open_files}',
        ]
        
        # Network
        if not self.config.network_access:
            args.append('--network=none')
        
        # User
        args.extend(['--user', f'{self.config.run_as_user}:{self.config.run_as_group}'])
        
        # Read-only root
        args.append('--read-only')
        
        # Temp directory
        args.extend(['--tmpfs', f'/tmp:noexec,nosuid,size={self.config.tmpfs_size_mb}m'])
        
        # Mount paths
        for path in self.config.read_only_paths:
            abs_path = os.path.abspath(path)
            args.extend(['--volume', f'{abs_path}:{abs_path}:ro'])
        
        for path in self.config.read_write_paths:
            abs_path = os.path.abspath(path)
            args.extend(['--volume', f'{abs_path}:{abs_path}'])
        
        # Working directory
        if cwd:
            args.extend(['--workdir', cwd])
        
        # Environment
        for key, value in self.config.env_vars.items():
            args.extend(['--env', f'{key}={value}'])
        
        # Timeout (using timeout command inside container)
        args.extend(['--stop-timeout', str(self.config.timeout_seconds)])
        
        # Image and command
        args.append(self.config.image)
        args.extend(command)
        
        return args
    
    def execute(self, command: List[str], cwd: Optional[str] = None) -> SandboxResult:
        """Execute command in Docker container."""
        start_time = time.time()
        
        docker_args = self._build_run_args(command, cwd)
        
        try:
            result = subprocess.run(
                docker_args,
                capture_output=True,
                timeout=self.config.timeout_seconds + 5,  # Buffer for cleanup
                text=True
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return SandboxResult(
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=duration_ms,
                timed_out=result.returncode == 124  # timeout exit code
            )
        
        except subprocess.TimeoutExpired:
            return SandboxResult(
                return_code=-1,
                stdout='',
                stderr='Execution timed out',
                duration_ms=int((time.time() - start_time) * 1000),
                timed_out=True
            )
        
        except Exception as e:
            return SandboxResult(
                return_code=-1,
                stdout='',
                stderr=str(e),
                duration_ms=int((time.time() - start_time) * 1000)
            )
    
    def run(self, func: Callable, *args, **kwargs) -> Any:
        """Run function in Docker sandbox."""
        # Create temporary script
        import pickle
        import base64
        
        script = f"""
import pickle
import base64

func = pickle.loads(base64.b64decode('{base64.b64encode(pickle.dumps(func)).decode()}'))
args = pickle.loads(base64.b64decode('{base64.b64encode(pickle.dumps(args)).decode()}'))
kwargs = pickle.loads(base64.b64decode('{base64.b64encode(pickle.dumps(kwargs)).decode()}'))

result = func(*args, **kwargs)
print("RESULT:" + base64.b64encode(pickle.dumps(result)).decode())
"""
        
        # Write to temp file and mount
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            # Mount the script
            self.config.read_only_paths.append(script_path)
            
            result = self.execute([
                'python3', script_path
            ])
            
            if result.timed_out:
                raise SandboxTimeoutError("Function execution timed out")
            
            if result.return_code != 0:
                raise SandboxError(f"Function failed: {result.stderr}")
            
            # Parse result
            for line in result.stdout.split('\n'):
                if line.startswith('RESULT:'):
                    return pickle.loads(base64.b64decode(line[7:]))
            
            return None
        
        finally:
            os.unlink(script_path)
    
    def cleanup(self):
        """Clean up Docker resources."""
        super().cleanup()
        
        if self.container_id:
            try:
                subprocess.run(
                    ['docker', 'rm', '-f', self.container_id],
                    capture_output=True,
                    timeout=10
                )
            except Exception:
                pass


class RestrictedPythonSandbox(BaseSandboxSession):
    """
    Sandbox using RestrictedPython for safe code execution.
    Only for Python code, provides language-level isolation.
    """
    
    def __init__(self, config: SandboxConfig):
        super().__init__(config)
        self._globals: Dict[str, Any] = {}
    
    def start(self):
        """Start restricted Python sandbox."""
        super().start()
        
        try:
            from RestrictedPython import safe_globals
            from RestrictedPython.Guards import safe_builtins
            self._globals = {
                '__builtins__': safe_builtins,
                '_getattr_': getattr,
                '_write_': lambda x: x,
            }
        except ImportError:
            # Fallback to restricted globals
            self._globals = {
                '__builtins__': {
                    'True': True,
                    'False': False,
                    'None': None,
                    'str': str,
                    'int': int,
                    'float': float,
                    'len': len,
                    'range': range,
                    'enumerate': enumerate,
                    'zip': zip,
                    'map': map,
                    'filter': filter,
                    'sum': sum,
                    'min': min,
                    'max': max,
                    'abs': abs,
                    'round': round,
                    'print': print,
                }
            }
    
    def run_code(self, code: str) -> Any:
        """Execute Python code in restricted environment."""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Code execution timed out")
        
        # Set timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(self.config.timeout_seconds)
        
        try:
            exec(code, self._globals)
            return self._globals.get('_result', None)
        finally:
            signal.alarm(0)
    
    def run(self, func: Callable, *args, **kwargs) -> Any:
        """Run function in restricted environment."""
        # Note: This is limited - can't easily sandbox arbitrary functions
        # without subprocess or container isolation
        return func(*args, **kwargs)
    
    def execute(self, command: List[str], cwd: Optional[str] = None) -> SandboxResult:
        """Execute not supported in RestrictedPython sandbox."""
        raise NotImplementedError("Use subprocess or Docker sandbox for command execution")


class SandboxManager:
    """
    Manages sandbox sessions and configurations.
    """
    
    def __init__(self):
        self._sessions: Dict[str, BaseSandboxSession] = {}
        self._session_counter = 0
        self._lock = threading.Lock()
    
    def create_session(self, config: Optional[Union[SandboxConfig, Dict]] = None,
                       sandbox_type: str = "auto") -> BaseSandboxSession:
        """
        Create a new sandbox session.
        
        Args:
            config: Sandbox configuration
            sandbox_type: Type of sandbox (auto, docker, subprocess, restricted)
        
        Returns:
            Sandbox session
        """
        if isinstance(config, dict):
            config = SandboxConfig.from_dict(config)
        elif config is None:
            config = SandboxConfig()
        
        # Auto-detect best sandbox
        if sandbox_type == "auto":
            sandbox_type = self._detect_best_sandbox()
        
        with self._lock:
            self._session_counter += 1
            session_id = f"sandbox_{self._session_counter}"
        
        if sandbox_type == "docker":
            session = DockerSandbox(config)
        elif sandbox_type == "restricted":
            session = RestrictedPythonSandbox(config)
        else:
            session = SubprocessSandbox(config)
        
        self._sessions[session_id] = session
        return session
    
    def _detect_best_sandbox(self) -> str:
        """Detect best available sandbox type."""
        # Check for Docker
        try:
            subprocess.run(
                ['docker', 'version'],
                capture_output=True,
                check=True
            )
            return "docker"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Default to subprocess
        return "subprocess"
    
    def get_session(self, session_id: str) -> Optional[BaseSandboxSession]:
        """Get session by ID."""
        return self._sessions.get(session_id)
    
    def cleanup_session(self, session_id: str):
        """Clean up a specific session."""
        session = self._sessions.pop(session_id, None)
        if session:
            session.cleanup()
    
    def cleanup_all(self):
        """Clean up all sessions."""
        for session in self._sessions.values():
            session.cleanup()
        self._sessions.clear()
    
    def quick_execute(self, command: List[str], 
                      config: Optional[SandboxConfig] = None) -> SandboxResult:
        """Quick one-off command execution."""
        with self.create_session(config) as session:
            return session.execute(command)


# Global sandbox manager
_sandbox_manager: Optional[SandboxManager] = None


def get_sandbox_manager() -> SandboxManager:
    """Get global sandbox manager."""
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager()
    return _sandbox_manager


def sandboxed(config: Optional[SandboxConfig] = None,
              sandbox_type: str = "auto"):
    """
    Decorator to run function in sandbox.
    
    Usage:
        @sandboxed(config=SandboxConfig(timeout_seconds=30))
        def risky_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            manager = get_sandbox_manager()
            with manager.create_session(config, sandbox_type) as session:
                return session.run(func, *args, **kwargs)
        return wrapper
    return decorator
