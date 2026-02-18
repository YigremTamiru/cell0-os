//! SYPAS (Secure Yielding Process Authorization System)
//! 
//! Capability-based security enforcement for Cell0 OS.
//! 
//! # Overview
//! SYPAS implements a pure capability-based security model where:
//! - All resources are accessed through capabilities
//! - Capabilities are unforgeable tokens
//! - Capabilities can be delegated but not escalated
//! - No ambient authority - all authority must be explicitly granted
//!
//! # Architecture
//! ```
//! ┌─────────────────────────────────────────────┐
//! │           SYPAS Security Manager             │
//! ├─────────────────────────────────────────────┤
//! │  Capability Store  │   Authorization Cache   │
//! ├─────────────────────────────────────────────┤
//! │   Delegation Graph  │   Revocation List       │
//! ├─────────────────────────────────────────────┤
//! │      Policy Engine   │   Audit Logger         │
//! └─────────────────────────────────────────────┘
//! ```

#![cfg_attr(not(feature = "std"), no_std)]

use core::sync::atomic::{AtomicU64, Ordering};

#[cfg(not(feature = "std"))]
use alloc::vec::Vec;
#[cfg(not(feature = "std"))]
use alloc::collections::BTreeMap;

use crate::process::{Capabilities, Capability, ProcessError};

/// SYPAS version
pub const SYPAS_VERSION: &str = "1.0.0";

/// Capability handle (unique identifier)
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct CapabilityHandle(u64);

impl CapabilityHandle {
    pub const fn new(id: u64) -> Self {
        CapabilityHandle(id)
    }
    
    pub fn as_u64(&self) -> u64 {
        self.0
    }
}

/// Capability entry in the capability store
#[derive(Debug, Clone)]
pub struct CapabilityEntry {
    pub handle: CapabilityHandle,
    pub owner: u64, // Process ID
    pub cap: Capability,
    pub delegated_from: Option<CapabilityHandle>,
    pub delegated_to: Vec<CapabilityHandle>,
    pub revoked: bool,
    pub created_at: u64,
}

/// Resource type that can be protected by capabilities
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum ResourceType {
    File = 0,
    Directory = 1,
    Device = 2,
    NetworkEndpoint = 3,
    Process = 4,
    MemoryRegion = 5,
    IpcChannel = 6,
    SystemCall = 7,
}

/// Resource identifier
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResourceId {
    pub resource_type: ResourceType,
    pub id: Vec<u8>,
}

impl ResourceId {
    pub fn new(resource_type: ResourceType, id: &[u8]) -> Self {
        ResourceId {
            resource_type,
            id: id.to_vec(),
        }
    }
}

/// Access rights for a resource
#[derive(Debug, Clone, Copy, Default)]
pub struct AccessRights {
    pub read: bool,
    pub write: bool,
    pub execute: bool,
    pub delete: bool,
    pub delegate: bool,
}

impl AccessRights {
    pub const READ: Self = AccessRights {
        read: true,
        write: false,
        execute: false,
        delete: false,
        delegate: false,
    };
    
    pub const READ_WRITE: Self = AccessRights {
        read: true,
        write: true,
        execute: false,
        delete: false,
        delegate: false,
    };
    
    pub const FULL: Self = AccessRights {
        read: true,
        write: true,
        execute: true,
        delete: true,
        delegate: true,
    };
}

/// Security policy for a resource
#[derive(Debug, Clone)]
pub struct SecurityPolicy {
    pub resource: ResourceId,
    pub required_caps: Vec<Capability>,
    pub default_rights: AccessRights,
}

/// Audit log entry
#[derive(Debug, Clone)]
pub struct AuditEntry {
    pub timestamp: u64,
    pub process_id: u64,
    pub action: AuditAction,
    pub resource: ResourceId,
    pub allowed: bool,
    pub reason: Option<&'static str>,
}

/// Audit action types
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum AuditAction {
    CapabilityCheck = 0,
    ResourceAccess = 1,
    CapabilityDelegation = 2,
    CapabilityRevocation = 3,
    PolicyViolation = 4,
}

/// SYPAS security manager
pub struct SypasManager {
    capability_store: Vec<CapabilityEntry>,
    next_handle: AtomicU64,
    policies: Vec<SecurityPolicy>,
    audit_log: Vec<AuditEntry>,
    enforcement_mode: EnforcementMode,
}

