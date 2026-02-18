//! Crypto Agility Framework
//! 
//! Provides dynamic algorithm selection, negotiation, and fallback mechanisms
//! for the cryptographic system. Enables seamless transition between
//! algorithms as security requirements evolve.
//!
//! # Features
//! - Algorithm negotiation between peers
//! - Priority-based algorithm selection
//! - Automatic fallback on negotiation failure
//! - Algorithm deprecation and migration
//! - Performance-based selection
//! - Crypto inventory management

use super::{
    AlgorithmId, AlgorithmCategory, SecurityLevel, CryptoError, CryptoResult,
    ed25519::{Ed25519Keypair, PUBLIC_KEY_SIZE as ED25519_PK_SIZE, SIGNATURE_SIZE as ED25519_SIG_SIZE},
    x25519::{X25519Keypair, KEY_SIZE as X25519_KEY_SIZE},
};

#[cfg(not(feature = "std"))]
use alloc::vec::Vec;
#[cfg(not(feature = "std"))]
use alloc::vec;
#[cfg(not(feature = "std"))]
use alloc::string::{String, ToString};

/// Algorithm capability descriptor
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AlgorithmCapability {
    /// Algorithm identifier
    pub id: AlgorithmId,
    /// Security level provided
    pub security_level: SecurityLevel,
    /// Estimated performance (operations per second)
    pub performance_ops_per_sec: u64,
    /// Hardware acceleration available
    pub hardware_accelerated: bool,
    /// Constant-time implementation
    pub constant_time: bool,
    /// Post-quantum secure
    pub post_quantum: bool,
    /// FIPS 140-2 compliant
    pub fips_compliant: bool,
}

impl AlgorithmCapability {
    pub fn new(id: AlgorithmId, security: SecurityLevel) -> Self {
        AlgorithmCapability {
            id,
            security_level: security,
            performance_ops_per_sec: 0,
            hardware_accelerated: false,
            constant_time: true,
            post_quantum: false,
            fips_compliant: false,
        }
    }

    pub fn with_performance(mut self, ops_per_sec: u64) -> Self {
        self.performance_ops_per_sec = ops_per_sec;
        self
    }

    pub fn with_hardware_acceleration(mut self) -> Self {
        self.hardware_accelerated = true;
        self
    }

    pub fn with_post_quantum(mut self) -> Self {
        self.post_quantum = true;
        self
    }

    pub fn with_fips_compliance(mut self) -> Self {
        self.fips_compliant = true;
        self
    }

    /// Score this algorithm for selection (higher is better)
    pub fn score(&self, preference: &AlgorithmPreference) -> u64 {
        let mut score = 0u64;

        // Security level (weighted heavily)
        let security_score = match (self.security_level, preference.min_security) {
            (SecurityLevel::Bits256, SecurityLevel::Bits128) => 100,
            (SecurityLevel::Bits256, SecurityLevel::Bits192) => 100,
            (SecurityLevel::Bits256, SecurityLevel::Bits256) => 100,
            (SecurityLevel::Bits192, SecurityLevel::Bits128) => 70,
            (SecurityLevel::Bits192, SecurityLevel::Bits192) => 70,
            (SecurityLevel::Bits128, SecurityLevel::Bits128) => 50,
            (SecurityLevel::PostQuantum128, _) if preference.require_post_quantum => 150,
            (SecurityLevel::PostQuantum256, _) if preference.require_post_quantum => 200,
            _ => 0, // Below minimum security
        };
        score += security_score;

        // Performance
        if preference.prefer_performance && self.performance_ops_per_sec > 0 {
            score += (self.performance_ops_per_sec / 10000).min(50);
        }

        // Hardware acceleration
        if preference.prefer_hardware && self.hardware_accelerated {
            score += 30;
        }

        // Post-quantum preference
        if preference.prefer_post_quantum && self.post_quantum {
            score += 40;
        }

        // FIPS compliance
        if preference.require_fips && self.fips_compliant {
            score += 20;
        } else if preference.require_fips && !self.fips_compliant {
            score = 0; // Disqualify non-FIPS
        }

        score
    }
}

