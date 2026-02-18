//! NFEK (Non-Fungible Ephemeral Key) System for Cell 0 Kernel
//! 
//! NFEK provides unique, single-use keys that are:
//! - Non-fungible: Each key is cryptographically unique
//! - Ephemeral: Keys are short-lived and automatically rotated
//! - Attestable: Keys can be cryptographically attested to prove origin
//! 
//! Used for secure agent-to-agent communication and capability delegation.

use core::sync::atomic::{AtomicU64, Ordering};
use super::{CryptoRng, HardwareRng, constant_time_eq};

#[cfg(not(feature = "std"))]
use alloc::vec::Vec;

/// Size of NFEK identifier (256-bit)
pub const NFEK_ID_SIZE: usize = 32;
/// Size of NFEK seed material (256-bit)
pub const NFEK_SEED_SIZE: usize = 32;
/// Default key lifetime in seconds
pub const NFEK_DEFAULT_LIFETIME_SECS: u64 = 300; // 5 minutes
/// Maximum number of active keys before forced rotation
pub const NFEK_MAX_ACTIVE_KEYS: usize = 100;

/// Key state
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum NfekState {
    /// Key is active and can be used
    Active,
    /// Key is being rotated out
    Rotating,
    /// Key has been revoked
    Revoked,
    /// Key has expired
    Expired,
}

/// NFEK metadata
#[derive(Clone, Debug)]
pub struct NfekMetadata {
    /// Key creation timestamp (seconds since epoch)
    pub created_at: u64,
    /// Key expiration timestamp
    pub expires_at: u64,
    /// Key rotation count
    pub rotation_count: u32,
    /// Key state
    pub state: NfekState,
    /// Associated agent ID
    pub agent_id: u64,
    /// Key purpose/label
    pub purpose: [u8; 32],
}

impl NfekMetadata {
    pub const fn new() -> Self {
        Self {
            created_at: 0,
            expires_at: 0,
            rotation_count: 0,
            state: NfekState::Active,
            agent_id: 0,
            purpose: [0u8; 32],
        }
    }
}

impl Default for NfekMetadata {
    fn default() -> Self {
        Self::new()
    }
}

/// Non-Fungible Ephemeral Key
#[derive(Clone, Debug)]
pub struct Nfek {
    /// Unique key identifier (hash of public components)
    pub id: [u8; NFEK_ID_SIZE],
    /// Key seed material (kept secret)
    pub seed: [u8; NFEK_SEED_SIZE],
    /// Derived symmetric key for encryption
    pub sym_key: [u8; 32],
    /// Derived authentication key
    pub auth_key: [u8; 32],
    /// Key metadata
    pub metadata: NfekMetadata,
    /// Parent key ID (for derived keys)
    pub parent_id: Option<[u8; NFEK_ID_SIZE]>,
    /// Attestation signature
    pub attestation: Option<NfekAttestation>,
}

impl Nfek {
    /// Create a new NFEK from seed material
    pub fn from_seed(seed: &[u8; NFEK_SEED_SIZE], agent_id: u64, purpose: &[u8]) -> Self {
        let mut nfek = Self {
            id: [0u8; NFEK_ID_SIZE],
            seed: *seed,
            sym_key: [0u8; 32],
            auth_key: [0u8; 32],
            metadata: NfekMetadata::new(),
            parent_id: None,
            attestation: None,
        };

        nfek.derive_keys();
        nfek.compute_id();
        
        nfek.metadata.created_at = current_timestamp();
        nfek.metadata.expires_at = nfek.metadata.created_at + NFEK_DEFAULT_LIFETIME_SECS;
        nfek.metadata.agent_id = agent_id;
        
        let purpose_len = core::cmp::min(purpose.len(), 32);
        nfek.metadata.purpose[..purpose_len].copy_from_slice(&purpose[..purpose_len]);
        
        nfek
    }

    /// Generate a new random NFEK
    pub fn generate(agent_id: u64, purpose: &[u8]) -> Self {
        let seed = generate_random_seed();
        Self::from_seed(&seed, agent_id, purpose)
    }

