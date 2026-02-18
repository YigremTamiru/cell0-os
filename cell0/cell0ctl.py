#!/usr/bin/env python3
"""
cell0ctl.py - Cell 0 OS Command Line Interface
Production CLI for managing Cell 0 OS daemon and operations.

Usage:
    cell0ctl status           # Show system status (default command)
    cell0ctl start            # Start the daemon
    cell0ctl stop             # Stop the daemon
    cell0ctl restart          # Restart the daemon
    cell0ctl logs             # View logs with filtering
    cell0ctl health           # Show health dashboard
    cell0ctl doctor           # Run diagnostics
    cell0ctl setup            # First-run configuration wizard
    cell0ctl config           # Manage configuration
    cell0ctl agent list       # List agents
    cell0ctl agent restart    # Restart an agent

Environment:
    CELL0_HOME         Cell 0 installation directory (default: ~/cell0)
    CELL0_STATE_DIR    Cell 0 state directory (default: ~/.cell0)
    CELL0_LOG_LEVEL    Logging level (default: INFO)
"""

import os
import sys
import json
import time
import signal
import socket
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
import subprocess
import argparse

# Rich for beautiful CLI output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.syntax import Syntax
    from rich.tree import Tree
    from rich.layout import Layout
    from rich.columns import Columns
    from rich import box
    from rich.prompt import Prompt, Confirm
    from rich.style import Style
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    class FakeConsole:
        def print(self, *args, **kwargs):
            print(*args)
        def rule(self, *args, **kwargs):
            print("-" * 50)
    Console = FakeConsole

console = Console()

# Configuration
DEFAULT_CELL0_HOME = Path.home() / "cell0"
DEFAULT_STATE_DIR = Path.home() / ".cell0"
DEFAULT_PORT = 18800
PID_FILE = DEFAULT_STATE_DIR / "cell0d.pid"
CONFIG_FILE = DEFAULT_STATE_DIR / "config.json"
VERSION = "1.2.0"


@dataclass
class DaemonStatus:
    """Daemon status information"""
    running: bool
    pid: Optional[int] = None
    version: str = "unknown"
    uptime: Optional[str] = None
    uptime_seconds: float = 0.0
    port: int = DEFAULT_PORT
    environment: str = "unknown"
    ws_port: Optional[int] = None
    metrics_port: Optional[int] = None


@dataclass
class LogEntry:
    """Represents a parsed log entry"""
    timestamp: Optional[datetime] = None
    level: str = "INFO"
    logger: str = "unknown"
    message: str = ""
    raw_line: str = ""