/// Algorithm selection preference
#[derive(Clone, Debug)]
pub struct AlgorithmPreference {
    /// Minimum required security level
    pub min_security: SecurityLevel,
    /// Prefer faster algorithms
    pub prefer_performance: bool,
    /// Prefer hardware-accelerated algorithms
    pub prefer_hardware: bool,
    /// Prefer post-quantum algorithms
    pub prefer_post_quantum: bool,
    /// Require post-quantum security
    pub require_post_quantum: bool,
    /// Require FIPS compliance
    pub require_fips: bool,
    /// Algorithm priority list (preferred first)
    pub priority_list: Vec<AlgorithmId>,
    /// Forbidden algorithms
    pub forbidden: Vec<AlgorithmId>,
}

impl AlgorithmPreference {
    pub fn default() -> Self {
        AlgorithmPreference {
            min_security: SecurityLevel::Bits128,
            prefer_performance: false,
            prefer_hardware: true,
            prefer_post_quantum: false,
            require_post_quantum: false,
            require_fips: false,
            priority_list: vec![],
            forbidden: vec![],
        }
    }

    pub fn secure_default() -> Self {
        AlgorithmPreference {
            min_security: SecurityLevel::Bits256,
            prefer_performance: false,
            prefer_hardware: true,
            prefer_post_quantum: true,
            require_post_quantum: false,
            require_fips: false,
            priority_list: vec![
                AlgorithmId::Ed25519,
                AlgorithmId::X25519,
                AlgorithmId::ChaCha20Poly1305,
                AlgorithmId::Aes256Gcm,
            ],
            forbidden: vec![],
        }
    }

    pub fn post_quantum() -> Self {
        AlgorithmPreference {
            min_security: SecurityLevel::PostQuantum128,
            prefer_performance: false,
            prefer_hardware: false,
            prefer_post_quantum: true,
            require_post_quantum: true,
            require_fips: false,
            priority_list: vec![
                AlgorithmId::Dilithium3,
                AlgorithmId::Kyber768,
                AlgorithmId::Kyber1024,
            ],
            forbidden: vec![],
        }
    }

    pub fn high_performance() -> Self {
        AlgorithmPreference {
            min_security: SecurityLevel::Bits128,
            prefer_performance: true,
            prefer_hardware: true,
            prefer_post_quantum: false,
            require_post_quantum: false,
            require_fips: false,
            priority_list: vec![
                AlgorithmId::ChaCha20Poly1305,
                AlgorithmId::Ed25519,
                AlgorithmId::X25519,
            ],
            forbidden: vec![],
        }
    }

    pub fn with_min_security(mut self, level: SecurityLevel) -> Self {
        self.min_security = level;
        self
    }

    pub fn forbid(mut self, alg: AlgorithmId) -> Self {
        self.forbidden.push(alg);
        self
    }

    pub fn prefer(mut self, alg: AlgorithmId) -> Self {
        self.priority_list.push(alg);
        self
    }
}

/// Negotiation result
#[derive(Clone, Debug)]
pub struct NegotiationResult {
    selected: AlgorithmId,
    alternatives: Vec<AlgorithmId>,
    security_level: SecurityLevel,
    fallback_available: bool,
}

impl NegotiationResult {
    pub fn selected_algorithm(&self) -> AlgorithmId {
        self.selected
    }

    pub fn alternatives(&self) -> &[AlgorithmId] {
        &self.alternatives
    }

    pub fn security_level(&self) -> SecurityLevel {
        self.security_level
    }

    pub fn has_fallback(&self) -> bool {
        self.fallback_available
    }
}

/// Crypto agility manager
pub struct AgilityManager {
    /// Local capabilities
    local_capabilities: Vec<(AlgorithmCategory, Vec<AlgorithmCapability>)>,
    /// Current preferences
    preference: AlgorithmPreference,
    /// Fallback strategy
    fallback_strategy: FallbackStrategy,
    /// Algorithm blacklist (security issues)
    blacklist: Vec<AlgorithmId>,
    /// Algorithm deprecation warnings
    deprecated: Vec<(AlgorithmId, String)>,
    /// Negotiation history
    negotiation_history: Vec<NegotiationRecord>,
}

/// Fallback strategy
#[derive(Clone, Debug)]
pub enum FallbackStrategy {
    /// Fail on negotiation failure
    Fail,
    /// Use minimum secure algorithm
    MinimumSecure,
    /// Use fastest available
    Fastest,
    /// Use most secure available
    MostSecure,
}

