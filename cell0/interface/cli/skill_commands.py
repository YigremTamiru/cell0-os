"""
Skill CLI Commands for Cell 0 OS

Provides CLI commands for managing skills via cell0ctl.

Usage:
    cell0ctl skill list              # List all skills
    cell0ctl skill list --enabled    # List only enabled skills
    cell0ctl skill info <skill>      # Show skill details
    cell0ctl skill enable <skill>    # Enable a skill
    cell0ctl skill disable <skill>   # Disable a skill
    cell0ctl skill install <path>    # Install a skill
    cell0ctl skill uninstall <skill> # Uninstall a skill
    cell0ctl skill create <name>     # Create a new skill template
"""

import argparse
import asyncio
import json
import shutil
import sys
from pathlib import Path
from typing import Optional

from cell0.engine.skills import (
    get_manager,
    get_loader,
    SkillStatus,
    SkillType,
    SkillManagerError
)


def format_status(status: SkillStatus) -> str:
    """Format skill status with color indicators"""
    colors = {
        SkillStatus.DISCOVERED: "\033[90m",   # Gray
        SkillStatus.LOADED: "\033[94m",       # Blue
        SkillStatus.ENABLED: "\033[92m",      # Green
        SkillStatus.DISABLED: "\033[93m",     # Yellow
        SkillStatus.ERROR: "\033[91m",        # Red
        SkillStatus.UNLOADED: "\033[90m",     # Gray
    }
    reset = "\033[0m"
    color = colors.get(status, "")
    return f"{color}{status.value.upper()}{reset}"


def format_skill_type(skill_type: SkillType) -> str:
    """Format skill type"""
    icons = {
        SkillType.SYSTEM: "⚙️ ",
        SkillType.WORKSPACE: "📁",
        SkillType.INSTALLED: "📦",
    }
    return f"{icons.get(skill_type, '?')} {skill_type.value}"


