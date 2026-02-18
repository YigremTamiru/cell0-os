//! Cell0 Cryptographic System
//!
//! ⚠️  SECURITY WARNING: THIS MODULE CONTAINS PLACEHOLDER/STUB IMPLEMENTATIONS
//!     Ed25519, Kyber, and Dilithium modules use simplified XOR-based stubs
//!     that DO NOT provide actual cryptographic security. DO NOT USE for
//!     production security operations until real crypto libraries are integrated.
//!
//! A comprehensive cryptographic primitive system providing:
//! - Classical: AES-GCM, ChaCha20-Poly1305, SHA-3, HMAC, ECDSA
//! - Modern: Ed25519, X25519, BLS12-381
//! - Post-Quantum: CRYSTALS-Kyber, CRYSTALS-Dilithium
//! - Quantum: BB84 QKD simulation (in quantum module)
//!
//! # Architecture
//! ```
//! ┌─────────────────────────────────────────────────────────────┐
//! │                    CRYPTO AGILITY LAYER                      │
//! │         (Algorithm Negotiation, Fallback, Inventory)         │
//! ├─────────────────────────────────────────────────────────────┤
//! │  CLASSICAL  │   MODERN    │  POST-QUANTUM  │    QUANTUM     │
//! │  AES-GCM    │  Ed25519    │   Kyber KEM    │   BB84 QKD     │
//! │  ChaCha20   │  X25519     │   Dilithium    │   E91 Protocol │
//! │  SHA-3      │  BLS12-381  │   SPHINCS+     │   QKD Manager  │
//! └─────────────────────────────────────────────────────────────┘
//! ```
//!
//! # TODO: Integrate Real Crypto Libraries
//! - [ ] ed25519-dalek for Ed25519 signatures
//! - [ ] pqc-kyber for Kyber KEM
//! - [ ] pqc-dilithium for Dilithium signatures
//! - [ ] sha2 for SHA-256/SHA-512

// Import alloc for no_std environments
#[cfg(not(feature = "std"))]
extern crate alloc;

// Re-export alloc types for crypto modules
#[cfg(not(feature = "std"))]
pub mod alloc_prelude {
    pub use alloc::vec::Vec;
    pub use alloc::vec;
    pub use alloc::string::{String, ToString};
    pub use alloc::boxed::Box;
    pub use alloc::format;
    pub use alloc::borrow::ToOwned;
}

#[cfg(feature = "std")]
pub mod alloc_prelude {
    pub use std::vec::Vec;
    pub use std::vec;
    pub use std::string::{String, ToString};
    pub use std::boxed::Box;
    pub use std::format;
    pub use std::borrow::ToOwned;
}

// Compile-time guard: Prevent production builds with stub crypto
// To build with real crypto, define the 'production-crypto' feature
#[cfg(all(feature = "production", not(feature = "production-crypto")))]
compile_error!("Production builds require real cryptographic implementations. \
    Either enable 'production-crypto' feature or build without 'production' feature. \
    See kernel/src/crypto/mod.rs for integration instructions.");

// Re-export individual crypto modules
pub mod aes_gcm;
pub mod chacha20;
pub mod sha3;
pub mod hmac;
pub mod ecdsa;
pub mod ed25519;
pub mod x25519;
pub mod bls;
pub mod kyber;
pub mod dilithium;
pub mod zkstark;
pub mod secure_boot;
pub mod tpm;
pub mod agility;
pub mod qkd;

use core::fmt;

/// Cryptographic error types
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CryptoError {
    InvalidKey,
    InvalidSignature,
    VerificationFailed,
    EncryptionFailed,
    DecryptionFailed,
    InvalidInput,
    BufferTooSmall,
    AlgorithmNotSupported,
    QuantumChannelCompromised,
    SecureBootViolation,
    TpmError,
    AgilityNegotiationFailed,
}

impl fmt::Display for CryptoError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CryptoError::InvalidKey => write!(f, "Invalid cryptographic key"),
            CryptoError::InvalidSignature => write!(f, "Invalid signature format"),
            CryptoError::VerificationFailed => write!(f, "Signature verification failed"),
            CryptoError::EncryptionFailed => write!(f, "Encryption operation failed"),
            CryptoError::DecryptionFailed => write!(f, "Decryption operation failed"),
            CryptoError::InvalidInput => write!(f, "Invalid input parameters"),
            CryptoError::BufferTooSmall => write!(f, "Output buffer too small"),
            CryptoError::AlgorithmNotSupported => write!(f, "Algorithm not supported"),
            CryptoError::QuantumChannelCompromised => write!(f, "QKD channel may be compromised"),
            CryptoError::SecureBootViolation => write!(f, "Secure boot verification failed"),
            CryptoError::TpmError => write!(f, "TPM operation failed"),
            CryptoError::AgilityNegotiationFailed => write!(f, "Crypto agility negotiation failed"),
        }
    }
}

