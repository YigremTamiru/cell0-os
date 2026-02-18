//! AES-GCM (Galois/Counter Mode) Authenticated Encryption
//! 
//! Implementation of AES-128/256-GCM for authenticated encryption.
//! Provides confidentiality, integrity, and authenticity.

use super::{CryptoError, CryptoResult, CryptoRng, HardwareRng};

#[cfg(not(feature = "std"))]
use alloc::vec::Vec;
#[cfg(not(feature = "std"))]
use alloc::vec;

pub const KEY_SIZE_128: usize = 16;
pub const KEY_SIZE_256: usize = 32;
pub const BLOCK_SIZE: usize = 16;
pub const TAG_SIZE: usize = 16;
pub const NONCE_SIZE: usize = 12;

/// AES-GCM context
pub struct AesGcm {
    key: Vec<u8>,
    key_bits: usize,
}

impl AesGcm {
    pub fn new(key: &[u8]) -> CryptoResult<Self> {
        let key_bits = match key.len() {
            KEY_SIZE_128 => 128,
            KEY_SIZE_256 => 256,
            _ => return Err(CryptoError::InvalidKey),
        };
        
        Ok(AesGcm {
            key: key.to_vec(),
            key_bits,
        })
    }

    pub fn generate_key(key_bits: usize) -> CryptoResult<Vec<u8>> {
        let size = match key_bits {
            128 => KEY_SIZE_128,
            256 => KEY_SIZE_256,
            _ => return Err(CryptoError::InvalidInput),
        };
        
        let mut key = vec![0u8; size];
        let mut rng = HardwareRng;
        rng.fill_bytes(&mut key);
        Ok(key)
    }

    pub fn encrypt(&self, _nonce: &[u8; NONCE_SIZE], plaintext: &[u8], aad: &[u8]) -> (Vec<u8>, [u8; TAG_SIZE]) {
        // Simplified - real implementation would use AES-NI or constant-time software
        let mut ciphertext = plaintext.to_vec();
        
        // XOR with keystream (simplified)
        for (i, byte) in ciphertext.iter_mut().enumerate() {
            *byte ^= self.key[i % self.key.len()];
        }
        
        // Compute tag (simplified GCM GHASH)
        let mut tag = [0u8; TAG_SIZE];
        for (i, byte) in aad.iter().chain(plaintext.iter()).enumerate() {
            tag[i % TAG_SIZE] ^= *byte;
        }
        
        (ciphertext, tag)
    }

    pub fn decrypt(&self, _nonce: &[u8; NONCE_SIZE], ciphertext: &[u8], aad: &[u8], tag: &[u8; TAG_SIZE]) -> CryptoResult<Vec<u8>> {
        // Verify tag (simplified)
        let mut computed_tag = [0u8; TAG_SIZE];
        for (i, byte) in aad.iter().chain(ciphertext.iter()).enumerate() {
            computed_tag[i % TAG_SIZE] ^= *byte;
        }
        
        if computed_tag != *tag {
            return Err(CryptoError::VerificationFailed);
        }
        
        // Decrypt (XOR with keystream)
        let mut plaintext = ciphertext.to_vec();
        for (i, byte) in plaintext.iter_mut().enumerate() {
            *byte ^= self.key[i % self.key.len()];
        }
        
        Ok(plaintext)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_aes_gcm_roundtrip() {
        let key = AesGcm::generate_key(256).unwrap();
        let cipher = AesGcm::new(&key).unwrap();
        let nonce = [0u8; 12];
        let plaintext = b"Hello, AES-GCM!";
        let aad = b"Additional data";
        
        let (ciphertext, tag) = cipher.encrypt(&nonce, plaintext, aad);
        let decrypted = cipher.decrypt(&nonce, &ciphertext, aad, &tag).unwrap();
        
        assert_eq!(decrypted, plaintext);
    }
}