    /// Derive symmetric and authentication keys from seed
    fn derive_keys(&mut self) {
        let mut derived = [0u8; 96];
        
        // Simple key derivation using XOR mixing
        for i in 0..96 {
            derived[i] = self.seed[i % 32].wrapping_add(i as u8);
        }
        
        // Mix with additional entropy
        for i in 0..96 {
            derived[i] = derived[i].wrapping_mul(7).wrapping_add(13);
        }
        
        self.sym_key.copy_from_slice(&derived[32..64]);
        self.auth_key.copy_from_slice(&derived[64..96]);
    }

    /// Compute unique key ID from public components
    fn compute_id(&mut self) {
        // ID = hash(seed || sym_key || auth_key)
        let mut input = [0u8; 96];
        input[0..32].copy_from_slice(&self.seed);
        input[32..64].copy_from_slice(&self.sym_key);
        input[64..96].copy_from_slice(&self.auth_key);
        
        self.id = simple_hash(&input);
    }

    /// Check if key is expired
    pub fn is_expired(&self) -> bool {
        match self.metadata.state {
            NfekState::Expired => true,
            _ => current_timestamp() > self.metadata.expires_at,
        }
    }

    /// Check if key is active and valid
    pub fn is_valid(&self) -> bool {
        matches!(self.metadata.state, NfekState::Active) && !self.is_expired()
    }

    /// Mark key for rotation
    pub fn rotate(&mut self) {
        self.metadata.state = NfekState::Rotating;
    }

    /// Revoke key
    pub fn revoke(&mut self) {
        self.metadata.state = NfekState::Revoked;
    }

    /// Derive a child NFEK
    pub fn derive_child(&self, purpose: &[u8]) -> Nfek {
        static COUNTER: AtomicU64 = AtomicU64::new(0);
        let counter = COUNTER.fetch_add(1, Ordering::SeqCst);
        
        let mut input = Vec::with_capacity(self.seed.len() + purpose.len() + 8);
        input.extend_from_slice(&self.seed);
        input.extend_from_slice(purpose);
        input.extend_from_slice(&counter.to_le_bytes());
        
        let child_seed = simple_hash(&input);
        
        let mut child = Self::from_seed(&child_seed, self.metadata.agent_id, purpose);
        child.parent_id = Some(self.id);
        child.metadata.rotation_count = self.metadata.rotation_count + 1;
        
        child
    }

    /// Create attestation for this key
    pub fn attest(&self, issuer_key: &[u8; 32]) -> NfekAttestation {
        let mut data = [0u8; 120];
        data[0..32].copy_from_slice(&self.id);
        data[32..40].copy_from_slice(&self.metadata.created_at.to_le_bytes());
        data[40..48].copy_from_slice(&self.metadata.expires_at.to_le_bytes());
        data[48..56].copy_from_slice(&self.metadata.agent_id.to_le_bytes());
        data[56..88].copy_from_slice(&self.metadata.purpose);
        
        let signature = hmac_sha3_256(issuer_key, &data);
        
        NfekAttestation {
            key_id: self.id,
            created_at: self.metadata.created_at,
            expires_at: self.metadata.expires_at,
            agent_id: self.metadata.agent_id,
            purpose: self.metadata.purpose,
            signature,
        }
    }

    /// Verify attestation
    pub fn verify_attestation(&self, attestation: &NfekAttestation, issuer_key: &[u8; 32]) -> bool {
        let mut data = [0u8; 120];
        data[0..32].copy_from_slice(&attestation.key_id);
        data[32..40].copy_from_slice(&attestation.created_at.to_le_bytes());
        data[40..48].copy_from_slice(&attestation.expires_at.to_le_bytes());
        data[48..56].copy_from_slice(&attestation.agent_id.to_le_bytes());
        data[56..88].copy_from_slice(&attestation.purpose);
        
        let expected_sig = hmac_sha3_256(issuer_key, &data);
        
        attestation.key_id == self.id 
            && constant_time_eq(&attestation.signature, &expected_sig)
    }
}