/// Negotiation record
#[derive(Clone, Debug)]
pub struct NegotiationRecord {
    timestamp: u64,
    peer_id: Option<[u8; 16]>,
    requested: Vec<AlgorithmId>,
    selected: AlgorithmId,
    success: bool,
}

impl AgilityManager {
    pub fn new() -> Self {
        let mut manager = AgilityManager {
            local_capabilities: Vec::new(),
            preference: AlgorithmPreference::default(),
            fallback_strategy: FallbackStrategy::MinimumSecure,
            blacklist: vec![],
            deprecated: vec![],
            negotiation_history: vec![],
        };
        
        manager.register_default_capabilities();
        manager
    }

    /// Register default local capabilities
    fn register_default_capabilities(&mut self) {
        // Symmetric encryption
        self.register_capability(AlgorithmCategory::SymmetricEncryption, 
            AlgorithmCapability::new(AlgorithmId::Aes256Gcm, SecurityLevel::Bits256)
                .with_performance(1000000)
                .with_hardware_acceleration()
                .with_fips_compliance());
        
        self.register_capability(AlgorithmCategory::SymmetricEncryption,
            AlgorithmCapability::new(AlgorithmId::ChaCha20Poly1305, SecurityLevel::Bits256)
                .with_performance(1500000)
                .with_hardware_acceleration());

        // Signatures
        self.register_capability(AlgorithmCategory::Signature,
            AlgorithmCapability::new(AlgorithmId::Ed25519, SecurityLevel::Bits256)
                .with_performance(50000)
                .with_hardware_acceleration());
        
        self.register_capability(AlgorithmCategory::Signature,
            AlgorithmCapability::new(AlgorithmId::Dilithium3, SecurityLevel::PostQuantum128)
                .with_performance(5000)
                .with_post_quantum());

        self.register_capability(AlgorithmCategory::Signature,
            AlgorithmCapability::new(AlgorithmId::Bls12_381, SecurityLevel::Bits256)
                .with_performance(10000));

        // Key exchange
        self.register_capability(AlgorithmCategory::KeyExchange,
            AlgorithmCapability::new(AlgorithmId::X25519, SecurityLevel::Bits256)
                .with_performance(10000)
                .with_hardware_acceleration());
        
        self.register_capability(AlgorithmCategory::KeyExchange,
            AlgorithmCapability::new(AlgorithmId::Kyber768, SecurityLevel::PostQuantum128)
                .with_performance(2000)
                .with_post_quantum());

        // Hashes
        self.register_capability(AlgorithmCategory::Hash,
            AlgorithmCapability::new(AlgorithmId::Sha3_256, SecurityLevel::Bits256)
                .with_performance(1000000)
                .with_hardware_acceleration());
    }

    /// Register a local capability
    pub fn register_capability(&mut self, category: AlgorithmCategory, capability: AlgorithmCapability) {
        if let Some((_, caps)) = self.local_capabilities.iter_mut().find(|(c, _)| *c == category) {
            caps.push(capability);
        } else {
            self.local_capabilities.push((category, vec![capability]));
        }
    }

    /// Set preference
    pub fn set_preference(&mut self, preference: AlgorithmPreference) {
        self.preference = preference;
    }

    /// Set fallback strategy
    pub fn set_fallback_strategy(&mut self, strategy: FallbackStrategy) {
        self.fallback_strategy = strategy;
    }

    /// Blacklist algorithm (security vulnerability discovered)
    pub fn blacklist(&mut self, alg: AlgorithmId, _reason: &str) {
        if !self.blacklist.contains(&alg) {
            self.blacklist.push(alg);
        }
    }

    /// Deprecate algorithm (not yet insecure, but being phased out)
    pub fn deprecate(&mut self, alg: AlgorithmId, notice: &str) {
        self.deprecated.push((alg, notice.to_string()));
    }

    /// Check if algorithm is available
    pub fn is_available(&self, alg: &AlgorithmId) -> bool {
        if self.blacklist.contains(alg) {
            return false;
        }
        if self.preference.forbidden.contains(alg) {
            return false;
        }
        
        // Check if we have this capability
        for (_, caps) in &self.local_capabilities {
            if caps.iter().any(|c: &AlgorithmCapability| c.id == *alg) {
                return true;
            }
        }
        false
    }