/// Result type alias for crypto operations
pub type CryptoResult<T> = Result<T, CryptoError>;

/// Security level classification
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u16)]
pub enum SecurityLevel {
    /// 128-bit security (e.g., AES-128, Curve25519)
    Bits128 = 128,
    /// 192-bit security (e.g., AES-192)
    Bits192 = 192,
    /// 256-bit security (e.g., AES-256, Ed25519)
    Bits256 = 256,
    /// Post-quantum 128-bit security
    PostQuantum128 = 256 + 128,
    /// Post-quantum 256-bit security
    PostQuantum256 = 512 + 256,
}

/// Algorithm categories
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AlgorithmCategory {
    SymmetricEncryption,
    AsymmetricEncryption,
    Signature,
    KeyExchange,
    Hash,
    Mac,
    Kdf,
    QuantumKeyDistribution,
    ZeroKnowledgeProof,
}

/// Algorithm identifier for agility framework
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u16)]
pub enum AlgorithmId {
    // Symmetric encryption
    Aes128Gcm = 0x0101,
    Aes256Gcm = 0x0102,
    ChaCha20Poly1305 = 0x0103,
    
    // Asymmetric encryption/KEM
    Kyber512 = 0x0201,
    Kyber768 = 0x0202,
    Kyber1024 = 0x0203,
    
    // Signatures
    EcdsaSecp256k1 = 0x0301,
    EcdsaP256 = 0x0302,
    Ed25519 = 0x0303,
    Dilithium2 = 0x0304,
    Dilithium3 = 0x0305,
    Dilithium5 = 0x0306,
    Bls12_381 = 0x0307,
    
    // Key exchange
    X25519 = 0x0401,
    
    // Hashes
    Sha3_256 = 0x0501,
    Sha3_512 = 0x0502,
    Shake128 = 0x0503,
    Shake256 = 0x0504,
    
    // MACs
    HmacSha256 = 0x0601,
    HmacSha512 = 0x0602,
    
    // QKD
    Bb84 = 0x0701,
    E91 = 0x0702,
    
    // ZKP
    ZkStark = 0x0801,
}

/// Trait for all cryptographic primitives
pub trait CryptoPrimitive: Send + Sync {
    /// Get algorithm identifier
    fn algorithm_id(&self) -> AlgorithmId;
    
    /// Get security level
    fn security_level(&self) -> SecurityLevel;
    
    /// Get algorithm category
    fn category(&self) -> AlgorithmCategory;
    
    /// Get algorithm name
    fn name(&self) -> &'static str;
}

/// Constant-time comparison to prevent timing attacks
pub fn constant_time_eq(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut result = 0u8;
    for (x, y) in a.iter().zip(b.iter()) {
        result |= x ^ y;
    }
    result == 0
}

/// Secure memory clearing
pub fn secure_clear(bytes: &mut [u8]) {
    for byte in bytes.iter_mut() {
        *byte = 0;
    }
    core::sync::atomic::fence(core::sync::atomic::Ordering::SeqCst);
}

/// Random number generator interface
pub trait CryptoRng {
    fn fill_bytes(&mut self, dest: &mut [u8]);
}

/// Hardware-backed RNG (placeholder for actual hardware RNG)
pub struct HardwareRng;

impl CryptoRng for HardwareRng {
    fn fill_bytes(&mut self, dest: &mut [u8]) {
        // In real implementation, this would use RDRAND or hardware TRNG
        // For now, use a placeholder that should be replaced
        for (i, byte) in dest.iter_mut().enumerate() {
            *byte = (i * 7 + 13) as u8;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_constant_time_eq() {
        let a = [1, 2, 3, 4, 5];
        let b = [1, 2, 3, 4, 5];
        let c = [1, 2, 3, 4, 6];
        
        assert!(constant_time_eq(&a, &b));
        assert!(!constant_time_eq(&a, &c));
        assert!(!constant_time_eq(&a, &b[..4]));
    }

    #[test]
    fn test_secure_clear() {
        let mut data = [0u8; 32];
        data.copy_from_slice(&[0xFF; 32]);
        secure_clear(&mut data);
        assert_eq!(data, [0u8; 32]);
    }
}