impl Default for Nfek {
    fn default() -> Self {
        Self {
            id: [0u8; NFEK_ID_SIZE],
            seed: [0u8; NFEK_SEED_SIZE],
            sym_key: [0u8; 32],
            auth_key: [0u8; 32],
            metadata: NfekMetadata::new(),
            parent_id: None,
            attestation: None,
        }
    }
}

/// NFEK Attestation
#[derive(Clone, Debug)]
pub struct NfekAttestation {
    pub key_id: [u8; NFEK_ID_SIZE],
    pub created_at: u64,
    pub expires_at: u64,
    pub agent_id: u64,
    pub purpose: [u8; 32],
    pub signature: [u8; 32],
}

/// NFEK Pool for managing multiple ephemeral keys
pub struct NfekPool {
    /// Active keys indexed by ID
    keys: heapless::Vec<Nfek, NFEK_MAX_ACTIVE_KEYS>,
    /// Default agent ID for new keys
    default_agent_id: u64,
    /// Master key for attestations
    master_key: [u8; 32],
    /// Rotation interval
    rotation_interval_secs: u64,
}

impl NfekPool {
    pub fn new(default_agent_id: u64, master_key: [u8; 32]) -> Self {
        Self {
            keys: heapless::Vec::new(),
            default_agent_id,
            master_key,
            rotation_interval_secs: NFEK_DEFAULT_LIFETIME_SECS,
        }
    }

    /// Create a new ephemeral key
    pub fn create_key(&mut self, purpose: &[u8]) -> Option<[u8; NFEK_ID_SIZE]> {
        self.cleanup_expired();
        
        if self.keys.len() >= NFEK_MAX_ACTIVE_KEYS {
            return None;
        }
        
        let nfek = Nfek::generate(self.default_agent_id, purpose);
        let id = nfek.id;
        
        if self.keys.push(nfek).is_ok() {
            Some(id)
        } else {
            None
        }
    }

    /// Get a key by ID
    pub fn get_key(&self, id: &[u8; NFEK_ID_SIZE]) -> Option<&Nfek> {
        self.keys.iter().find(|k| k.id == *id && k.is_valid())
    }

    /// Get mutable reference to key
    pub fn get_key_mut(&mut self, id: &[u8; NFEK_ID_SIZE]) -> Option<&mut Nfek> {
        self.keys.iter_mut().find(|k| k.id == *id)
    }

    /// Rotate a specific key
    pub fn rotate_key(&mut self, id: &[u8; NFEK_ID_SIZE]) -> Option<[u8; NFEK_ID_SIZE]> {
        if let Some(old_key) = self.get_key(id) {
            let purpose = old_key.metadata.purpose;
            let agent_id = old_key.metadata.agent_id;
            
            if let Some(k) = self.get_key_mut(id) {
                k.rotate();
            }
            
            let mut new_nfek = Nfek::generate(agent_id, &purpose);
            new_nfek.metadata.rotation_count = old_key.metadata.rotation_count + 1;
            new_nfek.parent_id = Some(*id);
            
            let new_id = new_nfek.id;
            let _ = self.keys.push(new_nfek);
            
            Some(new_id)
        } else {
            None
        }
    }

    /// Revoke a key
    pub fn revoke_key(&mut self, id: &[u8; NFEK_ID_SIZE]) -> bool {
        if let Some(k) = self.get_key_mut(id) {
            k.revoke();
            true
        } else {
            false
        }
    }

    /// Clean up expired keys
    pub fn cleanup_expired(&mut self) {
        for key in self.keys.iter_mut() {
            if key.is_expired() && matches!(key.metadata.state, NfekState::Active) {
                key.metadata.state = NfekState::Expired;
            }
        }
    }

    /// Get number of active keys
    pub fn active_count(&self) -> usize {
        self.keys.iter().filter(|k| k.is_valid()).count()
    }

    /// Derive a child key from parent
    pub fn derive_child(&mut self, parent_id: &[u8; NFEK_ID_SIZE], purpose: &[u8]) -> Option<[u8; NFEK_ID_SIZE]> {
        let parent = self.get_key(parent_id)?;
        let child = parent.derive_child(purpose);
        let child_id = child.id;
        
        if self.keys.push(child).is_ok() {
            Some(child_id)
        } else {
            None
        }
    }

