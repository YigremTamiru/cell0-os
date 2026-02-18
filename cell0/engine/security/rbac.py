"""
cell0/engine/security/rbac.py - Role-Based Access Control System

Comprehensive RBAC implementation for Cell 0 OS:
- Hierarchical roles with inheritance
- Resource-based permissions
- Role assignments with time limits
- Dynamic permission checking
- Policy engine with rules

Features:
- Role definitions with inheritance trees
- Fine-grained permissions (resource:action)
- User-role bindings with expiration
- Permission evaluation with caching
- Policy rules engine
- Resource-level access control
"""

import fnmatch
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("cell0.security.rbac")

# ============================================================================
# Permission Definitions
# ============================================================================

class PermissionAction(Enum):
    """Standard permission actions"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    LIST = "list"
    ADMIN = "admin"


@dataclass(frozen=True)
class Permission:
    """
    A permission represents the ability to perform an action on a resource.
    
    Format: resource:action or resource:* (wildcard)
    Examples:
        - agents:create - create agents
        - agents:* - all actions on agents
        - *:read - read access to everything
    """
    resource: str
    action: str
    
    def __str__(self) -> str:
        return f"{self.resource}:{self.action}"
    
    @classmethod
    def from_string(cls, permission_str: str) -> "Permission":
        """Parse permission from string"""
        parts = permission_str.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid permission format: {permission_str}")
        return cls(resource=parts[0], action=parts[1])
    
    def matches(self, other: "Permission") -> bool:
        """Check if this permission matches another (supports wildcards)"""
        resource_match = self.resource == "*" or other.resource == "*" or self.resource == other.resource
        action_match = self.action == "*" or other.action == "*" or self.action == other.action
        return resource_match and action_match
    
    def implies(self, required: "Permission") -> bool:
        """Check if this permission implies the required permission"""
        # Wildcard resource
        if self.resource == "*":
            # *:admin implies everything
            if self.action == "admin":
                return True
            # *:action matches resource:action
            return self.action == required.action or self.action == "*"
        
        # Specific resource
        if self.resource != required.resource:
            return False
        
        # Wildcard action on resource
        if self.action == "*":
            return True
        
        # Specific action
        return self.action == required.action


# ============================================================================
# Role Definitions
# ============================================================================

@dataclass
class Role:
    """
    A role is a collection of permissions.
    
    Roles can inherit from other roles, creating a hierarchy.
    """
    id: str
    name: str
    description: str = ""
    permissions: Set[Permission] = field(default_factory=set)
    parent_roles: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_system: bool = False  # System roles cannot be deleted
    
    def add_permission(self, permission: Union[str, Permission]) -> None:
        """Add permission to role"""
        if isinstance(permission, str):
            permission = Permission.from_string(permission)
        self.permissions.add(permission)
    
    def remove_permission(self, permission: Union[str, Permission]) -> None:
        """Remove permission from role"""
        if isinstance(permission, str):
            permission = Permission.from_string(permission)
        self.permissions.discard(permission)
    
    def has_permission(self, permission: Union[str, Permission]) -> bool:
        """Check if role has specific permission (direct)"""
        if isinstance(permission, str):
            permission = Permission.from_string(permission)
        
        for p in self.permissions:
            if p.implies(permission):
                return True
        return False
    
    def add_parent(self, role_id: str) -> None:
        """Add parent role (inheritance)"""
        self.parent_roles.add(role_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "permissions": [str(p) for p in self.permissions],
            "parent_roles": list(self.parent_roles),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "is_system": self.is_system,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Role":
        """Create from dictionary"""
        role = cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            permissions={Permission.from_string(p) for p in data.get("permissions", [])},
            parent_roles=set(data.get("parent_roles", [])),
            metadata=data.get("metadata", {}),
            is_system=data.get("is_system", False),
        )
        if "created_at" in data:
            role.created_at = datetime.fromisoformat(data["created_at"])
        return role


# ============================================================================
# Predefined System Roles
# ============================================================================

def create_system_roles() -> Dict[str, Role]:
    """Create default system roles"""
    roles = {}
    
    # Super Admin - everything
    admin = Role(
        id="admin",
        name="Administrator",
        description="Full system access",
        is_system=True,
    )
    admin.add_permission("*:admin")
    roles["admin"] = admin
    
    # User Manager
    user_manager = Role(
        id="user_manager",
        name="User Manager",
        description="Manage users and roles",
        is_system=True,
    )
    user_manager.add_permission("users:*")
    user_manager.add_permission("roles:*")
    user_manager.add_parent("admin")
    roles["user_manager"] = user_manager
    
    # Operator - can run agents and view logs
    operator = Role(
        id="operator",
        name="Operator",
        description="Run agents and monitor system",
        is_system=True,
    )
    operator.add_permission("agents:*")
    operator.add_permission("tasks:*")
    operator.add_permission("logs:read")
    operator.add_permission("monitoring:read")
    roles["operator"] = operator
    
    # Developer - can create and modify agents
    developer = Role(
        id="developer",
        name="Developer",
        description="Create and modify agents",
        is_system=True,
    )
    developer.add_permission("agents:create")
    developer.add_permission("agents:read")
    developer.add_permission("agents:update")
    developer.add_permission("agents:execute")
    developer.add_permission("skills:*")
    developer.add_parent("operator")
    roles["developer"] = developer
    
    # Read Only
    readonly = Role(
        id="readonly",
        name="Read Only",
        description="View-only access",
        is_system=True,
    )
    readonly.add_permission("*:read")
    readonly.add_permission("*:list")
    roles["readonly"] = readonly
    
    # Service Account - for automated services
    service = Role(
        id="service",
        name="Service Account",
        description="For automated services and integrations",
        is_system=True,
    )
    service.add_permission("agents:read")
    service.add_permission("agents:execute")
    service.add_permission("tasks:*")
    service.add_permission("hooks:*")
    roles["service"] = service
    
    return roles


# ============================================================================
# Role Assignment
# ============================================================================

@dataclass
class RoleAssignment:
    """
    Assignment of a role to a user.
    
    Can have optional expiration time and conditions.
    """
    user_id: str
    role_id: str
    assigned_by: Optional[str] = None
    assigned_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if assignment has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_active(self) -> bool:
        """Check if assignment is currently active"""
        return not self.is_expired()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "role_id": self.role_id,
            "assigned_by": self.assigned_by,
            "assigned_at": self.assigned_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "conditions": self.conditions,
            "metadata": self.metadata,
            "is_active": self.is_active(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoleAssignment":
        """Create from dictionary"""
        assignment = cls(
            user_id=data["user_id"],
            role_id=data["role_id"],
            assigned_by=data.get("assigned_by"),
            conditions=data.get("conditions", {}),
            metadata=data.get("metadata", {}),
        )
        if "assigned_at" in data:
            assignment.assigned_at = datetime.fromisoformat(data["assigned_at"])
        if data.get("expires_at"):
            assignment.expires_at = datetime.fromisoformat(data["expires_at"])
        return assignment


# ============================================================================
# Resource Context
# ============================================================================

@dataclass
class ResourceContext:
    """
    Context for permission evaluation on a specific resource.
    
    Allows fine-grained access control based on resource attributes.
    """
    resource_type: str
    resource_id: Optional[str] = None
    owner_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def is_owner(self, user_id: str) -> bool:
        """Check if user is the resource owner"""
        return self.owner_id == user_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "owner_id": self.owner_id,
            "attributes": self.attributes,
        }


# ============================================================================
# RBAC Engine
# ============================================================================

class RBACError(Exception):
    """RBAC operation error"""
    pass


class RoleNotFoundError(RBACError):
    """Role does not exist"""
    pass


class PermissionDeniedError(RBACError):
    """Permission check failed"""
    pass


class CircularRoleError(RBACError):
    """Circular role inheritance detected"""
    pass


class RBACEngine:
    """
    Core RBAC engine with caching and policy evaluation.
    
    Features:
    - Role hierarchy resolution
    - Permission caching
    - Context-aware evaluation
    - Policy rules
    """
    
    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._assignments: Dict[str, Set[RoleAssignment]] = {}  # user_id -> assignments
        self._cache: Dict[str, Tuple[Set[Permission], float]] = {}  # cache with TTL
        self._cache_ttl: int = 300  # 5 minutes
        
        # Initialize system roles
        self._roles.update(create_system_roles())
        
        # Policy rules
        self._rules: List[Callable[[str, Permission, Optional[ResourceContext]], Optional[bool]]] = []
    
    # -------------------------------------------------------------------------
    # Role Management
    # -------------------------------------------------------------------------
    
    def create_role(
        self,
        id: str,
        name: str,
        description: str = "",
        permissions: Optional[List[str]] = None,
        parent_roles: Optional[List[str]] = None,
    ) -> Role:
        """Create a new role"""
        if id in self._roles:
            raise RBACError(f"Role already exists: {id}")
        
        role = Role(
            id=id,
            name=name,
            description=description,
            parent_roles=set(parent_roles or []),
        )
        
        if permissions:
            for p in permissions:
                role.add_permission(p)
        
        self._roles[id] = role
        self._invalidate_cache()
        logger.info(f"Created role: {id}")
        return role
    
    def get_role(self, role_id: str) -> Role:
        """Get role by ID"""
        if role_id not in self._roles:
            raise RoleNotFoundError(f"Role not found: {role_id}")
        return self._roles[role_id]
    
    def update_role(self, role_id: str, **updates) -> Role:
        """Update role attributes"""
        role = self.get_role(role_id)
        
        if role.is_system:
            raise RBACError(f"Cannot modify system role: {role_id}")
        
        for key, value in updates.items():
            if hasattr(role, key):
                setattr(role, key, value)
        
        self._invalidate_cache()
        logger.info(f"Updated role: {role_id}")
        return role
    
    def delete_role(self, role_id: str) -> None:
        """Delete a role"""
        if role_id not in self._roles:
            raise RoleNotFoundError(f"Role not found: {role_id}")
        
        role = self._roles[role_id]
        if role.is_system:
            raise RBACError(f"Cannot delete system role: {role_id}")
        
        # Remove from all parent references
        for r in self._roles.values():
            r.parent_roles.discard(role_id)
        
        del self._roles[role_id]
        self._invalidate_cache()
        logger.info(f"Deleted role: {role_id}")
    
    def list_roles(self) -> List[Role]:
        """List all roles"""
        return list(self._roles.values())
    
    # -------------------------------------------------------------------------
    # Permission Resolution
    # -------------------------------------------------------------------------
    
    def _resolve_role_permissions(self, role_id: str, visited: Optional[Set[str]] = None) -> Set[Permission]:
        """
        Resolve all permissions for a role including inherited ones.
        Detects circular inheritance.
        """
        if visited is None:
            visited = set()
        
        if role_id in visited:
            raise CircularRoleError(f"Circular role inheritance detected: {role_id}")
        
        visited.add(role_id)
        
        role = self._roles.get(role_id)
        if not role:
            return set()
        
        # Start with direct permissions
        all_permissions = set(role.permissions)
        
        # Add parent role permissions
        for parent_id in role.parent_roles:
            parent_perms = self._resolve_role_permissions(parent_id, visited.copy())
            all_permissions.update(parent_perms)
        
        return all_permissions
    
    def get_effective_permissions(self, user_id: str) -> Set[Permission]:
        """
        Get all effective permissions for a user.
        Cached for performance.
        """
        cache_key = f"user:{user_id}:perms"
        
        # Check cache
        if cache_key in self._cache:
            permissions, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return permissions
        
        # Resolve permissions
        permissions = set()
        assignments = self._assignments.get(user_id, set())
        
        for assignment in assignments:
            if assignment.is_active():
                role_perms = self._resolve_role_permissions(assignment.role_id)
                permissions.update(role_perms)
        
        # Cache result
        self._cache[cache_key] = (permissions, time.time())
        return permissions
    
    def check_permission(
        self,
        user_id: str,
        permission: Union[str, Permission],
        resource_context: Optional[ResourceContext] = None,
    ) -> bool:
        """
        Check if user has a specific permission.
        
        Supports context-aware evaluation through policy rules.
        """
        if isinstance(permission, str):
            permission = Permission.from_string(permission)
        
        # Run policy rules first (can allow or deny)
        for rule in self._rules:
            try:
                result = rule(user_id, permission, resource_context)
                if result is not None:
                    return result
            except Exception as e:
                logger.warning(f"Policy rule error: {e}")
        
        # Check owner access (owners get implicit read/update on their resources)
        if resource_context and resource_context.is_owner(user_id):
            if permission.action in ("read", "update"):
                return True
        
        # Check explicit permissions
        user_permissions = self.get_effective_permissions(user_id)
        
        for user_perm in user_permissions:
            if user_perm.implies(permission):
                return True
        
        return False
    
    def require_permission(
        self,
        user_id: str,
        permission: Union[str, Permission],
        resource_context: Optional[ResourceContext] = None,
    ) -> None:
        """Require permission, raise exception if denied"""
        if not self.check_permission(user_id, permission, resource_context):
            perm_str = permission if isinstance(permission, str) else str(permission)
            raise PermissionDeniedError(
                f"User {user_id} lacks required permission: {perm_str}"
            )
    
    # -------------------------------------------------------------------------
    # Role Assignments
    # -------------------------------------------------------------------------
    
    def assign_role(
        self,
        user_id: str,
        role_id: str,
        assigned_by: Optional[str] = None,
        expires_in: Optional[timedelta] = None,
        conditions: Optional[Dict[str, Any]] = None,
    ) -> RoleAssignment:
        """Assign role to user"""
        # Verify role exists
        self.get_role(role_id)
        
        expires_at = None
        if expires_in:
            expires_at = datetime.utcnow() + expires_in
        
        assignment = RoleAssignment(
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by,
            expires_at=expires_at,
            conditions=conditions or {},
        )
        
        if user_id not in self._assignments:
            self._assignments[user_id] = set()
        
        self._assignments[user_id].add(assignment)
        self._invalidate_cache_for_user(user_id)
        
        logger.info(f"Assigned role {role_id} to user {user_id}")
        return assignment
    
    def revoke_role(self, user_id: str, role_id: str) -> None:
        """Revoke role from user"""
        if user_id not in self._assignments:
            return
        
        self._assignments[user_id] = {
            a for a in self._assignments[user_id]
            if a.role_id != role_id
        }
        
        self._invalidate_cache_for_user(user_id)
        logger.info(f"Revoked role {role_id} from user {user_id}")
    
    def get_user_roles(self, user_id: str) -> List[Role]:
        """Get all active roles for a user"""
        if user_id not in self._assignments:
            return []
        
        roles = []
        for assignment in self._assignments[user_id]:
            if assignment.is_active():
                try:
                    role = self.get_role(assignment.role_id)
                    roles.append(role)
                except RoleNotFoundError:
                    pass
        
        return roles
    
    def get_user_assignments(self, user_id: str) -> List[RoleAssignment]:
        """Get all role assignments for a user"""
        if user_id not in self._assignments:
            return []
        return list(self._assignments[user_id])
    
    # -------------------------------------------------------------------------
    # Policy Rules
    # -------------------------------------------------------------------------
    
    def add_policy_rule(
        self,
        rule: Callable[[str, Permission, Optional[ResourceContext]], Optional[bool]]
    ) -> None:
        """
        Add a policy rule function.
        
        Rule should return:
        - True to allow access
        - False to deny access
        - None to defer to next rule/permission check
        """
        self._rules.append(rule)
    
    def add_owner_rule(self) -> None:
        """Add default owner rule (resource owners get full access)"""
        def owner_rule(
            user_id: str,
            permission: Permission,
            context: Optional[ResourceContext]
        ) -> Optional[bool]:
            if context and context.is_owner(user_id):
                # Owners get all permissions except admin
                if permission.action != "admin":
                    return True
            return None
        
        self.add_policy_rule(owner_rule)
    
    # -------------------------------------------------------------------------
    # Caching
    # -------------------------------------------------------------------------
    
    def _invalidate_cache(self) -> None:
        """Invalidate all permission caches"""
        self._cache.clear()
    
    def _invalidate_cache_for_user(self, user_id: str) -> None:
        """Invalidate cache for specific user"""
        keys_to_remove = [k for k in self._cache if k.startswith(f"user:{user_id}:")]
        for key in keys_to_remove:
            del self._cache[key]
    
    # -------------------------------------------------------------------------
    # Import/Export
    # -------------------------------------------------------------------------
    
    def export_roles(self) -> Dict[str, Any]:
        """Export all roles to dictionary"""
        return {
            "roles": {id: role.to_dict() for id, role in self._roles.items()},
            "assignments": {
                user_id: [a.to_dict() for a in assignments]
                for user_id, assignments in self._assignments.items()
            },
        }
    
    def import_roles(self, data: Dict[str, Any]) -> None:
        """Import roles from dictionary"""
        # Import roles
        for role_id, role_data in data.get("roles", {}).items():
            if role_id not in self._roles or not self._roles[role_id].is_system:
                self._roles[role_id] = Role.from_dict(role_data)
        
        # Import assignments
        for user_id, assignments_data in data.get("assignments", {}).items():
            self._assignments[user_id] = {
                RoleAssignment.from_dict(a) for a in assignments_data
            }
        
        self._invalidate_cache()
        logger.info("Imported RBAC data")


# ============================================================================
# Global RBAC Instance
# ============================================================================

_rbac_engine: Optional[RBACEngine] = None


def get_rbac_engine() -> RBACEngine:
    """Get global RBAC engine instance"""
    global _rbac_engine
    if _rbac_engine is None:
        _rbac_engine = RBACEngine()
        _rbac_engine.add_owner_rule()
    return _rbac_engine


def set_rbac_engine(engine: RBACEngine) -> None:
    """Set global RBAC engine instance"""
    global _rbac_engine
    _rbac_engine = engine


# ============================================================================
# Convenience Functions
# ============================================================================

def has_permission(
    user_id: str,
    permission: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    owner_id: Optional[str] = None,
) -> bool:
    """Quick permission check"""
    engine = get_rbac_engine()
    
    context = None
    if resource_type:
        context = ResourceContext(
            resource_type=resource_type,
            resource_id=resource_id,
            owner_id=owner_id,
        )
    
    return engine.check_permission(user_id, permission, context)


def require_permission(
    user_id: str,
    permission: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    owner_id: Optional[str] = None,
) -> None:
    """Quick permission requirement"""
    engine = get_rbac_engine()
    
    context = None
    if resource_type:
        context = ResourceContext(
            resource_type=resource_type,
            resource_id=resource_id,
            owner_id=owner_id,
        )
    
    engine.require_permission(user_id, permission, context)


def assign_role(
    user_id: str,
    role: str,
    assigned_by: Optional[str] = None,
    expires_in_days: Optional[int] = None,
) -> RoleAssignment:
    """Quick role assignment"""
    engine = get_rbac_engine()
    expires_in = None
    if expires_in_days:
        expires_in = timedelta(days=expires_in_days)
    return engine.assign_role(user_id, role, assigned_by, expires_in)


# ============================================================================
# Decorator for Permission Checking
# ============================================================================

def permission_required(permission: str):
    """Decorator to require permission on a function"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Try to get user_id from kwargs or first argument
            user_id = kwargs.get("user_id") or kwargs.get("requester")
            if not user_id and args:
                user_id = getattr(args[0], "user_id", None)
            
            if not user_id:
                raise PermissionDeniedError("No user_id found for permission check")
            
            require_permission(user_id, permission)
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# CLI Interface
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Cell 0 RBAC CLI")
    parser.add_argument("command", choices=["roles", "check", "export"])
    parser.add_argument("--user", help="User ID for permission check")
    parser.add_argument("--permission", help="Permission to check")
    parser.add_argument("--output", help="Output file for export")
    
    args = parser.parse_args()
    
    engine = get_rbac_engine()
    
    if args.command == "roles":
        print("System Roles:")
        for role in engine.list_roles():
            print(f"  {role.id}: {role.name}")
            print(f"    Permissions: {', '.join(str(p) for p in role.permissions)[:60]}...")
    
    elif args.command == "check":
        if not args.user or not args.permission:
            print("Error: --user and --permission required")
            exit(1)
        
        has = engine.check_permission(args.user, args.permission)
        print(f"User {args.user} has permission {args.permission}: {has}")
    
    elif args.command == "export":
        data = engine.export_roles()
        output = json.dumps(data, indent=2)
        if args.output:
            Path(args.output).write_text(output)
            print(f"Exported to {args.output}")
        else:
            print(output)