    /// Negotiate with peer
    pub fn negotiate(&mut self, peer_capabilities: &[AlgorithmCapability]) -> CryptoResult<NegotiationResult> {
        // Filter peer capabilities by our requirements
        let mut candidates: Vec<&AlgorithmCapability> = peer_capabilities
            .iter()
            .filter(|cap| self.is_available(&cap.id))
            .filter(|cap| {
                cap.security_level >= self.preference.min_security ||
                (cap.post_quantum && self.preference.require_post_quantum)
            })
            .collect();

        // Score and sort
        candidates.sort_by(|a: &&AlgorithmCapability, b| {
            let score_a = a.score(&self.preference);
            let score_b = b.score(&self.preference);
            score_b.cmp(&score_a) // Higher score first
        });

        // Apply priority list
        for preferred in &self.preference.priority_list {
            if let Some(pos) = candidates.iter().position(|c| c.id == *preferred) {
                let cap = candidates.remove(pos);
                candidates.insert(0, cap);
            }
        }

        if candidates.is_empty() {
            // Try fallback
            return self.fallback();
        }

        let selected = candidates[0].id.clone();
        let alternatives: Vec<AlgorithmId> = candidates[1..]
            .iter()
            .map(|c| c.id)
            .take(3)
            .collect();

        // Record negotiation
        self.negotiation_history.push(NegotiationRecord {
            timestamp: 0, // Would use actual time
            peer_id: None,
            requested: peer_capabilities.iter().map(|c| c.id).collect(),
            selected,
            success: true,
        });

        let fallback_available = !alternatives.is_empty();
        Ok(NegotiationResult {
            selected,
            alternatives,
            security_level: candidates[0].security_level,
            fallback_available,
        })
    }

    /// Fallback selection
    pub fn fallback(&mut self) -> CryptoResult<NegotiationResult> {
        match self.fallback_strategy {
            FallbackStrategy::Fail => {
                Err(CryptoError::AgilityNegotiationFailed)
            }
            FallbackStrategy::MinimumSecure => {
                // Find minimum algorithm that meets security requirements
                for (_, caps) in &self.local_capabilities {
                    for cap in caps {
                        if cap.security_level >= self.preference.min_security {
                            return Ok(NegotiationResult {
                                selected: cap.id,
                                alternatives: vec![],
                                security_level: cap.security_level,
                                fallback_available: true,
                            });
                        }
                    }
                }
                Err(CryptoError::AgilityNegotiationFailed)
            }
            FallbackStrategy::Fastest => {
                // Find fastest available
                let mut fastest: Option<&AlgorithmCapability> = None;
                for (_, caps) in &self.local_capabilities {
                    for cap in caps {
                        if fastest.is_none() || 
                           cap.performance_ops_per_sec > fastest.unwrap().performance_ops_per_sec {
                            fastest = Some(cap);
                        }
                    }
                }
                fastest.map(|c| NegotiationResult {
                    selected: c.id,
                    alternatives: vec![],
                    security_level: c.security_level,
                    fallback_available: true,
                }).ok_or(CryptoError::AgilityNegotiationFailed)
            }
            FallbackStrategy::MostSecure => {
                // Find most secure available
                let mut most_secure: Option<&AlgorithmCapability> = None;
                for (_, caps) in &self.local_capabilities {
                    for cap in caps {
                        if most_secure.is_none() || 
                           cap.security_level > most_secure.unwrap().security_level {
                            most_secure = Some(cap);
                        }
                    }
                }
                most_secure.map(|c| NegotiationResult {
                    selected: c.id,
                    alternatives: vec![],
                    security_level: c.security_level,
                    fallback_available: true,
                }).ok_or(CryptoError::AgilityNegotiationFailed)
            }
        }
    }

    /// Get algorithm capabilities for a category
    pub fn get_capabilities(&self, category: AlgorithmCategory) -> Option<&[AlgorithmCapability]> {
        self.local_capabilities
            .iter()
            .find(|(c, _)| *c == category)
            .map(|(_, v)| v.as_slice())
    }

    /// Get all local capabilities
    pub fn get_all_capabilities(&self) -> Vec<&AlgorithmCapability> {
        self.local_capabilities
            .iter()
            .flat_map(|(_, v)| v.iter())
            .collect()
    }

    /// Get negotiation history
    pub fn negotiation_history(&self) -> &[NegotiationRecord] {
        &self.negotiation_history
    }