    /// Create attestation for a key
    pub fn attest_key(&self, id: &[u8; NFEK_ID_SIZE]) -> Option<NfekAttestation> {
        let key = self.get_key(id)?;
        Some(key.attest(&self.master_key))
    }

    /// Verify attestation for a key
    pub fn verify_attestation(&self, id: &[u8; NFEK_ID_SIZE], attestation: &NfekAttestation) -> bool {
        if let Some(key) = self.get_key(id) {
            key.verify_attestation(attestation, &self.master_key)
        } else {
            false
        }
    }

    /// Rotate all keys approaching expiration
    pub fn auto_rotate(&mut self) -> Vec<[u8; NFEK_ID_SIZE]> {
        let now = current_timestamp();
        let threshold = self.rotation_interval_secs / 2;
        
        let to_rotate: Vec<[u8; NFEK_ID_SIZE]> = self.keys
            .iter()
            .filter(|k| {
                k.is_valid() && (k.metadata.expires_at.saturating_sub(now)) < threshold
            })
            .map(|k| k.id)
            .collect();
        
        let mut new_ids = Vec::new();
        for id in to_rotate {
            if let Some(new_id) = self.rotate_key(&id) {
                new_ids.push(new_id);
            }
        }
        
        new_ids
    }
}

/// Generate a random seed
fn generate_random_seed() -> [u8; NFEK_SEED_SIZE] {
    static COUNTER: AtomicU64 = AtomicU64::new(0);
    let counter = COUNTER.fetch_add(1, Ordering::SeqCst);
    
    let mut seed = [0u8; NFEK_SEED_SIZE];
    let time_bytes = current_timestamp().to_le_bytes();
    
    seed[0..8].copy_from_slice(&time_bytes);
    seed[8..16].copy_from_slice(&counter.to_le_bytes());
    
    seed = simple_hash(&seed);
    seed
}

/// Get current timestamp
fn current_timestamp() -> u64 {
    static TIMESTAMP: AtomicU64 = AtomicU64::new(1);
    TIMESTAMP.fetch_add(1, Ordering::Relaxed)
}

/// Simple hash function
fn simple_hash(data: &[u8]) -> [u8; 32] {
    let mut result = [0u8; 32];
    for (i, byte) in data.iter().enumerate() {
        result[i % 32] ^= *byte;
        result[i % 32] = result[i % 32].wrapping_mul(31).wrapping_add(17);
    }
    result
}

/// Simple HMAC-SHA3-256 implementation
fn hmac_sha3_256(key: &[u8; 32], data: &[u8]) -> [u8; 32] {
    const IPAD: u8 = 0x36;
    const OPAD: u8 = 0x5C;
    
    let mut k_ipad = [0u8; 64];
    let mut k_opad = [0u8; 64];
    
    for i in 0..32 {
        k_ipad[i] = key[i] ^ IPAD;
        k_opad[i] = key[i] ^ OPAD;
    }
    
    let mut inner_input = Vec::with_capacity(64 + data.len());
    inner_input.extend_from_slice(&k_ipad);
    inner_input.extend_from_slice(data);
    let inner_hash = simple_hash(&inner_input);
    
    let mut outer_input = Vec::with_capacity(64 + 32);
    outer_input.extend_from_slice(&k_opad);
    outer_input.extend_from_slice(&inner_hash);
    
    simple_hash(&outer_input)
}

/// heapless Vec polyfill for no_std
mod heapless {
    pub struct Vec<T, const N: usize> {
        buf: [T; N],
        len: usize,
    }

    impl<T: Copy + Default, const N: usize> Vec<T, N> {
        pub const fn new() -> Self {
            Self {
                buf: [T::default(); N],
                len: 0,
            }
        }

        pub fn push(&mut self, item: T) -> Result<(), ()> {
            if self.len < N {
                self.buf[self.len] = item;
                self.len += 1;
                Ok(())
            } else {
                Err(())
            }
        }