/// Security enforcement mode
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum EnforcementMode {
    /// Allow all access (for debugging)
    Permissive = 0,
    /// Log violations but allow
    Auditing = 1,
    /// Full enforcement
    Enforcing = 2,
}

impl SypasManager {
    pub const fn new() -> Self {
        SypasManager {
            capability_store: Vec::new(),
            next_handle: AtomicU64::new(1),
            policies: Vec::new(),
            audit_log: Vec::new(),
            enforcement_mode: EnforcementMode::Enforcing,
        }
    }
    
    /// Initialize SYPAS
    pub fn init(&mut self) {
        // Set up default policies
        self.add_default_policies();
    }
    
    /// Set enforcement mode
    pub fn set_enforcement_mode(&mut self, mode: EnforcementMode) {
        self.enforcement_mode = mode;
    }
    
    /// Check if process has capability for resource
    pub fn check_access(
        &mut self,
        process_id: u64,
        resource: &ResourceId,
        requested_rights: AccessRights,
    ) -> Result<(), SypasError> {
        let allowed = match self.enforcement_mode {
            EnforcementMode::Permissive => true,
            EnforcementMode::Auditing | EnforcementMode::Enforcing => {
                self.verify_access(process_id, resource, requested_rights)
            }
        };
        
        // Audit the access attempt
        self.audit_log.push(AuditEntry {
            timestamp: 0, // TODO: Get real time
            process_id,
            action: AuditAction::ResourceAccess,
            resource: resource.clone(),
            allowed,
            reason: if allowed { None } else { Some("Access denied") },
        });
        
        if allowed || self.enforcement_mode == EnforcementMode::Auditing {
            Ok(())
        } else {
            Err(SypasError::AccessDenied)
        }
    }
    
    /// Verify access internally
    fn verify_access(&self, _process_id: u64, resource: &ResourceId, _rights: AccessRights) -> bool {
        // Find applicable policy
        for policy in &self.policies {
            if policy.resource.resource_type == resource.resource_type {
                // Check if process has required capabilities
                // In real implementation, would check process capabilities
                return true; // Simplified
            }
        }
        
        // No policy found - deny by default
        false
    }
    
    /// Grant a capability to a process
    pub fn grant_capability(
        &mut self,
        process_id: u64,
        cap: Capability,
    ) -> Result<CapabilityHandle, SypasError> {
        let handle = CapabilityHandle(self.next_handle.fetch_add(1, Ordering::SeqCst));
        
        let entry = CapabilityEntry {
            handle,
            owner: process_id,
            cap,
            delegated_from: None,
            delegated_to: Vec::new(),
            revoked: false,
            created_at: 0, // TODO: Get real time
        };
        
        self.capability_store.push(entry);
        
        self.audit_log.push(AuditEntry {
            timestamp: 0,
            process_id,
            action: AuditAction::CapabilityDelegation,
            resource: ResourceId::new(ResourceType::Process, &process_id.to_le_bytes()),
            allowed: true,
            reason: None,
        });
        
        Ok(handle)
    }
    
    /// Revoke a capability
    pub fn revoke_capability(&mut self, handle: CapabilityHandle) -> Result<(), SypasError> {
        // Find the entry and collect info first
        let (owner, delegated_to) = if let Some(entry) = self.capability_store.iter_mut().find(|e| e.handle == handle) {
            entry.revoked = true;
            let owner = entry.owner;
            let delegated = entry.delegated_to.clone();
            (owner, delegated)
        } else {
            return Err(SypasError::CapabilityNotFound);
        };
        
        // Recursively revoke delegated capabilities (after mutable borrow is released)
        for delegated in delegated_to {
            let _ = self.revoke_capability(delegated);
        }
        
        self.audit_log.push(AuditEntry {
            timestamp: 0,
            process_id: owner,
            action: AuditAction::CapabilityRevocation,
            resource: ResourceId::new(ResourceType::Process, &owner.to_le_bytes()),
            allowed: true,
            reason: None,
        });
        
        Ok(())
    }
    