async def cmd_list(args: argparse.Namespace) -> int:
    """List all skills"""
    try:
        manager = get_manager()
        
        # Filter by status if specified
        status_filter = None
        if args.enabled:
            status_filter = SkillStatus.ENABLED
        elif args.disabled:
            status_filter = SkillStatus.DISABLED
        
        skills = manager.list_skills(status=status_filter)
        
        if not skills:
            print("No skills found.")
            return 0
        
        # Print header
        print(f"\n{'ID':<30} {'Type':<12} {'Version':<10} {'Status':<10} {'Name'}")
        print("-" * 80)
        
        # Print skills
        for skill in skills:
            status = manager.get_skill_status(skill.full_id)
            print(
                f"{skill.full_id:<30} "
                f"{skill.skill_type.value:<12} "
                f"{skill.version:<10} "
                f"{format_status(status):<20} "
                f"{skill.name}"
            )
        
        print(f"\nTotal: {len(skills)} skill(s)")
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def cmd_info(args: argparse.Namespace) -> int:
    """Show detailed information about a skill"""
    try:
        manager = get_manager()
        skill = manager.get_skill(args.skill_id)
        
        if not skill:
            print(f"Skill not found: {args.skill_id}", file=sys.stderr)
            return 1
        
        status = manager.get_skill_status(args.skill_id)
        
        print(f"\n{'='*60}")
        print(f"  {skill.name}")
        print(f"{'='*60}")
        print(f"  ID:          {skill.full_id}")
        print(f"  Version:     {skill.version}")
        print(f"  Status:      {format_status(status)}")
        print(f"  Type:        {format_skill_type(skill.skill_type)}")
        print(f"  Path:        {skill.path}")
        print(f"  Author:      {skill.author or 'N/A'}")
        print(f"  License:     {skill.license}")
        
        if skill.description:
            print(f"\n  Description:")
            print(f"    {skill.description}")
        
        if skill.dependencies:
            print(f"\n  Dependencies:")
            for dep in skill.dependencies:
                opt = " (optional)" if dep.optional else ""
                print(f"    • {dep.skill_id} {dep.version_range}{opt}")
        
        if skill.tools:
            print(f"\n  Tools ({len(skill.tools)}):")
            for tool in skill.tools:
                print(f"    • {tool.name} - {tool.description}")
        
        if skill.commands:
            print(f"\n  Commands ({len(skill.commands)}):")
            for cmd in skill.commands:
                aliases = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
                print(f"    • {cmd.name}{aliases} - {cmd.description}")
        
        if skill.events:
            print(f"\n  Event Handlers ({len(skill.events)}):")
            for evt in skill.events:
                print(f"    • {evt.event_type} (priority: {evt.priority})")
        
        print(f"{'='*60}\n")
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def cmd_enable(args: argparse.Namespace) -> int:
    """Enable a skill"""
    try:
        manager = get_manager()
        
        # Load skill first if not loaded
        await manager.load_skill(args.skill_id)
        
        # Enable
        success = await manager.enable_skill(args.skill_id)
        
        if success:
            print(f"✓ Skill enabled: {args.skill_id}")
            return 0
        else:
            print(f"✗ Failed to enable skill: {args.skill_id}", file=sys.stderr)
            return 1
            
    except SkillManagerError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def cmd_disable(args: argparse.Namespace) -> int:
    """Disable a skill"""
    try:
        manager = get_manager()
        success = await manager.disable_skill(args.skill_id)
        
        if success:
            print(f"✓ Skill disabled: {args.skill_id}")
            return 0
        else:
            print(f"✗ Failed to disable skill: {args.skill_id}", file=sys.stderr)
            return 1
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def cmd_install(args: argparse.Namespace) -> int:
    """Install a skill from a directory"""
    try:
        source_path = Path(args.source).expanduser().resolve()
        
        if not source_path.exists():
            print(f"Source path not found: {source_path}", file=sys.stderr)
            return 1
        
        # Check for skill.yaml
        manifest_path = source_path / "skill.yaml"
        if not manifest_path.exists():
            print(f"No skill.yaml found in {source_path}", file=sys.stderr)
            return 1
        
        # Parse manifest to get skill ID
        import yaml
        with open(manifest_path) as f:
            manifest_data = yaml.safe_load(f)
        
        skill_id = manifest_data.get('id')
        if not skill_id:
            print("Invalid skill.yaml: missing 'id' field", file=sys.stderr)
            return 1
        
        # Determine target path
        manager = get_manager()
        if args.system:
            target_path = manager.system_path / skill_id
        elif args.workspace:
            target_path = manager.workspace_path / skill_id
        else:
            target_path = manager.installed_path / skill_id
        
        if target_path.exists() and not args.force:
            print(f"Skill already installed at {target_path}", file=sys.stderr)
            print("Use --force to overwrite")
            return 1
        
        # Copy skill
        if target_path.exists():
            shutil.rmtree(target_path)
        
        shutil.copytree(source_path, target_path)
        
        print(f"✓ Installed skill '{skill_id}' to {target_path}")
        
        # Auto-enable if requested
        if args.enable:
            await manager.discover_all()
            full_id = f"{SkillType.INSTALLED.value}:{skill_id}"
            await cmd_enable(argparse.Namespace(skill_id=full_id))
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def cmd_uninstall(args: argparse.Namespace) -> int:
    """Uninstall a skill"""
    try:
        manager = get_manager()
        skill = manager.get_skill(args.skill_id)
        
        if not skill:
            print(f"Skill not found: {args.skill_id}", file=sys.stderr)
            return 1
        
        if not skill.path:
            print("Skill has no path information", file=sys.stderr)
            return 1
        
        # Disable first
        await manager.disable_skill(args.skill_id)
        
        # Unload
        await manager.unload_skill(args.skill_id)
        
        # Remove directory
        if skill.path.exists():
            shutil.rmtree(skill.path)
        
        print(f"✓ Uninstalled skill: {args.skill_id}")
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def cmd_create(args: argparse.Namespace) -> int:
    """Create a new skill template"""
    try:
        loader = get_loader()
        
        # Determine target directory
        if args.system:
            base_path = get_manager().system_path
        elif args.workspace:
            base_path = get_manager().workspace_path
        else:
            base_path = Path.cwd()
        
        skill_dir = loader.create_skill_template(args.name, args.name.replace('-', ' ').title(), base_path)
        
        print(f"✓ Created new skill template at {skill_dir}")
        print(f"\nNext steps:")
        print(f"  1. Edit {skill_dir / 'skill.yaml'}")
        print(f"  2. Implement your tools in {skill_dir / 'tools.py'}")
        print(f"  3. Add CLI commands in {skill_dir / 'cli.py'}")
        print(f"  4. Install with: cell0ctl skill install {skill_dir}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def cmd_stats(args: argparse.Namespace) -> int:
    """Show skill system statistics"""
    try:
        manager = get_manager()
        stats = manager.get_stats()
        
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"\n{'='*50}")
            print(f"  Skill System Statistics")
            print(f"{'='*50}")
            print(f"  Total Skills:   {stats['skills']}")
            print(f"  Registered Tools: {stats['tools']}")
            print(f"  CLI Commands:   {stats['commands']}")
            print(f"  Event Types:    {stats['event_types']}")
            print(f"\n  Status Breakdown:")
            for status, count in stats['status_breakdown'].items():
                if count > 0:
                    print(f"    {status}: {count}")
            print(f"\n  Paths:")
            print(f"    System:    {stats['paths']['system']}")
            print(f"    Workspace: {stats['paths']['workspace']}")
            print(f"    Installed: {stats['paths']['installed']}")
            print(f"{'='*50}\n")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def cmd_discover(args: argparse.Namespace) -> int:
    """Rediscover skills from filesystem"""
    try:
        manager = get_manager()
        skills = await manager.discover_all()
        
        print(f"✓ Discovered {len(skills)} skill(s)")
        for skill in skills:
            print(f"  • {skill.full_id} ({skill.version})")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for skill CLI commands"""
    parser = argparse.ArgumentParser(
        prog='cell0ctl skill',
        description='Manage Cell 0 OS skills'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all skills')
    list_parser.add_argument('--enabled', action='store_true', help='Show only enabled skills')
    list_parser.add_argument('--disabled', action='store_true', help='Show only disabled skills')
    list_parser.set_defaults(func=cmd_list)
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show skill details')
    info_parser.add_argument('skill_id', help='Skill ID (e.g., workspace:my_skill)')
    info_parser.set_defaults(func=cmd_info)
    
    # Enable command
    enable_parser = subparsers.add_parser('enable', help='Enable a skill')
    enable_parser.add_argument('skill_id', help='Skill ID to enable')
    enable_parser.set_defaults(func=cmd_enable)
    
    # Disable command
    disable_parser = subparsers.add_parser('disable', help='Disable a skill')
    disable_parser.add_argument('skill_id', help='Skill ID to disable')
    disable_parser.set_defaults(func=cmd_disable)
    
    # Install command
    install_parser = subparsers.add_parser('install', help='Install a skill from directory')
    install_parser.add_argument('source', help='Path to skill directory')
    install_parser.add_argument('--system', action='store_true', help='Install as system skill')
    install_parser.add_argument('--workspace', action='store_true', help='Install as workspace skill')
    install_parser.add_argument('--force', action='store_true', help='Overwrite existing')
    install_parser.add_argument('--enable', action='store_true', help='Enable after install')
    install_parser.set_defaults(func=cmd_install)
    
    # Uninstall command
    uninstall_parser = subparsers.add_parser('uninstall', help='Uninstall a skill')
    uninstall_parser.add_argument('skill_id', help='Skill ID to uninstall')
    uninstall_parser.set_defaults(func=cmd_uninstall)
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new skill template')
    create_parser.add_argument('name', help='Skill name (used as ID)')
    create_parser.add_argument('--system', action='store_true', help='Create in system path')
    create_parser.add_argument('--workspace', action='store_true', help='Create in workspace path')
    create_parser.set_defaults(func=cmd_create)
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show skill system statistics')
    stats_parser.add_argument('--json', action='store_true', help='Output as JSON')
    stats_parser.set_defaults(func=cmd_stats)
    
    # Discover command
    discover_parser = subparsers.add_parser('discover', help='Rediscover skills')
    discover_parser.set_defaults(func=cmd_discover)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return asyncio.run(args.func(args))


if __name__ == '__main__':
    sys.exit(main())