class ConfigManager:
    """Manages Cell 0 configuration"""
    
    def __init__(self):
        self.config_path = CONFIG_FILE
        self.state_dir = DEFAULT_STATE_DIR
        self._config: Dict[str, Any] = {}
        self._load()
    
    def _load(self):
        """Load configuration from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._config = {}
    
    def save(self):
        """Save configuration to file"""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self._config, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self._config[key] = value
    
    def exists(self) -> bool:
        """Check if config file exists"""
        return self.config_path.exists()
    
    def is_first_run(self) -> bool:
        """Check if this is first run"""
        return not self.exists() or not self.get("setup_complete", False)


class Cell0CTL:
    """Cell 0 Control CLI"""
    
    def __init__(self):
        self.cell0_home = Path(os.getenv("CELL0_HOME", DEFAULT_CELL0_HOME))
        self.state_dir = Path(os.getenv("CELL0_STATE_DIR", DEFAULT_STATE_DIR))
        self.api_url = f"http://localhost:{DEFAULT_PORT}"
        self.config = ConfigManager()
        
    def _get_venv_python(self) -> Path:
        """Get the correct Python interpreter from venv"""
        venv_paths = [
            self.cell0_home / ".venv" / "bin" / "python3",
            self.cell0_home / "venv" / "bin" / "python3",
            Path.home() / ".cell0" / "venv" / "bin" / "python3",
        ]
        
        for venv_path in venv_paths:
            if venv_path.exists():
                return venv_path
        return Path(sys.executable)
    
    def _check_daemon_running(self) -> DaemonStatus:
        """Check if daemon is running with detailed info"""
        if not PID_FILE.exists():
            return DaemonStatus(running=False)
        
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
            
            # Try to get detailed status from API
            try:
                import urllib.request
                with urllib.request.urlopen(
                    f"{self.api_url}/api/status", timeout=2
                ) as resp:
                    data = json.loads(resp.read())
                    daemon_data = data.get("daemon", {})
                    config_data = data.get("config", {})
                    ports = config_data.get("ports", {})
                    
                    return DaemonStatus(
                        running=True,
                        pid=pid,
                        version=daemon_data.get("version", VERSION),
                        uptime=self._format_uptime(daemon_data.get("uptime", 0)),
                        uptime_seconds=daemon_data.get("uptime", 0),
                        port=ports.get("http", DEFAULT_PORT),
                        environment=daemon_data.get("environment", "unknown"),
                        ws_port=ports.get("websocket"),
                        metrics_port=ports.get("metrics")
                    )
            except Exception:
                # Process exists but API not responding
                return DaemonStatus(running=True, pid=pid)
                
        except (OSError, ValueError):
            # Process not running, stale PID file
            PID_FILE.unlink(missing_ok=True)
            return DaemonStatus(running=False)
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human readable form"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            return f"{days}d {hours}h"
    
    def _get_listening_ports(self) -> List[Tuple[int, str]]:
        """Get list of ports Cell 0 is listening on"""
        ports = []
        status = self._check_daemon_running()
        
        if status.running:
            # Check main port
            if self._is_port_listening(DEFAULT_PORT):
                ports.append((DEFAULT_PORT, "HTTP API"))
            if status.ws_port and self._is_port_listening(status.ws_port):
                ports.append((status.ws_port, "WebSocket"))
            if status.metrics_port and self._is_port_listening(status.metrics_port):
                ports.append((status.metrics_port, "Metrics"))
        
        return ports
    
    def _is_port_listening(self, port: int) -> bool:
        """Check if a port is listening"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def _get_active_channels(self) -> List[Dict[str, Any]]:
        """Get active channel information"""
        channels = []
        
        # Check for Signal
        try:
            result = subprocess.run(
                ["pgrep", "-f", "signal-cli"],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                channels.append({
                    "name": "Signal",
                    "status": "active",
                    "type": "messaging"
                })
        except Exception:
            pass
        
        # Check for WhatsApp (if implemented)
        # channels.append({"name": "WhatsApp", ...})
        
        return channels
    
    def _get_recent_errors(self, count: int = 5) -> List[str]:
        """Get recent error lines from logs"""
        errors = []
        log_file = self.state_dir / "logs" / "cell0d.log"
        
        if not log_file.exists():
            return errors
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Look for ERROR or CRITICAL lines
                for line in reversed(lines):
                    if 'ERROR' in line or 'CRITICAL' in line or 'Traceback' in line:
                        errors.append(line.strip())
                        if len(errors) >= count:
                            break
        except Exception:
            pass
        
        return list(reversed(errors))  # Return in chronological order
    
    def _parse_log_line(self, line: str) -> LogEntry:
        """Parse a log line into a LogEntry"""
        entry = LogEntry(raw_line=line.strip())
        
        # Try JSON format first
        try:
            data = json.loads(line)
            entry.timestamp = datetime.fromisoformat(
                data.get("timestamp", "").replace("Z", "+00:00")
            ) if "timestamp" in data else None
            entry.level = data.get("level", "INFO")
            entry.logger = data.get("logger", "unknown")
            entry.message = data.get("message", line.strip())
            return entry
        except json.JSONDecodeError:
            pass
        
        # Try plain format: "2024-01-01 10:00:00 | LEVEL | logger | message"
        match = re.match(
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*\|\s*(\w+)\s*\|\s*([^|]+)\|\s*(.+)',
            line
        )
        if match:
            try:
                entry.timestamp = datetime.strptime(
                    match.group(1), "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                pass
            entry.level = match.group(2).strip()
            entry.logger = match.group(3).strip()
            entry.message = match.group(4).strip()
        else:
            entry.message = line.strip()
        
        return entry
    
    def _write_pid(self, pid: int):
        """Write PID file"""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(pid))
    
    def _remove_pid(self):
        """Remove PID file"""
        PID_FILE.unlink(missing_ok=True)
    
    # ==================== COMMANDS ====================
    
    def cmd_status(self, args: argparse.Namespace = None):
        """Show enhanced system status with Rich tables/panels"""
        status = self._check_daemon_running()
        
        if not HAS_RICH:
            # Plain text fallback
            if status.running:
                print(f"Status: Running (PID: {status.pid})")
                print(f"Version: {status.version}")
                print(f"Uptime: {status.uptime}")
                print(f"Port: {status.port}")
                print(f"Environment: {status.environment}")
            else:
                print("Status: Not running")
                print("Start with: cell0ctl start")
            return
        
        # Rich enhanced output
        console.print()
        
        if status.running:
            # Main status panel
            status_grid = Table.grid(padding=1)
            status_grid.add_column(style="cyan", justify="right")
            status_grid.add_column()
            
            status_grid.add_row("Status:", "[green]● Running[/green]")
            status_grid.add_row("PID:", str(status.pid))
            status_grid.add_row("Version:", f"[cyan]{status.version}[/cyan]")
            status_grid.add_row("Uptime:", f"[green]{status.uptime}[/green]")
            status_grid.add_row("Environment:", f"[yellow]{status.environment}[/yellow]")
            
            console.print(Panel(
                status_grid,
                title="[bold blue]Cell 0 Daemon Status[/bold blue]",
                border_style="green",
                padding=(1, 2)
            ))
            
            # Ports table
            ports = self._get_listening_ports()
            if ports:
                ports_table = Table(
                    title="\n[bold]Listening Ports[/bold]",
                    box=box.ROUNDED,
                    show_header=True
                )
                ports_table.add_column("Port", style="cyan", justify="right")
                ports_table.add_column("Service", style="green")
                
                for port, service in ports:
                    ports_table.add_row(str(port), service)
                
                console.print(ports_table)
            
            # Active channels
            channels = self._get_active_channels()
            if channels:
                channels_table = Table(
                    title="\n[bold]Active Channels[/bold]",
                    box=box.ROUNDED
                )
                channels_table.add_column("Channel", style="cyan")
                channels_table.add_column("Status")
                channels_table.add_column("Type", style="dim")
                
                for ch in channels:
                    status_str = "[green]● Active[/green]" if ch.get("status") == "active" else "[red]● Inactive[/red]"
                    channels_table.add_row(
                        ch.get("name", "Unknown"),
                        status_str,
                        ch.get("type", "unknown")
                    )
                
                console.print(channels_table)
            
            # Recent errors panel
            errors = self._get_recent_errors(5)
            if errors:
                error_text = Text()
                for i, error in enumerate(errors, 1):
                    error_text.append(f"{i}. ", style="dim")
                    # Truncate long lines
                    error_preview = error[:120] + "..." if len(error) > 120 else error
                    error_text.append(error_preview + "\n", style="red")
                
                console.print(Panel(
                    error_text,
                    title="[bold red]Recent Errors[/bold red]",
                    border_style="red",
                    padding=(1, 1)
                ))
            else:
                console.print(Panel(
                    "[green]No recent errors found[/green]",
                    title="[bold]Recent Errors[/bold]",
                    border_style="green"
                ))
            
            # Try to get detailed API status
            try:
                import urllib.request
                with urllib.request.urlopen(
                    f"{self.api_url}/api/status", timeout=5
                ) as resp:
                    data = json.loads(resp.read())
                    
                    # Services status
                    services = data.get("services", {})
                    if services:
                        svc_table = Table(
                            title="\n[bold]Services[/bold]",
                            box=box.ROUNDED
                        )
                        svc_table.add_column("Service", style="cyan")
                        svc_table.add_column("Status", justify="center")
                        
                        for svc, active in services.items():
                            if active:
                                svc_table.add_row(
                                    svc.replace("_", " ").title(),
                                    "[green]✓ Active[/green]"
                                )
                            else:
                                svc_table.add_row(
                                    svc.replace("_", " ").title(),
                                    "[red]✗ Inactive[/red]"
                                )
                        
                        console.print(svc_table)
                    
                    # Agent counts
                    agents = data.get("agents", {})
                    if agents:
                        agent_table = Table(
                            title="\n[bold]Agents[/bold]",
                            box=box.ROUNDED
                        )
                        agent_table.add_column("Type", style="cyan")
                        agent_table.add_column("Count", justify="right")
                        
                        for agent_type, count in agents.items():
                            agent_table.add_row(
                                agent_type.replace("_", " ").title(),
                                str(count)
                            )
                        
                        console.print(agent_table)
                        
            except Exception as e:
                console.print(
                    f"\n[yellow]Could not fetch detailed status: {e}[/yellow]"
                )
        else:
            # Not running panel
            console.print(Panel(
                "\n[red]● Daemon is not running[/red]\n\n"
                "Start with: [bold]cell0ctl start[/bold]\n"
                "Or run setup: [bold]cell0ctl setup[/bold]",
                title="[bold red]Cell 0 Daemon Status[/bold red]",
                border_style="red",
                padding=(1, 2)
            ))
        
        console.print()
    
    def cmd_setup(self, args: argparse.Namespace = None):
        """Interactive first-run setup wizard"""
        console.print()
        console.print(Panel(
            "[bold blue]Welcome to Cell 0 OS Setup[/bold blue]\n"
            "This wizard will help you configure Cell 0 for first use.",
            border_style="blue",
            padding=(1, 2)
        ))
        
        # Check prerequisites
        console.print("\n[bold]Checking Prerequisites...[/bold]")
        
        checks = []
        
        # Python version
        py_version = sys.version_info
        py_ok = py_version >= (3, 9)
        checks.append(("Python 3.9+", py_ok, f"{py_version.major}.{py_version.minor}.{py_version.micro}"))
        
        # Cell 0 home
        cell0_home = self.cell0_home
        cell0_exists = cell0_home.exists()
        checks.append(("Cell 0 Installation", cell0_exists, str(cell0_home)))
        
        # Virtual environment
        venv_python = self._get_venv_python()
        venv_ok = venv_python != Path(sys.executable)
        checks.append(("Virtual Environment", venv_ok, str(venv_python)))
        
        # Rich library
        checks.append(("Rich Library", HAS_RICH, "installed" if HAS_RICH else "missing"))
        
        if HAS_RICH:
            check_table = Table(box=box.SIMPLE)
            check_table.add_column("Component")
            check_table.add_column("Status", justify="center")
            check_table.add_column("Details")
            
            for name, ok, detail in checks:
                status = "[green]✓[/green]" if ok else "[red]✗[/red]"
                check_table.add_row(name, status, detail)
            
            console.print(check_table)
        else:
            for name, ok, detail in checks:
                status = "OK" if ok else "FAIL"
                print(f"[{status}] {name}: {detail}")
        
        # Configuration
        console.print("\n[bold]Configuration[/bold]")
        
        if HAS_RICH:
            # Interactive prompts
            cell0_path = Prompt.ask(
                "Cell 0 installation path",
                default=str(self.cell0_home)
            )
            self.cell0_home = Path(cell0_path).expanduser().resolve()
            
            env = Prompt.ask(
                "Environment",
                choices=["development", "staging", "production"],
                default="development"
            )
            
            log_level = Prompt.ask(
                "Log level",
                choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                default="INFO"
            )
            
            enable_channels = Confirm.ask(
                "Enable messaging channels?",
                default=False
            )
        else:
            # Non-interactive fallback
            cell0_path = input(f"Cell 0 path [{self.cell0_home}]: ").strip()
            if cell0_path:
                self.cell0_home = Path(cell0_path).expanduser()
            env = input("Environment (development/staging/production) [development]: ").strip() or "development"
            log_level = input("Log level (DEBUG/INFO/WARNING/ERROR) [INFO]: ").strip() or "INFO"
            enable_channels = input("Enable channels? (y/n) [n]: ").strip().lower() == 'y'
        
        # Progress bar for setup
        if HAS_RICH:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Setting up Cell 0...", total=4)
                
                # Create state directory
                progress.update(task, advance=1, description="Creating state directory...")
                self.state_dir.mkdir(parents=True, exist_ok=True)
                (self.state_dir / "logs").mkdir(exist_ok=True)
                time.sleep(0.5)
                
                # Save configuration
                progress.update(task, advance=1, description="Saving configuration...")
                self.config.set("cell0_home", str(self.cell0_home))
                self.config.set("environment", env)
                self.config.set("log_level", log_level)
                self.config.set("channels_enabled", enable_channels)
                self.config.set("setup_complete", True)
                self.config.set("setup_date", datetime.now().isoformat())
                self.config.save()
                time.sleep(0.5)
                
                # Create necessary directories
                progress.update(task, advance=1, description="Creating directories...")
                (self.state_dir / "tpv").mkdir(exist_ok=True)
                (self.state_dir / "agents").mkdir(exist_ok=True)
                time.sleep(0.5)
                
                # Finalize
                progress.update(task, advance=1, description="Finalizing...")
                time.sleep(0.5)
        else:
            print("Setting up Cell 0...")
            self.state_dir.mkdir(parents=True, exist_ok=True)
            (self.state_dir / "logs").mkdir(exist_ok=True)
            
            self.config.set("cell0_home", str(self.cell0_home))
            self.config.set("environment", env)
            self.config.set("log_level", log_level)
            self.config.set("channels_enabled", enable_channels)
            self.config.set("setup_complete", True)
            self.config.set("setup_date", datetime.now().isoformat())
            self.config.save()
            
            (self.state_dir / "tpv").mkdir(exist_ok=True)
            (self.state_dir / "agents").mkdir(exist_ok=True)
        
        # Success message
        console.print()
        console.print(Panel(
            "[bold green]✓ Setup Complete![/bold green]\n\n"
            "Cell 0 OS has been configured.\n\n"
            "Next steps:\n"
            "  • Start the daemon: [bold]cell0ctl start[/bold]\n"
            "  • Check status: [bold]cell0ctl status[/bold]\n"
            "  • View health: [bold]cell0ctl health[/bold]",
            border_style="green",
            padding=(1, 2)
        ))
        console.print()
    
    def cmd_health(self, args: argparse.Namespace = None):
        """Show health dashboard with component status grid"""
        console.print()
        
        # Check daemon status first
        daemon_status = self._check_daemon_running()
        
        if not daemon_status.running:
            console.print(Panel(
                "[red]● Daemon is not running[/red]\n"
                "Start the daemon to see health information.",
                title="[bold red]Health Dashboard[/bold red]",
                border_style="red"
            ))
            return
        
        # Try to get health from API
        try:
            import urllib.request
            with urllib.request.urlopen(
                f"{self.api_url}/health/deep", timeout=10
            ) as resp:
                health_data = json.loads(resp.read())
                
                # Overall status
                overall = health_data.get("status", "unknown")
                version = health_data.get("version", VERSION)
                timestamp = health_data.get("timestamp", "unknown")
                
                # Status color mapping
                status_colors = {
                    "healthy": "green",
                    "degraded": "yellow",
                    "unhealthy": "red",
                    "unknown": "dim"
                }
                status_color = status_colors.get(overall, "white")
                status_symbol = "●" if overall == "healthy" else "⚠" if overall == "degraded" else "✗"
                
                # Header
                header_text = (
                    f"[bold {status_color}]{status_symbol} Overall: {overall.upper()}[/bold {status_color}]\n"
                    f"Version: {version}\n"
                    f"Timestamp: {timestamp}"
                )
                
                console.print(Panel(
                    header_text,
                    title="[bold blue]Cell 0 Health Dashboard[/bold blue]",
                    border_style=status_color,
                    padding=(1, 2)
                ))
                
                # Component status grid
                components = health_data.get("components", {})
                if components and HAS_RICH:
                    console.print("\n[bold]Component Status[/bold]\n")
                    
                    # Create columns for components
                    comp_tables = []
                    for comp_name, comp_data in components.items():
                        comp_status = comp_data.get("status", "unknown")
                        comp_message = comp_data.get("message", "No message")
                        comp_latency = comp_data.get("latency_ms", 0)
                        
                        comp_color = status_colors.get(comp_status, "white")
                        comp_symbol = "●"
                        
                        comp_table = Table(
                            box=box.ROUNDED,
                            show_header=False,
                            padding=(0, 1)
                        )
                        comp_table.add_column(style="cyan")
                        comp_table.add_column()
                        
                        comp_table.add_row(
                            f"[{comp_color}]{comp_symbol}[/{comp_color}] {comp_name.title()}",
                            f"[{comp_color}]{comp_status.upper()}[/{comp_color}]"
                        )
                        comp_table.add_row("", comp_message, style="dim")
                        if comp_latency:
                            comp_table.add_row("", f"Latency: {comp_latency:.1f}ms", style="dim")
                        
                        comp_tables.append(comp_table)
                    
                    # Display in columns
                    if len(comp_tables) <= 2:
                        console.print(Columns(comp_tables))
                    else:
                        # Split into rows
                        mid = (len(comp_tables) + 1) // 2
                        for i in range(0, len(comp_tables), 2):
                            row_tables = comp_tables[i:i+2]
                            console.print(Columns(row_tables))
                            console.print()
                
                elif components:
                    # Plain text fallback
                    print("\nComponents:")
                    for comp_name, comp_data in components.items():
                        print(f"  {comp_name}: {comp_data.get('status')} - {comp_data.get('message')}")
                
                # Recent events summary
                console.print("\n[bold]Recent Events[/bold]\n")
                errors = self._get_recent_errors(3)
                if errors:
                    for i, error in enumerate(errors, 1):
                        console.print(f"  [red]{i}.[/red] {error[:100]}...")
                else:
                    console.print("  [green]No recent errors[/green]")
                
        except Exception as e:
            console.print(Panel(
                f"[yellow]Could not fetch health data: {e}[/yellow]\n"
                "The daemon may be starting up or health checks are not available.",
                title="[bold yellow]Health Dashboard[/bold yellow]",
                border_style="yellow"
            ))
        
        console.print()
    
    def cmd_logs(self, args: argparse.Namespace):
        """View logs with filtering options"""
        log_dir = self.state_dir / "logs"
        log_file = log_dir / "cell0d.log"
        
        if not log_file.exists():
            console.print(f"[yellow]Log file not found: {log_file}[/yellow]")
            return
        
        if args.follow:
            # Follow mode
            console.print(f"[dim]Following logs (Ctrl+C to exit)...[/dim]\n")
            try:
                # Use subprocess for real-time following
                if args.level:
                    # Filter by level in follow mode using grep
                    proc = subprocess.Popen(
                        ["tail", "-f", str(log_file)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    try:
                        for line in proc.stdout:
                            entry = self._parse_log_line(line)
                            if entry.level.upper() == args.level.upper():
                                self._print_log_entry(entry)
                    except KeyboardInterrupt:
                        proc.terminate()
                else:
                    subprocess.run(["tail", "-f", str(log_file)])
            except KeyboardInterrupt:
                console.print("\n[dim]Stopped following logs[/dim]")
            return
        
        # Read and filter logs
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            # Parse all entries
            entries = [self._parse_log_line(line) for line in lines]
            
            # Apply filters
            if args.level:
                entries = [e for e in entries if e.level.upper() == args.level.upper()]
            
            if args.since:
                # Parse duration (e.g., "1h", "30m", "1d")
                since_delta = self._parse_duration(args.since)
                if since_delta:
                    cutoff = datetime.now() - since_delta
                    entries = [
                        e for e in entries 
                        if e.timestamp and e.timestamp >= cutoff
                    ]
            
            # Apply line limit
            limit = args.lines or 50
            entries = entries[-limit:]
            
            if not entries:
                console.print("[yellow]No log entries matching the filters[/yellow]")
                return
            
            # Display logs
            if HAS_RICH and not args.no_color:
                console.print(f"\n[dim]Showing {len(entries)} log entries:[/dim]\n")
                
                for entry in entries:
                    self._print_log_entry(entry)
            else:
                for entry in entries:
                    print(entry.raw_line)
                    
        except Exception as e:
            console.print(f"[red]Error reading logs: {e}[/red]")
    
    def _print_log_entry(self, entry: LogEntry):
        """Print a single log entry with color formatting"""
        # Color mapping for log levels
        level_colors = {
            "DEBUG": "dim",
            "INFO": "blue",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold red"
        }
        
        level_color = level_colors.get(entry.level.upper(), "white")
        
        # Format timestamp
        ts_str = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else "--:--:--"
        
        # Format the entry
        console.print(
            f"[dim]{ts_str}[/dim] "
            f"[{level_color}]{entry.level:8}[/{level_color}] "
            f"[cyan]{entry.logger:20}[/cyan] "
            f"{entry.message[:200]}"
        )
    
    def _parse_duration(self, duration_str: str) -> Optional[timedelta]:
        """Parse duration string like '1h', '30m', '1d' into timedelta"""
        match = re.match(r'(\d+)([hmd])', duration_str.lower())
        if not match:
            return None
        
        value = int(match.group(1))
        unit = match.group(2)
        
        if unit == 'h':
            return timedelta(hours=value)
        elif unit == 'm':
            return timedelta(minutes=value)
        elif unit == 'd':
            return timedelta(days=value)
        
        return None
    
    def cmd_start(self, args: argparse.Namespace):
        """Start the daemon"""
        status = self._check_daemon_running()
        if status.running:
            console.print(f"[yellow]Daemon already running (PID: {status.pid})[/yellow]")
            return
        
        # Check prerequisites
        if not self._check_prerequisites():
            return
        
        console.print("[green]Starting Cell 0 daemon...[/green]")
        
        venv_python = self._get_venv_python()
        daemon_path = self.cell0_home / "cell0d.py"
        
        if not daemon_path.exists():
            console.print(f"[red]Daemon not found at {daemon_path}[/red]")
            return
        
        # Set environment variables
        env = os.environ.copy()
        env["CELL0_HOME"] = str(self.cell0_home)
        env["CELL0_STATE_DIR"] = str(self.state_dir)
        env["CELL0_ENV"] = args.env or self.config.get("environment", "production")
        env["CELL0_LOG_LEVEL"] = args.log_level or self.config.get("log_level", "INFO")
        
        if args.detach:
            # Start in background
            process = subprocess.Popen(
                [str(venv_python), str(daemon_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                start_new_session=True
            )
            self._write_pid(process.pid)
            console.print(f"[green]Daemon started in background (PID: {process.pid})[/green]")
            
            # Wait a moment and check if it's still running
            time.sleep(2)
            status = self._check_daemon_running()
            if status.running:
                console.print(f"[green]✓ Daemon is healthy on port {status.port}[/green]")
            else:
                console.print("[red]✗ Daemon failed to start. Check logs with: cell0ctl logs[/red]")
        else:
            # Start in foreground
            console.print("[dim]Running in foreground mode. Press Ctrl+C to stop.[/dim]\n")
            try:
                process = subprocess.run(
                    [str(venv_python), str(daemon_path)],
                    env=env
                )
            except KeyboardInterrupt:
                console.print("\n[yellow]Shutdown requested[/yellow]")
    
    def cmd_stop(self, args: argparse.Namespace):
        """Stop the daemon"""
        status = self._check_daemon_running()
        if not status.running:
            console.print("[yellow]Daemon is not running[/yellow]")
            return
        
        console.print(f"[yellow]Stopping daemon (PID: {status.pid})...[/yellow]")
        
        try:
            if args.force:
                os.kill(status.pid, signal.SIGKILL)
            else:
                os.kill(status.pid, signal.SIGTERM)
            
            # Wait for process to stop
            for _ in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                try:
                    os.kill(status.pid, 0)
                except OSError:
                    break
            else:
                console.print("[red]Daemon did not stop gracefully, forcing...[/red]")
                try:
                    os.kill(status.pid, signal.SIGKILL)
                except OSError:
                    pass
            
            self._remove_pid()
            console.print("[green]Daemon stopped[/green]")
            
        except ProcessLookupError:
            console.print("[yellow]Process already terminated[/yellow]")
            self._remove_pid()
        except Exception as e:
            console.print(f"[red]Error stopping daemon: {e}[/red]")
    
    def cmd_restart(self, args: argparse.Namespace):
        """Restart the daemon"""
        self.cmd_stop(args)
        time.sleep(1)
        self.cmd_start(args)
    
    def cmd_doctor(self, args: argparse.Namespace):
        """Run diagnostics"""
        console.print(Panel("Cell 0 System Diagnostics", border_style="blue"))
        
        checks = []
        all_passed = True
        
        # Check Python version
        py_version = sys.version_info
        py_ok = py_version >= (3, 9)
        checks.append(("Python Version", f"{py_version.major}.{py_version.minor}.{py_version.micro}", py_ok))
        all_passed = all_passed and py_ok
        
        # Check Cell 0 installation
        cell0_exists = self.cell0_home.exists()
        checks.append(("Cell 0 Installation", str(self.cell0_home), cell0_exists))
        all_passed = all_passed and cell0_exists
        
        # Check venv
        venv_python = self._get_venv_python()
        venv_ok = venv_python != Path(sys.executable)
        checks.append(("Virtual Environment", str(venv_python), venv_ok))
        
        # Check daemon file
        daemon_exists = (self.cell0_home / "cell0d.py").exists()
        checks.append(("Daemon File", "cell0d.py", daemon_exists))
        all_passed = all_passed and daemon_exists
        
        # Check state directory
        state_ok = self.state_dir.exists() or self.state_dir.parent.exists()
        checks.append(("State Directory", str(self.state_dir), state_ok))
        
        # Check port availability
        port_ok = self._check_port_available(DEFAULT_PORT)
        checks.append(("Port 18800", "Available" if port_ok else "In Use", port_ok))
        
        # Check daemon status
        status = self._check_daemon_running()
        checks.append(("Daemon Status", "Running" if status.running else "Stopped", True))
        
        # Check config
        config_exists = self.config.exists()
        checks.append(("Configuration", "Exists" if config_exists else "Missing", config_exists))
        
        # Display results
        if HAS_RICH:
            table = Table()
            table.add_column("Check")
            table.add_column("Value")
            table.add_column("Status")
            
            for name, value, passed in checks:
                status_icon = "✅" if passed else "❌"
                table.add_row(name, value, status_icon)
            
            console.print(table)
        else:
            for name, value, passed in checks:
                status = "PASS" if passed else "FAIL"
                print(f"[{status}] {name}: {value}")
        
        if all_passed:
            console.print("\n[green]✓ All critical checks passed[/green]")
        else:
            console.print("\n[red]✗ Some checks failed[/red]")
            if not config_exists:
                console.print("\nRun [bold]cell0ctl setup[/bold] to configure Cell 0")
    
    def _check_prerequisites(self) -> bool:
        """Check if prerequisites are met"""
        # Check cell0 home exists
        if not self.cell0_home.exists():
            console.print(f"[red]Cell 0 home not found: {self.cell0_home}[/red]")
            console.print("[yellow]Run setup first: cell0ctl setup[/yellow]")
            return False
        
        # Check if first run
        if self.config.is_first_run():
            console.print("[yellow]First run detected. Running setup...[/yellow]")
            self.cmd_setup()
            return True
        
        # Check venv exists
        venv_python = self._get_venv_python()
        if venv_python == Path(sys.executable):
            console.print("[yellow]Warning: Virtual environment not found, using system Python[/yellow]")
        
        return True
    
    def _check_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return True
        except socket.error:
            return False
    
    def cmd_agent(self, args: argparse.Namespace):
        """Agent management commands"""
        if args.agent_command == "list":
            try:
                import urllib.request
                with urllib.request.urlopen(
                    f"{self.api_url}/api/agents", timeout=5
                ) as resp:
                    agents = json.loads(resp.read())
                    
                    if HAS_RICH:
                        table = Table(title="Active Agents")
                        table.add_column("ID")
                        table.add_column("Type")
                        table.add_column("Status")
                        
                        for agent in agents:
                            table.add_row(
                                agent.get("id", "unknown"),
                                agent.get("type", "unknown"),
                                agent.get("status", "unknown")
                            )
                        
                        console.print(table)
                    else:
                        for agent in agents:
                            print(f"{agent.get('id')}: {agent.get('type')} ({agent.get('status')})")
            except Exception as e:
                console.print(f"[red]Failed to fetch agents: {e}[/red]")
        
        elif args.agent_command == "restart":
            if not args.agent_id:
                console.print("[red]Agent ID required[/red]")
                return
            
            try:
                import urllib.request
                req = urllib.request.Request(
                    f"{self.api_url}/api/agents/{args.agent_id}/restart",
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    result = json.loads(resp.read())
                    console.print(f"[green]Agent {args.agent_id} restarted[/green]")
            except Exception as e:
                console.print(f"[red]Failed to restart agent: {e}[/red]")
    
    def cmd_config(self, args: argparse.Namespace):
        """Configuration management"""
        if args.config_command == "show":
            if self.config.exists():
                config_data = {}
                # Load and display
                try:
                    with open(CONFIG_FILE, 'r') as f:
                        config_data = json.load(f)
                    
                    if HAS_RICH:
                        table = Table(title="Cell 0 Configuration")
                        table.add_column("Key", style="cyan")
                        table.add_column("Value")
                        
                        for key, value in config_data.items():
                            table.add_row(key, str(value))
                        
                        console.print(table)
                    else:
                        print(json.dumps(config_data, indent=2))
                except Exception as e:
                    console.print(f"[red]Error reading config: {e}[/red]")
            else:
                console.print("[yellow]No configuration file found[/yellow]")
                console.print("Run: cell0ctl setup")
        
        elif args.config_command == "set":
            if not args.key or not args.value:
                console.print("[red]Usage: cell0ctl config set <key> <value>[/red]")
                return
            
            self.config.set(args.key, args.value)
            self.config.save()
            console.print(f"[green]Set {args.key} = {args.value}[/green]")
        
        elif args.config_command == "get":
            if not args.key:
                console.print("[red]Usage: cell0ctl config get <key>[/red]")
                return
            
            value = self.config.get(args.key)
            if value is not None:
                console.print(f"{args.key} = {value}")
            else:
                console.print(f"[yellow]Key '{args.key}' not found[/yellow]")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        prog="cell0ctl",
        description="Cell 0 OS Command Line Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    cell0ctl status              # Check daemon status (default)
    cell0ctl start               # Start daemon in foreground
    cell0ctl start --detach      # Start daemon in background
    cell0ctl stop                # Stop daemon
    cell0ctl logs --follow       # Follow logs in real-time
    cell0ctl logs --since 1h     # Show logs from last hour
    cell0ctl logs --level ERROR  # Show only error logs
    cell0ctl health              # Show health dashboard
    cell0ctl doctor              # Run diagnostics
    cell0ctl setup               # First-run configuration
    cell0ctl agent list          # List agents
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Status command (default)
    status_parser = subparsers.add_parser("status", help="Show system status")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="First-run configuration wizard")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the daemon")
    start_parser.add_argument("--detach", "-d", action="store_true", help="Run in background")
    start_parser.add_argument("--env", choices=["development", "staging", "production"], 
                             help="Environment")
    start_parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                             help="Logging level")
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop the daemon")
    stop_parser.add_argument("--force", "-f", action="store_true", help="Force kill")
    
    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart the daemon")
    restart_parser.add_argument("--force", "-f", action="store_true", help="Force restart")
    restart_parser.add_argument("--detach", "-d", action="store_true", help="Run in background")
    
    # Logs command
    logs_parser = subparsers.add_parser("logs", help="View logs with filtering")
    logs_parser.add_argument("--follow", "-f", action="store_true", help="Follow logs")
    logs_parser.add_argument("--lines", "-n", type=int, default=50, help="Number of lines")
    logs_parser.add_argument("--since", help="Show logs since duration (e.g., 1h, 30m, 1d)")
    logs_parser.add_argument("--level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                            help="Filter by log level")
    logs_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    
    # Health command
    health_parser = subparsers.add_parser("health", help="Show health dashboard")
    
    # Doctor command
    doctor_parser = subparsers.add_parser("doctor", help="Run diagnostics")
    doctor_parser.add_argument("--fix", action="store_true", help="Attempt to fix issues")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_subparsers = config_parser.add_subparsers(dest="config_command")
    config_subparsers.add_parser("show", help="Show configuration")
    set_parser = config_subparsers.add_parser("set", help="Set configuration value")
    set_parser.add_argument("key", help="Configuration key")
    set_parser.add_argument("value", help="Configuration value")
    get_parser = config_subparsers.add_parser("get", help="Get configuration value")
    get_parser.add_argument("key", help="Configuration key")
    
    # Agent command
    agent_parser = subparsers.add_parser("agent", help="Agent management")
    agent_subparsers = agent_parser.add_subparsers(dest="agent_command")
    agent_subparsers.add_parser("list", help="List agents")
    restart_agent_parser = agent_subparsers.add_parser("restart", help="Restart an agent")
    restart_agent_parser.add_argument("agent_id", help="Agent ID to restart")
    
    args = parser.parse_args()
    
    ctl = Cell0CTL()
    
    # Check for first run and auto-run setup
    if not args.command and ctl.config.is_first_run():
        console.print("[yellow]First run detected. Starting setup wizard...[/yellow]")
        ctl.cmd_setup()
        return
    
    # Default to status if no command given
    if not args.command:
        args.command = "status"
    
    commands = {
        "status": ctl.cmd_status,
        "setup": ctl.cmd_setup,
        "start": ctl.cmd_start,
        "stop": ctl.cmd_stop,
        "restart": ctl.cmd_restart,
        "logs": ctl.cmd_logs,
        "health": ctl.cmd_health,
        "doctor": ctl.cmd_doctor,
        "config": ctl.cmd_config,
        "agent": ctl.cmd_agent,
    }
    
    if args.command in commands:
        try:
            commands[args.command](args)
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
            sys.exit(130)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()