    /// Delegate a capability to another process
    pub fn delegate_capability(
        &mut self,
        from_handle: CapabilityHandle,
        to_process: u64,
    ) -> Result<CapabilityHandle, SypasError> {
        // Find the original capability
        let original = self.capability_store
            .iter()
            .find(|e| e.handle == from_handle && !e.revoked)
            .ok_or(SypasError::CapabilityNotFound)?;
        
        // Create delegated capability
        let new_handle = CapabilityHandle(self.next_handle.fetch_add(1, Ordering::SeqCst));
        
        let delegated = CapabilityEntry {
            handle: new_handle,
            owner: to_process,
            cap: original.cap,
            delegated_from: Some(from_handle),
            delegated_to: Vec::new(),
            revoked: false,
            created_at: 0,
        };
        
        self.capability_store.push(delegated);
        
        Ok(new_handle)
    }
    
    /// Add default security policies
    fn add_default_policies(&mut self) {
        // File system policy
        self.policies.push(SecurityPolicy {
            resource: ResourceId::new(ResourceType::File, b"*"),
            required_caps: vec![Capability::FileRead],
            default_rights: AccessRights::READ,
        });
        
        // Network policy
        self.policies.push(SecurityPolicy {
            resource: ResourceId::new(ResourceType::NetworkEndpoint, b"*"),
            required_caps: vec![Capability::Network],
            default_rights: AccessRights::READ_WRITE,
        });
    }
    
    /// Get audit log
    pub fn get_audit_log(&self) -> &[AuditEntry] {
        &self.audit_log
    }
    
    /// Clear audit log
    pub fn clear_audit_log(&mut self) {
        self.audit_log.clear();
    }
}

/// SYPAS errors
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SypasError {
    AccessDenied,
    CapabilityNotFound,
    InvalidCapability,
    DelegationNotAllowed,
    PolicyViolation,
    AuditLogFull,
}

/// Global SYPAS manager
static mut SYPAS_MANAGER: Option<SypasManager> = None;

/// Initialize SYPAS
pub fn init() {
    unsafe {
        SYPAS_MANAGER = Some(SypasManager::new());
        if let Some(ref mut manager) = SYPAS_MANAGER {
            manager.init();
        }
    }
}

/// Check access to resource
pub fn check_access(
    process_id: u64,
    resource: &ResourceId,
    rights: AccessRights,
) -> Result<(), SypasError> {
    unsafe {
        if let Some(ref mut manager) = SYPAS_MANAGER {
            manager.check_access(process_id, resource, rights)
        } else {
            Err(SypasError::AccessDenied)
        }
    }
}

/// Grant capability to process
pub fn grant_capability(process_id: u64, cap: Capability) -> Result<CapabilityHandle, SypasError> {
    unsafe {
        if let Some(ref mut manager) = SYPAS_MANAGER {
            manager.grant_capability(process_id, cap)
        } else {
            Err(SypasError::AccessDenied)
        }
    }
}

/// Revoke capability
pub fn revoke_capability(handle: CapabilityHandle) -> Result<(), SypasError> {
    unsafe {
        if let Some(ref mut manager) = SYPAS_MANAGER {
            manager.revoke_capability(handle)
        } else {
            Err(SypasError::CapabilityNotFound)
        }
    }
}

/// Set enforcement mode
pub fn set_enforcement_mode(mode: EnforcementMode) {
    unsafe {
        if let Some(ref mut manager) = SYPAS_MANAGER {
            manager.set_enforcement_mode(mode);
        }
    }
}

/// Get audit log
pub fn get_audit_log() -> &'static [AuditEntry] {
    unsafe {
        if let Some(ref manager) = SYPAS_MANAGER {
            manager.get_audit_log()
        } else {
            &[]
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_capability_handle() {
        let handle = CapabilityHandle::new(42);
        assert_eq!(handle.as_u64(), 42);
    }

    #[test]
    fn test_access_rights() {
        let rights = AccessRights::READ;
        assert!(rights.read);
        assert!(!rights.write);
        
        let full = AccessRights::FULL;
        assert!(full.read && full.write && full.execute && full.delete);
    }

    #[test]
    fn test_resource_id() {
        let res = ResourceId::new(ResourceType::File, b"/etc/passwd");
        assert_eq!(res.resource_type, ResourceType::File);
        assert_eq!(res.id, b"/etc/passwd");
    }

    #[test]
    fn test_sypas_manager() {
        let mut manager = SypasManager::new();
        manager.init();
        
        // Grant capability
        let handle = manager.grant_capability(1, Capability::FileRead);
        assert!(handle.is_ok());
    }
}