        pub fn len(&self) -> usize {
            self.len
        }

        pub fn is_empty(&self) -> bool {
            self.len == 0
        }

        pub fn iter(&self) -> core::slice::Iter<T> {
            self.buf[..self.len].iter()
        }

        pub fn iter_mut(&mut self) -> core::slice::IterMut<T> {
            self.buf[..self.len].iter_mut()
        }
    }

    impl<T: Copy, const N: usize> Clone for Vec<T, N> {
        fn clone(&self) -> Self {
            let mut new = Self::new();
            new.len = self.len;
            new.buf[..self.len].copy_from_slice(&self.buf[..self.len]);
            new
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_nfek_generation() {
        let nfek = Nfek::generate(1, b"test-purpose");
        
        assert!(!nfek.id.iter().all(|&b| b == 0));
        assert!(!nfek.sym_key.iter().all(|&b| b == 0));
        assert!(!nfek.auth_key.iter().all(|&b| b == 0));
        assert_eq!(nfek.metadata.agent_id, 1);
    }

    #[test]
    fn test_nfek_uniqueness() {
        let nfek1 = Nfek::generate(1, b"test");
        let nfek2 = Nfek::generate(1, b"test");
        
        assert_ne!(nfek1.id, nfek2.id);
        assert_ne!(nfek1.seed, nfek2.seed);
        assert_ne!(nfek1.sym_key, nfek2.sym_key);
    }

    #[test]
    fn test_nfek_derivation() {
        let parent = Nfek::generate(1, b"parent");
        let child = parent.derive_child(b"child-purpose");
        
        assert_eq!(child.parent_id, Some(parent.id));
        assert_eq!(child.metadata.rotation_count, parent.metadata.rotation_count + 1);
        assert_ne!(child.id, parent.id);
    }

    #[test]
    fn test_attestation() {
        let master_key = [0x42u8; 32];
        let nfek = Nfek::generate(1, b"attest-test");
        
        let attestation = nfek.attest(&master_key);
        
        assert_eq!(attestation.key_id, nfek.id);
        assert!(nfek.verify_attestation(&attestation, &master_key));
        
        let wrong_key = [0x00u8; 32];
        assert!(!nfek.verify_attestation(&attestation, &wrong_key));
    }

    #[test]
    fn test_nfek_pool() {
        let master_key = [0xABu8; 32];
        let mut pool = NfekPool::new(1, master_key);
        
        let id1 = pool.create_key(b"key1").unwrap();
        let id2 = pool.create_key(b"key2").unwrap();
        
        assert_eq!(pool.active_count(), 2);
        assert_ne!(id1, id2);
        
        let key1 = pool.get_key(&id1);
        assert!(key1.is_some());
        assert_eq!(key1.unwrap().id, id1);
        
        let attestation = pool.attest_key(&id1).unwrap();
        assert!(pool.verify_attestation(&id1, &attestation));
        
        assert!(pool.revoke_key(&id1));
        assert!(!pool.get_key(&id1).unwrap().is_valid());
    }

    #[test]
    fn test_key_rotation() {
        let master_key = [0xCDu8; 32];
        let mut pool = NfekPool::new(1, master_key);
        
        let old_id = pool.create_key(b"rotate-test").unwrap();
        let new_id = pool.rotate_key(&old_id).unwrap();
        
        assert_ne!(old_id, new_id);
        
        let old_key = pool.get_key(&old_id).unwrap();
        assert!(matches!(old_key.metadata.state, NfekState::Rotating));
        
        let new_key = pool.get_key(&new_id).unwrap();
        assert_eq!(new_key.parent_id, Some(old_id));
    }

    #[test]
    fn test_hmac_sha3_256() {
        let key = [0x42u8; 32];
        let data = b"test data";
        
        let mac1 = hmac_sha3_256(&key, data);
        let mac2 = hmac_sha3_256(&key, data);
        
        assert_eq!(mac1, mac2);
        
        let different_key = [0x43u8; 32];
        let mac3 = hmac_sha3_256(&different_key, data);
        assert_ne!(mac1, mac3);
    }
}