    /// Get deprecation warnings
    pub fn deprecation_warnings(&self) -> &[(AlgorithmId, String)] {
        &self.deprecated
    }

    /// Check for deprecation warning
    pub fn check_deprecation(&self, alg: AlgorithmId) -> Option<&str> {
        self.deprecated.iter()
            .find(|(a, _)| *a == alg)
            .map(|(_, msg)| msg.as_str())
    }
}

/// Crypto inventory for tracking algorithm usage
pub struct CryptoInventory {
    algorithm_usage: Vec<(AlgorithmId, UsageStats)>,
    total_operations: u64,
}

/// Usage statistics
#[derive(Clone, Debug, Default)]
pub struct UsageStats {
    pub encrypt_ops: u64,
    pub decrypt_ops: u64,
    pub sign_ops: u64,
    pub verify_ops: u64,
    pub key_gen_ops: u64,
    pub failures: u64,
}

impl CryptoInventory {
    pub fn new() -> Self {
        CryptoInventory {
            algorithm_usage: Vec::new(),
            total_operations: 0,
        }
    }

    pub fn record_operation(&mut self, alg: AlgorithmId, op_type: OperationType) {
        if let Some((_, stats)) = self.algorithm_usage.iter_mut().find(|(a, _)| *a == alg) {
            match op_type {
                OperationType::Encrypt => stats.encrypt_ops += 1,
                OperationType::Decrypt => stats.decrypt_ops += 1,
                OperationType::Sign => stats.sign_ops += 1,
                OperationType::Verify => stats.verify_ops += 1,
                OperationType::KeyGen => stats.key_gen_ops += 1,
                OperationType::Failure => stats.failures += 1,
            }
        } else {
            let mut stats = UsageStats::default();
            match op_type {
                OperationType::Encrypt => stats.encrypt_ops += 1,
                OperationType::Decrypt => stats.decrypt_ops += 1,
                OperationType::Sign => stats.sign_ops += 1,
                OperationType::Verify => stats.verify_ops += 1,
                OperationType::KeyGen => stats.key_gen_ops += 1,
                OperationType::Failure => stats.failures += 1,
            }
            self.algorithm_usage.push((alg, stats));
        }
        
        self.total_operations += 1;
    }

    pub fn get_stats(&self, alg: AlgorithmId) -> Option<&UsageStats> {
        self.algorithm_usage.iter().find(|(a, _)| *a == alg).map(|(_, s)| s)
    }

    pub fn most_used(&self) -> Option<(AlgorithmId, &UsageStats)> {
        self.algorithm_usage
            .iter()
            .max_by_key(|(_, stats)| {
                stats.encrypt_ops + stats.decrypt_ops + stats.sign_ops + 
                stats.verify_ops + stats.key_gen_ops
            })
            .map(|(k, v)| (*k, v))
    }

    pub fn failure_rate(&self, alg: AlgorithmId) -> f64 {
        if let Some((_, stats)) = self.algorithm_usage.iter().find(|(a, _)| *a == alg) {
            let total = stats.encrypt_ops + stats.decrypt_ops + stats.sign_ops + 
                       stats.verify_ops + stats.key_gen_ops + stats.failures;
            if total > 0 {
                stats.failures as f64 / total as f64
            } else {
                0.0
            }
        } else {
            0.0
        }
    }

    pub fn generate_report(&self) -> InventoryReport {
        let mut algorithms: Vec<(AlgorithmId, &UsageStats)> = self.algorithm_usage.iter().map(|(k, v)| (*k, v)).collect();
        algorithms.sort_by(|a, b| {
            let total_a = a.1.encrypt_ops + a.1.decrypt_ops + a.1.sign_ops + a.1.verify_ops;
            let total_b = b.1.encrypt_ops + b.1.decrypt_ops + b.1.sign_ops + b.1.verify_ops;
            total_b.cmp(&total_a)
        });

        InventoryReport {
            total_operations: self.total_operations,
            algorithm_usage: algorithms.into_iter()
                .map(|(k, v)| (k, v.clone()))
                .collect(),
        }
    }
}

/// Operation type for inventory
#[derive(Clone, Copy, Debug)]
pub enum OperationType {
    Encrypt,
    Decrypt,
    Sign,
    Verify,
    KeyGen,
    Failure,
}

