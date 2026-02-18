"""
test_rbac.py - Unit tests for RBAC system
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add cell0 to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from cell0.engine.security.rbac import (
    PermissionAction,
    Permission,
    Role,
    RoleAssignment,
    ResourceContext,
    RBACError,
    RoleNotFoundError,
    PermissionDeniedError,
    CircularRoleError,
    RBACEngine,
    get_rbac_engine,
    set_rbac_engine,
    has_permission,
    require_permission,
    assign_role,
    create_system_roles,
)


class TestPermission:
    """Test Permission class"""
    
    def test_from_string(self):
        """Parse permission from string"""
        p = Permission.from_string("agents:create")
        assert p.resource == "agents"
        assert p.action == "create"
    
    def test_from_string_invalid(self):
        """Invalid format should raise error"""
        with pytest.raises(ValueError):
            Permission.from_string("invalid")
        
        with pytest.raises(ValueError):
            Permission.from_string("too:many:parts")
    
    def test_str(self):
        """String representation"""
        p = Permission(resource="agents", action="read")
        assert str(p) == "agents:read"
    
    def test_implies_exact(self):
        """Exact match implies"""
        p1 = Permission("agents", "read")
        p2 = Permission("agents", "read")
        assert p1.implies(p2)
    
    def test_implies_wildcard_resource(self):
        """Wildcard resource implies any resource"""
        p = Permission("*", "read")
        assert p.implies(Permission("agents", "read"))
        assert p.implies(Permission("tasks", "read"))
    
    def test_implies_wildcard_action(self):
        """Wildcard action implies any action on resource"""
        p = Permission("agents", "*")
        assert p.implies(Permission("agents", "read"))
        assert p.implies(Permission("agents", "create"))
        assert not p.implies(Permission("tasks", "read"))
    
    def test_implies_admin(self):
        """*:admin implies everything"""
        p = Permission("*", "admin")
        assert p.implies(Permission("anything", "anything"))
    
    def test_not_implies(self):
        """Non-matching permissions"""
        p = Permission("agents", "read")
        assert not p.implies(Permission("tasks", "read"))
        assert not p.implies(Permission("agents", "admin"))


class TestRole:
    """Test Role class"""
    
    def test_create_role(self):
        """Create basic role"""
        role = Role(
            id="test_role",
            name="Test Role",
            description="A test role",
        )
        
        assert role.id == "test_role"
        assert role.name == "Test Role"
        assert role.is_system is False
    
    def test_add_permission(self):
        """Add permission to role"""
        role = Role(id="test", name="Test")
        role.add_permission("agents:read")
        
        assert len(role.permissions) == 1
        assert role.has_permission("agents:read")
    
    def test_add_permission_string(self):
        """Add permission as string"""
        role = Role(id="test", name="Test")
        role.add_permission("agents:create")
        
        assert role.has_permission("agents:create")
    
    def test_remove_permission(self):
        """Remove permission from role"""
        role = Role(id="test", name="Test")
        role.add_permission("agents:read")
        role.remove_permission("agents:read")
        
        assert not role.has_permission("agents:read")
    
    def test_parent_roles(self):
        """Role inheritance"""
        role = Role(id="test", name="Test")
        role.add_parent("admin")
        
        assert "admin" in role.parent_roles
    
    def test_to_dict(self):
        """Serialize to dict"""
        role = Role(
            id="test",
            name="Test",
            description="Test role",
            is_system=True,
        )
        role.add_permission("agents:read")
        
        d = role.to_dict()
        assert d["id"] == "test"
        assert d["name"] == "Test"
        assert d["is_system"] is True
        assert "agents:read" in d["permissions"]
    
    def test_from_dict(self):
        """Deserialize from dict"""
        d = {
            "id": "test",
            "name": "Test",
            "description": "Test role",
            "permissions": ["agents:read", "tasks:create"],
            "parent_roles": ["admin"],
            "is_system": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        role = Role.from_dict(d)
        assert role.id == "test"
        assert role.has_permission("agents:read")
        assert role.has_permission("tasks:create")
        assert "admin" in role.parent_roles


class TestSystemRoles:
    """Test predefined system roles"""
    
    def test_admin_role(self):
        """Admin role has all permissions"""
        roles = create_system_roles()
        admin = roles["admin"]
        
        assert admin.is_system is True
        assert admin.has_permission("*:admin")
        assert admin.has_permission("anything:anything")
    
    def test_operator_role(self):
        """Operator role has agent/task permissions"""
        roles = create_system_roles()
        operator = roles["operator"]
        
        assert operator.has_permission("agents:read")
        assert operator.has_permission("tasks:create")
        assert operator.has_permission("logs:read")
    
    def test_readonly_role(self):
        """Readonly role has only read access"""
        roles = create_system_roles()
        readonly = roles["readonly"]
        
        assert readonly.has_permission("*:read")
        assert readonly.has_permission("agents:read")
        assert not readonly.has_permission("agents:create")
    
    def test_developer_role(self):
        """Developer role has agent management permissions"""
        roles = create_system_roles()
        dev = roles["developer"]
        
        assert dev.has_permission("agents:create")
        assert dev.has_permission("agents:update")
        assert dev.has_permission("skills:read")
        # Should inherit from operator
        assert dev.has_permission("tasks:create")


class TestRoleAssignment:
    """Test RoleAssignment"""
    
    def test_active_assignment(self):
        """Active assignment not expired"""
        assignment = RoleAssignment(
            user_id="user1",
            role_id="operator",
        )
        
        assert assignment.is_active() is True
        assert assignment.is_expired() is False
    
    def test_expired_assignment(self):
        """Expired assignment"""
        assignment = RoleAssignment(
            user_id="user1",
            role_id="operator",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        
        assert assignment.is_expired() is True
        assert assignment.is_active() is False
    
    def test_to_dict(self):
        """Serialize to dict"""
        assignment = RoleAssignment(
            user_id="user1",
            role_id="operator",
            assigned_by="admin",
        )
        
        d = assignment.to_dict()
        assert d["user_id"] == "user1"
        assert d["role_id"] == "operator"
        assert d["assigned_by"] == "admin"
        assert d["is_active"] is True


class TestResourceContext:
    """Test ResourceContext"""
    
    def test_is_owner(self):
        """Check resource ownership"""
        context = ResourceContext(
            resource_type="agent",
            resource_id="agent-123",
            owner_id="user1",
        )
        
        assert context.is_owner("user1") is True
        assert context.is_owner("user2") is False
    
    def test_to_dict(self):
        """Serialize to dict"""
        context = ResourceContext(
            resource_type="agent",
            resource_id="agent-123",
            owner_id="user1",
            attributes={"name": "Test Agent"},
        )
        
        d = context.to_dict()
        assert d["resource_type"] == "agent"
        assert d["owner_id"] == "user1"


class TestRBACEngine:
    """Test RBACEngine"""
    
    def test_create_role(self):
        """Create custom role"""
        engine = RBACEngine()
        role = engine.create_role(
            id="custom_role",
            name="Custom Role",
            permissions=["agents:read"],
        )
        
        assert role.id == "custom_role"
        assert role.has_permission("agents:read")
    
    def test_create_duplicate_role(self):
        """Cannot create duplicate role"""
        engine = RBACEngine()
        engine.create_role(id="test", name="Test")
        
        with pytest.raises(RBACError):
            engine.create_role(id="test", name="Test 2")
    
    def test_get_role(self):
        """Get existing role"""
        engine = RBACEngine()
        role = engine.get_role("admin")  # System role
        
        assert role.id == "admin"
        assert role.is_system is True
    
    def test_get_nonexistent_role(self):
        """Get nonexistent role raises error"""
        engine = RBACEngine()
        
        with pytest.raises(RoleNotFoundError):
            engine.get_role("nonexistent")
    
    def test_delete_role(self):
        """Delete custom role"""
        engine = RBACEngine()
        engine.create_role(id="test", name="Test")
        engine.delete_role("test")
        
        with pytest.raises(RoleNotFoundError):
            engine.get_role("test")
    
    def test_delete_system_role(self):
        """Cannot delete system role"""
        engine = RBACEngine()
        
        with pytest.raises(RBACError):
            engine.delete_role("admin")
    
    def test_assign_role(self):
        """Assign role to user"""
        engine = RBACEngine()
        assignment = engine.assign_role(
            user_id="user1",
            role_id="operator",
            assigned_by="admin",
        )
        
        assert assignment.user_id == "user1"
        assert assignment.role_id == "operator"
        assert assignment.assigned_by == "admin"
    
    def test_get_user_roles(self):
        """Get all roles for user"""
        engine = RBACEngine()
        engine.assign_role("user1", "readonly")
        engine.assign_role("user1", "operator")
        
        roles = engine.get_user_roles("user1")
        role_ids = {r.id for r in roles}
        
        assert "readonly" in role_ids
        assert "operator" in role_ids
    
    def test_revoke_role(self):
        """Revoke role from user"""
        engine = RBACEngine()
        engine.assign_role("user1", "operator")
        engine.revoke_role("user1", "operator")
        
        roles = engine.get_user_roles("user1")
        assert len(roles) == 0
    
    def test_check_permission_direct(self):
        """Check permission with direct assignment"""
        engine = RBACEngine()
        engine.assign_role("user1", "operator")
        
        assert engine.check_permission("user1", "agents:read") is True
        assert engine.check_permission("user1", "agents:create") is True
        assert engine.check_permission("user1", "users:create") is False
    
    def test_check_permission_with_context_owner(self):
        """Owner gets implicit permissions on their resources"""
        engine = RBACEngine()
        engine.add_owner_rule()
        
        context = ResourceContext(
            resource_type="agent",
            resource_id="agent-123",
            owner_id="user1",
        )
        
        # Owner should be able to read
        assert engine.check_permission("user1", "agents:read", context) is True
        # Non-owner should not
        assert engine.check_permission("user2", "agents:read", context) is False
    
    def test_check_permission_inherited(self):
        """Permissions inherited from parent roles"""
        engine = RBACEngine()
        # Developer inherits from Operator
        engine.assign_role("user1", "developer")
        
        # Should have operator permissions
        assert engine.check_permission("user1", "tasks:create") is True
        # Should have developer permissions
        assert engine.check_permission("user1", "skills:read") is True
    
    def test_require_permission_success(self):
        """Require permission succeeds"""
        engine = RBACEngine()
        engine.assign_role("user1", "admin")
        
        # Should not raise
        engine.require_permission("user1", "anything:anything")
    
    def test_require_permission_failure(self):
        """Require permission raises on failure"""
        engine = RBACEngine()
        engine.assign_role("user1", "readonly")
        
        with pytest.raises(PermissionDeniedError) as exc_info:
            engine.require_permission("user1", "agents:create")
        
        assert "user1" in str(exc_info.value)
        assert "agents:create" in str(exc_info.value)
    
    def test_circular_inheritance_detection(self):
        """Detect circular role inheritance"""
        engine = RBACEngine()
        
        # Create circular dependency: a -> b -> a
        engine.create_role(id="role_a", name="A", parent_roles=["role_b"])
        engine.create_role(id="role_b", name="B", parent_roles=["role_a"])
        
        with pytest.raises(CircularRoleError):
            engine._resolve_role_permissions("role_a")
    
    def test_list_roles(self):
        """List all roles"""
        engine = RBACEngine()
        roles = engine.list_roles()
        
        # Should have system roles
        role_ids = {r.id for r in roles}
        assert "admin" in role_ids
        assert "operator" in role_ids
    
    def test_export_import(self):
        """Export and import RBAC data"""
        engine = RBACEngine()
        engine.assign_role("user1", "operator")
        
        data = engine.export_roles()
        
        # Create new engine and import
        new_engine = RBACEngine()
        new_engine.import_roles(data)
        
        assert new_engine.check_permission("user1", "agents:read") is True


class TestGlobalEngine:
    """Test global RBAC engine functions"""
    
    def test_get_set_engine(self):
        """Get and set global engine"""
        original = get_rbac_engine()
        
        new_engine = RBACEngine()
        set_rbac_engine(new_engine)
        
        assert get_rbac_engine() is new_engine
        
        # Restore
        set_rbac_engine(original)
    
    def test_has_permission(self):
        """Quick permission check"""
        engine = get_rbac_engine()
        engine.assign_role("test_user", "readonly")
        
        assert has_permission("test_user", "agents:read") is True
        assert has_permission("test_user", "agents:create") is False
    
    def test_require_permission(self):
        """Quick permission requirement"""
        engine = get_rbac_engine()
        engine.assign_role("test_user", "admin")
        
        # Should not raise
        require_permission("test_user", "agents:admin")


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_assign_role_with_expiration(self):
        """Assign role with expiration days"""
        engine = get_rbac_engine()
        assignment = assign_role(
            "test_user",
            "operator",
            assigned_by="admin",
            expires_in_days=30,
        )
        
        assert assignment.role_id == "operator"
        assert assignment.expires_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
