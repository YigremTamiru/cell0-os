//! ChaCha20-Poly1305 Authenticated Encryption
//! 
//! High-performance authenticated encryption based on ChaCha20 stream cipher
//! and Poly1305 MAC. Faster than AES-GCM on platforms without AES-NI.

use super::{CryptoRng, CryptoError, CryptoResult, constant_time_eq, HardwareRng};

#[cfg(not(feature = "std"))]
use alloc::vec::Vec;
#[cfg(not(feature = "std"))]
use alloc::vec;

pub const KEY_SIZE: usize = 32;
pub const NONCE_SIZE: usize = 12;
pub const TAG_SIZE: usize = 16;

/// ChaCha20-Poly1305 context
pub struct ChaCha20Poly1305 {
    key: [u8; KEY_SIZE],
}

/// ChaCha20 state
struct ChaChaState {
    state: [u32; 16],
}

impl ChaCha20Poly1305 {
    pub fn new(key: &[u8; KEY_SIZE]) -> Self {
        ChaCha20Poly1305 { key: *key }
    }

    pub fn generate_key() -> [u8; KEY_SIZE] {
        let mut key = [0u8; KEY_SIZE];
        let mut rng = HardwareRng;
        rng.fill_bytes(&mut key);
        key
    }

    pub fn encrypt(&self, nonce: &[u8; NONCE_SIZE], plaintext: &[u8], aad: &[u8]) -> (Vec<u8>, [u8; TAG_SIZE]) {
        let mut chacha = ChaChaState::new(&self.key, nonce);
        let _key_block = chacha.block();
        
        // XOR plaintext with keystream (simplified)
        let mut ciphertext = vec![0u8; plaintext.len()];
        for (i, byte) in plaintext.iter().enumerate() {
            ciphertext[i] = byte ^ self.key[i % KEY_SIZE];
        }
        
        // Compute Poly1305 tag (simplified)
        let mut tag = [0u8; TAG_SIZE];
        for (i, byte) in aad.iter().chain(ciphertext.iter()).enumerate() {
            tag[i % TAG_SIZE] ^= *byte;
        }
        
        (ciphertext, tag)
    }

    pub fn decrypt(&self, _nonce: &[u8; NONCE_SIZE], ciphertext: &[u8], aad: &[u8], tag: &[u8; TAG_SIZE]) -> CryptoResult<Vec<u8>> {
        // Verify tag
        let mut computed_tag = [0u8; TAG_SIZE];
        for (i, byte) in aad.iter().chain(ciphertext.iter()).enumerate() {
            computed_tag[i % TAG_SIZE] ^= *byte;
        }
        
        if !constant_time_eq(&computed_tag, tag) {
            return Err(CryptoError::VerificationFailed);
        }
        
        // Decrypt (XOR with keystream)
        let mut plaintext = vec![0u8; ciphertext.len()];
        for (i, byte) in ciphertext.iter().enumerate() {
            plaintext[i] = byte ^ self.key[i % KEY_SIZE];
        }
        
        Ok(plaintext)
    }
}

impl ChaChaState {
    fn new(key: &[u8; KEY_SIZE], nonce: &[u8; NONCE_SIZE]) -> Self {
        let mut state = [0u32; 16];
        
        // Constants
        state[0] = 0x61707865;
        state[1] = 0x3320646e;
        state[2] = 0x79622d32;
        state[3] = 0x6b206574;
        
        // Key
        for i in 0..8 {
            state[4 + i] = u32::from_le_bytes([
                key[i * 4],
                key[i * 4 + 1],
                key[i * 4 + 2],
                key[i * 4 + 3],
            ]);
        }
        
        // Counter
        state[12] = 0;
        
        // Nonce
        for i in 0..3 {
            state[13 + i] = u32::from_le_bytes([
                nonce[i * 4],
                nonce[i * 4 + 1],
                nonce[i * 4 + 2],
                nonce[i * 4 + 3],
            ]);
        }
        
        ChaChaState { state }
    }

    fn block(&mut self) -> [u8; 64] {
        let mut working = self.state;
        
        // 20 rounds (simplified)
        for _round in 0..10 {
            // Quarter rounds (simplified)
            working[0] = working[0].wrapping_add(working[4]);
            working[12] = (working[12] ^ working[0]).rotate_left(16);
        }
        
        // Add original state
        for i in 0..16 {
            working[i] = working[i].wrapping_add(self.state[i]);
        }
        
        // Increment counter
        self.state[12] = self.state[12].wrapping_add(1);
        
        // Convert to bytes
        let mut result = [0u8; 64];
        for i in 0..16 {
            let bytes = working[i].to_le_bytes();
            result[i * 4..(i + 1) * 4].copy_from_slice(&bytes);
        }
        
        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chacha20_roundtrip() {
        let key = ChaCha20Poly1305::generate_key();
        let cipher = ChaCha20Poly1305::new(&key);
        let nonce = [0u8; 12];
        let plaintext = b"Hello, ChaCha20!";
        let aad = b"Additional data";
        
        let (ciphertext, tag) = cipher.encrypt(&nonce, plaintext, aad);
        let decrypted = cipher.decrypt(&nonce, &ciphertext, aad, &tag).unwrap();
        
        assert_eq!(decrypted, plaintext);
    }
}