/// Inventory report
#[derive(Clone, Debug)]
pub struct InventoryReport {
    pub total_operations: u64,
    pub algorithm_usage: Vec<(AlgorithmId, UsageStats)>,
}

/// Algorithm migration helper
pub struct AlgorithmMigration;

impl AlgorithmMigration {
    /// Check if migration from old to new algorithm is needed
    pub fn migration_needed(_old_alg: AlgorithmId, _new_alg: AlgorithmId, _security_requirement: SecurityLevel) -> bool {
        // Check if old algorithm is deprecated or below security requirement
        // and new algorithm is available
        true // Simplified
    }

    /// Create migration plan
    pub fn create_plan(current: AlgorithmId, target: AlgorithmId) -> MigrationPlan {
        MigrationPlan {
            from: current,
            to: target,
            steps: vec![
                MigrationStep::EnableTarget,
                MigrationStep::DualOperation,
                MigrationStep::PreferTarget,
                MigrationStep::DisableSource,
            ],
        }
    }
}

/// Migration plan
#[derive(Clone, Debug)]
pub struct MigrationPlan {
    pub from: AlgorithmId,
    pub to: AlgorithmId,
    pub steps: Vec<MigrationStep>,
}

/// Migration step
#[derive(Clone, Copy, Debug)]
pub enum MigrationStep {
    EnableTarget,
    DualOperation,
    PreferTarget,
    DisableSource,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agility_manager_creation() {
        let manager = AgilityManager::new();
        let caps = manager.get_capabilities(AlgorithmCategory::Signature);
        assert!(caps.is_some());
        assert!(!caps.unwrap().is_empty());
    }

    #[test]
    fn test_algorithm_capability_scoring() {
        let cap = AlgorithmCapability::new(AlgorithmId::Ed25519, SecurityLevel::Bits256)
            .with_performance(100000)
            .with_hardware_acceleration();
        
        let pref = AlgorithmPreference::secure_default();
        let score = cap.score(&pref);
        assert!(score > 0);
    }

    #[test]
    fn test_negotiation() {
        let mut manager = AgilityManager::new();
        manager.set_preference(AlgorithmPreference::secure_default());
        
        let peer_caps = vec![
            AlgorithmCapability::new(AlgorithmId::Ed25519, SecurityLevel::Bits256),
            AlgorithmCapability::new(AlgorithmId::Aes256Gcm, SecurityLevel::Bits256),
        ];
        
        let result = manager.negotiate(&peer_caps).unwrap();
        assert!(result.has_fallback());
    }

    #[test]
    fn test_blacklist() {
        let mut manager = AgilityManager::new();
        manager.blacklist(AlgorithmId::Ed25519, "Test vulnerability");
        
        assert!(!manager.is_available(&AlgorithmId::Ed25519));
    }

    #[test]
    fn test_crypto_inventory() {
        let mut inventory = CryptoInventory::new();
        
        inventory.record_operation(AlgorithmId::Ed25519, OperationType::Sign);
        inventory.record_operation(AlgorithmId::Ed25519, OperationType::Sign);
        inventory.record_operation(AlgorithmId::Ed25519, OperationType::Verify);
        
        let stats = inventory.get_stats(AlgorithmId::Ed25519).unwrap();
        assert_eq!(stats.sign_ops, 2);
        assert_eq!(stats.verify_ops, 1);
        
        let report = inventory.generate_report();
        assert_eq!(report.total_operations, 3);
    }

    #[test]
    fn test_preference_builders() {
        let pref = AlgorithmPreference::secure_default()
            .with_min_security(SecurityLevel::PostQuantum256)
            .forbid(AlgorithmId::Aes128Gcm)
            .prefer(AlgorithmId::Ed25519);
        
        assert!(pref.priority_list.contains(&AlgorithmId::Ed25519));
        assert!(pref.forbidden.contains(&AlgorithmId::Aes128Gcm));
    }

    #[test]
    fn test_algorithm_migration() {
        let plan = AlgorithmMigration::create_plan(
            AlgorithmId::Aes128Gcm,
            AlgorithmId::Aes256Gcm,
        );
        
        assert_eq!(plan.from, AlgorithmId::Aes128Gcm);
        assert_eq!(plan.to, AlgorithmId::Aes256Gcm);
        assert!(!plan.steps.is_empty());
    }
}
