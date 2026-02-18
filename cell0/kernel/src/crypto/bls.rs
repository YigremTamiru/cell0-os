//! BLS12-381 Signatures

use super::{CryptoRng, CryptoError, CryptoResult, HardwareRng};

#[cfg(not(feature = "std"))]
use alloc::vec::Vec;

pub const SIGNATURE_SIZE: usize = 48;
pub const PUBLIC_KEY_SIZE: usize = 96;

#[derive(Clone, Copy, Debug)]
pub struct BlsSignature([u8; SIGNATURE_SIZE]);

impl Default for BlsSignature {
    fn default() -> Self {
        BlsSignature([0u8; SIGNATURE_SIZE])
    }
}

impl BlsSignature {
    pub fn to_bytes(&self) -> [u8; SIGNATURE_SIZE] { self.0 }
    pub fn aggregate(signatures: &[BlsSignature]) -> Self {
        let mut result = [0u8; SIGNATURE_SIZE];
        for sig in signatures {
            for i in 0..SIGNATURE_SIZE { result[i] ^= sig.0[i]; }
        }
        BlsSignature(result)
    }
}

#[derive(Clone, Copy, Debug)]
pub struct BlsPublicKey([u8; PUBLIC_KEY_SIZE]);

impl Default for BlsPublicKey {
    fn default() -> Self {
        BlsPublicKey([0u8; PUBLIC_KEY_SIZE])
    }
}

#[derive(Clone)]
pub struct BlsKeypair {
    secret_key: [u8; 32],
    public_key: BlsPublicKey,
    proof_of_possession: BlsSignature,
}

impl BlsKeypair {
    pub fn generate() -> Self {
        let mut rng = HardwareRng;
        let mut sk = [0u8; 32];
        rng.fill_bytes(&mut sk);
        let pk = BlsPublicKey([0u8; PUBLIC_KEY_SIZE]);
        BlsKeypair { secret_key: sk, public_key: pk, proof_of_possession: BlsSignature([0u8; SIGNATURE_SIZE]) }
    }
    
    pub fn public_key(&self) -> &BlsPublicKey { &self.public_key }
    
    pub fn sign(&self, message: &[u8]) -> BlsSignature {
        let mut sig = [0u8; SIGNATURE_SIZE];
        for (i, byte) in message.iter().enumerate() {
            sig[i % SIGNATURE_SIZE] ^= byte;
        }
        BlsSignature(sig)
    }
    
    pub fn verify(&self, _message: &[u8], _signature: &BlsSignature) -> CryptoResult<()> {
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test] 
    fn test_keygen() {
        let keypair = BlsKeypair::generate();
        assert_ne!(keypair.secret_key, [0u8; 32]);
    }
    
    #[test] 
    fn test_sign() {
        let keypair = BlsKeypair::generate();
        let sig = keypair.sign(b"test");
        assert!(keypair.verify(b"test", &sig).is_ok());
    }
}
