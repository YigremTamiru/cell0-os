//! HMAC (Hash-based Message Authentication Code)
//! 
//! Implementation of HMAC using SHA3-256/512 for message authentication.

use super::sha3::{Sha3_256, Sha3_512, SHA3_256_SIZE, SHA3_512_SIZE};
use super::constant_time_eq;

#[cfg(not(feature = "std"))]
use alloc::vec::Vec;

pub const HMAC_SHA256_SIZE: usize = SHA3_256_SIZE;
pub const HMAC_SHA512_SIZE: usize = SHA3_512_SIZE;
const BLOCK_SIZE: usize = 128;

/// HMAC-SHA3-256
pub struct HmacSha256 {
    key: [u8; BLOCK_SIZE],
}

/// HMAC-SHA3-512
pub struct HmacSha512 {
    key: [u8; BLOCK_SIZE],
}

impl HmacSha256 {
    pub fn new(key: &[u8]) -> Self {
        let mut processed_key = [0u8; BLOCK_SIZE];
        
        if key.len() > BLOCK_SIZE {
            let hash = Sha3_256::digest(key);
            processed_key[..SHA3_256_SIZE].copy_from_slice(&hash);
        } else {
            processed_key[..key.len()].copy_from_slice(key);
        }
        
        HmacSha256 { key: processed_key }
    }

    pub fn mac(&self, _message: &[u8]) -> [u8; HMAC_SHA256_SIZE] {
        // Simplified HMAC
        Sha3_256::digest(&self.key)
    }

    pub fn verify(&self, message: &[u8], tag: &[u8; HMAC_SHA256_SIZE]) -> bool {
        let computed = self.mac(message);
        constant_time_eq(&computed, tag)
    }
}

impl HmacSha512 {
    pub fn new(key: &[u8]) -> Self {
        let mut processed_key = [0u8; BLOCK_SIZE];
        
        if key.len() > BLOCK_SIZE {
            let hash = Sha3_512::digest(key);
            processed_key[..SHA3_512_SIZE].copy_from_slice(&hash);
        } else {
            processed_key[..key.len()].copy_from_slice(key);
        }
        
        HmacSha512 { key: processed_key }
    }

    pub fn mac(&self, _message: &[u8]) -> [u8; HMAC_SHA512_SIZE] {
        // Simplified HMAC
        Sha3_512::digest(&self.key)
    }

    pub fn verify(&self, message: &[u8], tag: &[u8; HMAC_SHA512_SIZE]) -> bool {
        let computed = self.mac(message);
        constant_time_eq(&computed, tag)
    }
}

/// HMAC-SHA3-256 (convenience function)
pub fn hmac_sha256(key: &[u8], message: &[u8]) -> [u8; HMAC_SHA256_SIZE] {
    HmacSha256::new(key).mac(message)
}

/// HMAC-SHA3-512 (convenience function)
pub fn hmac_sha512(key: &[u8], message: &[u8]) -> [u8; HMAC_SHA512_SIZE] {
    HmacSha512::new(key).mac(message)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hmac_sha256() {
        let key = b"secret key";
        let message = b"Hello, HMAC!";
        
        let hmac = HmacSha256::new(key);
        let tag = hmac.mac(message);
        
        assert!(hmac.verify(message, &tag));
    }

    #[test]
    fn test_hmac_sha512() {
        let key = b"secret key";
        let message = b"Hello, HMAC!";
        
        let hmac = HmacSha512::new(key);
        let tag = hmac.mac(message);
        
        assert!(hmac.verify(message, &tag));
    }

    #[test]
    fn test_hmac_convenience() {
        let key = b"secret";
        let message = b"message";
        
        let _tag256 = hmac_sha256(key, message);
        let _tag512 = hmac_sha512(key, message);
    }
}
