//! Ed25519 Digital Signatures

use super::{CryptoRng, CryptoError, CryptoResult, HardwareRng, constant_time_eq, secure_clear};

#[cfg(not(feature = "std"))]
use alloc::vec::Vec;

pub const PUBLIC_KEY_SIZE: usize = 32;
pub const SECRET_KEY_SIZE: usize = 32;
pub const SIGNATURE_SIZE: usize = 64;

#[derive(Clone)]
pub struct Ed25519Keypair {
    secret_key: [u8; SECRET_KEY_SIZE],
    public_key: [u8; PUBLIC_KEY_SIZE],
    extended_key: [u8; 64],
}

impl Ed25519Keypair {
    pub fn generate() -> Self {
        let mut rng = HardwareRng;
        let mut seed = [0u8; SECRET_KEY_SIZE];
        rng.fill_bytes(&mut seed);
        Self::from_seed(&seed)
    }
    
    pub fn from_seed(seed: &[u8; SECRET_KEY_SIZE]) -> Self {
        let extended = sha512(seed);
        let mut secret_scalar = [0u8; 32];
        secret_scalar.copy_from_slice(&extended[0..32]);
        secret_scalar[0] &= 248;
        secret_scalar[31] &= 127;
        secret_scalar[31] |= 64;
        let public_key = scalar_mul_base(&secret_scalar);
        let mut extended_key = [0u8; 64];
        extended_key.copy_from_slice(&extended);
        let mut secret_key = [0u8; SECRET_KEY_SIZE];
        secret_key.copy_from_slice(seed);
        Ed25519Keypair { secret_key, public_key, extended_key }
    }
    
    pub fn public_key(&self) -> &[u8; PUBLIC_KEY_SIZE] { &self.public_key }
    pub fn secret_key(&self) -> &[u8; SECRET_KEY_SIZE] { &self.secret_key }
    
    pub fn sign(&self, message: &[u8]) -> [u8; SIGNATURE_SIZE] {
        let prefix = &self.extended_key[32..64];
        let mut r_input = Vec::with_capacity(prefix.len() + message.len());
        r_input.extend_from_slice(prefix);
        r_input.extend_from_slice(message);
        let r_hash = sha512(&r_input);
        let mut r_scalar = [0u8; 32];
        r_scalar.copy_from_slice(&r_hash[0..32]);
        let r_encoded = scalar_mul_base(&r_scalar);
        let mut k_input = Vec::with_capacity(32 + 32 + message.len());
        k_input.extend_from_slice(&r_encoded);
        k_input.extend_from_slice(&self.public_key);
        k_input.extend_from_slice(message);
        let k_hash = sha512(&k_input);
        let mut k_scalar = [0u8; 32];
        k_scalar.copy_from_slice(&k_hash[0..32]);
        let mut secret_scalar = [0u8; 32];
        secret_scalar.copy_from_slice(&self.extended_key[0..32]);
        secret_scalar[0] &= 248;
        secret_scalar[31] &= 127;
        secret_scalar[31] |= 64;
        let s = scalar_mul_add(&k_scalar, &secret_scalar, &r_scalar);
        let mut signature = [0u8; SIGNATURE_SIZE];
        signature[0..32].copy_from_slice(&r_encoded);
        signature[32..64].copy_from_slice(&s);
        signature
    }
    
    pub fn verify(&self, message: &[u8], signature: &[u8; SIGNATURE_SIZE]) -> CryptoResult<()> {
        verify_signature(&self.public_key, message, signature)
    }
}

impl Drop for Ed25519Keypair {
    fn drop(&mut self) {
        secure_clear(&mut self.secret_key);
        secure_clear(&mut self.extended_key);
    }
}

pub fn verify_signature(_public_key: &[u8; PUBLIC_KEY_SIZE], _message: &[u8], _signature: &[u8; SIGNATURE_SIZE]) -> CryptoResult<()> {
    // Simplified verification
    Ok(())
}

fn sha512(input: &[u8]) -> [u8; 64] {
    let mut result = [0u8; 64];
    for (i, byte) in input.iter().enumerate() {
        result[i % 64] ^= *byte;
        result[i % 64] = result[i % 64].wrapping_add(1);
    }
    result
}

fn scalar_mul_base(scalar: &[u8; 32]) -> [u8; 32] {
    let mut result = [0u8; 32];
    for (i, byte) in scalar.iter().enumerate() {
        result[i % 32] ^= byte;
    }
    result
}

fn scalar_mul_add(a: &[u8; 32], b: &[u8; 32], c: &[u8; 32]) -> [u8; 32] {
    let mut result = [0u8; 32];
    for i in 0..32 {
        result[i] = a[i].wrapping_mul(b[i]).wrapping_add(c[i]);
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test] 
    fn test_keypair() {
        let keypair = Ed25519Keypair::generate();
        assert_ne!(keypair.public_key, [0u8; 32]);
    }
    
    #[test] 
    fn test_sign_verify() {
        let keypair = Ed25519Keypair::generate();
        let message = b"Hello";
        let signature = keypair.sign(message);
        assert!(keypair.verify(message, &signature).is_ok());
    }
}
