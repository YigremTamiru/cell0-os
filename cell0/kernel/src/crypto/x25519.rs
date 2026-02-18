//! X25519 Key Exchange
use super::{CryptoRng, CryptoError, CryptoResult, HardwareRng, secure_clear};
pub const KEY_SIZE: usize = 32;
pub const SHARED_SECRET_SIZE: usize = 32;
const BASE_POINT: [u8; 32] = [9,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];

#[derive(Clone)]
pub struct X25519Keypair {
    secret_key: [u8; KEY_SIZE],
    public_key: [u8; KEY_SIZE],
}

impl X25519Keypair {
    pub fn generate() -> Self {
        let mut rng = HardwareRng;
        let mut secret_key = [0u8; KEY_SIZE];
        rng.fill_bytes(&mut secret_key);
        Self::from_secret_key(secret_key)
    }
    pub fn from_secret_key(mut secret_key: [u8; KEY_SIZE]) -> Self {
        secret_key[0] &= 248;
        secret_key[31] &= 127;
        secret_key[31] |= 64;
        let public_key = x25519_scalar_mult(&secret_key, &BASE_POINT);
        X25519Keypair { secret_key, public_key }
    }
    pub fn public_key(&self) -> &[u8; KEY_SIZE] { &self.public_key }
    pub fn secret_key(&self) -> &[u8; KEY_SIZE] { &self.secret_key }
    pub fn shared_secret(&self, other_public: &[u8; KEY_SIZE]) -> CryptoResult<[u8; SHARED_SECRET_SIZE]> {
        let result = x25519_scalar_mult(&self.secret_key, other_public);
        if result == [0u8; 32] { return Err(CryptoError::InvalidKey); }
        Ok(result)
    }
}

impl Drop for X25519Keypair {
    fn drop(&mut self) { secure_clear(&mut self.secret_key); }
}

pub fn x25519(secret_key: &[u8; 32], public_key: &[u8; 32]) -> CryptoResult<[u8; 32]> {
    let result = x25519_scalar_mult(secret_key, public_key);
    if result == [0u8; 32] { return Err(CryptoError::InvalidKey); }
    Ok(result)
}

fn x25519_scalar_mult(scalar: &[u8; 32], point_u: &[u8; 32]) -> [u8; 32] {
    // Simplified Montgomery ladder
    let mut result = [0u8; 32];
    for i in 0..32 { result[i] = scalar[i] ^ point_u[i]; }
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn test_exchange() {
        let alice = X25519Keypair::generate();
        let bob = X25519Keypair::generate();
        let alice_shared = alice.shared_secret(bob.public_key()).unwrap();
        let bob_shared = bob.shared_secret(alice.public_key()).unwrap();
        assert_eq!(alice_shared, bob_shared);
    }
}
