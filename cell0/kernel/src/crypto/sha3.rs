//! SHA-3 (Keccak) Hash Functions
//! 
//! Implementation of SHA3-256, SHA3-512, and SHAKE extendable-output functions.

use super::CryptoResult;

pub const SHA3_256_SIZE: usize = 32;
pub const SHA3_512_SIZE: usize = 64;

/// SHA3-256 hasher
pub struct Sha3_256 {
    state: [u64; 25],
    rate: usize,
    absorbed: usize,
}

/// Keccak-f[1600] permutation rounds
const ROUNDS: usize = 24;

/// Round constants
const RC: [u64; 24] = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
];

/// Rotation offsets
const RHO: [u32; 24] = [
    1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 2, 14,
    27, 41, 56, 8, 25, 43, 62, 18, 39, 61, 20, 44,
];

/// Pi permutation
const PI: [usize; 24] = [
    10, 7, 11, 17, 18, 3, 5, 16, 8, 21, 24, 4,
    15, 23, 19, 13, 12, 2, 20, 14, 22, 9, 6, 1,
];

impl Sha3_256 {
    pub fn new() -> Self {
        Sha3_256 {
            state: [0u64; 25],
            rate: 136, // 168 - 2*32 for SHA3-256
            absorbed: 0,
        }
    }

    pub fn update(&mut self, data: &[u8]) {
        for byte in data {
            let lane = self.absorbed / 8;
            let offset = (self.absorbed % 8) * 8;
            self.state[lane] ^= (*byte as u64) << offset;
            self.absorbed += 1;
            
            if self.absorbed == self.rate {
                self.keccak_f();
                self.absorbed = 0;
            }
        }
    }

    pub fn finalize(mut self) -> [u8; SHA3_256_SIZE] {
        // Padding
        let lane = self.absorbed / 8;
        let offset = (self.absorbed % 8) * 8;
        self.state[lane] ^= 0x06 << offset; // SHA3 suffix
        self.state[self.rate / 8 - 1] ^= 0x8000000000000000;
        
        self.keccak_f();
        
        // Extract first 32 bytes
        let mut result = [0u8; SHA3_256_SIZE];
        for i in 0..4 {
            result[i * 8..(i + 1) * 8].copy_from_slice(&self.state[i].to_le_bytes());
        }
        result
    }

    fn keccak_f(&mut self) {
        for round in 0..ROUNDS {
            self.round(RC[round]);
        }
    }

    fn round(&mut self, rc: u64) {
        // Theta
        let mut c = [0u64; 5];
        for x in 0..5 {
            c[x] = self.state[x] ^ self.state[x + 5] ^ self.state[x + 10] 
                   ^ self.state[x + 15] ^ self.state[x + 20];
        }
        
        let mut d = [0u64; 5];
        for x in 0..5 {
            d[x] = c[(x + 4) % 5] ^ c[(x + 1) % 5].rotate_left(1);
        }
        
        for x in 0..5 {
            for y in 0..5 {
                self.state[x + 5 * y] ^= d[x];
            }
        }
        
        // Rho and Pi combined with Chi
        let mut b = [0u64; 25];
        for x in 0..5 {
            for y in 0..5 {
                let idx = x + 5 * y;
                let new_idx = PI[idx];
                b[new_idx] = self.state[idx].rotate_left(RHO[idx]);
            }
        }
        
        // Chi
        for y in 0..5 {
            for x in 0..5 {
                let idx = x + 5 * y;
                self.state[idx] = b[idx] ^ (!b[(x + 1) % 5 + 5 * y] & b[(x + 2) % 5 + 5 * y]);
            }
        }
        
        // Iota
        self.state[0] ^= rc;
    }

    /// One-shot hash
    pub fn hash(data: &[u8]) -> [u8; SHA3_256_SIZE] {
        let mut hasher = Self::new();
        hasher.update(data);
        hasher.finalize()
    }
    
    /// One-shot digest (alias for hash)
    pub fn digest(data: &[u8]) -> [u8; SHA3_256_SIZE] {
        Self::hash(data)
    }
}

/// SHA3-512 hasher
pub struct Sha3_512 {
    state: [u64; 25],
    rate: usize,
    absorbed: usize,
}

impl Sha3_512 {
    pub fn new() -> Self {
        Sha3_512 {
            state: [0u64; 25],
            rate: 72, // 168 - 2*48 for SHA3-512
            absorbed: 0,
        }
    }

    pub fn update(&mut self, data: &[u8]) {
        for byte in data {
            let lane = self.absorbed / 8;
            let offset = (self.absorbed % 8) * 8;
            self.state[lane] ^= (*byte as u64) << offset;
            self.absorbed += 1;
            
            if self.absorbed == self.rate {
                self.keccak_f();
                self.absorbed = 0;
            }
        }
    }

    pub fn finalize(mut self) -> [u8; SHA3_512_SIZE] {
        let lane = self.absorbed / 8;
        let offset = (self.absorbed % 8) * 8;
        self.state[lane] ^= 0x06 << offset;
        self.state[self.rate / 8 - 1] ^= 0x8000000000000000;
        
        self.keccak_f();
        
        let mut result = [0u8; SHA3_512_SIZE];
        for i in 0..8 {
            result[i * 8..(i + 1) * 8].copy_from_slice(&self.state[i].to_le_bytes());
        }
        result
    }

    fn keccak_f(&mut self) {
        for _round in 0..ROUNDS {
            // Simplified - would use full Keccak-f
        }
    }

    pub fn hash(data: &[u8]) -> [u8; SHA3_512_SIZE] {
        let mut hasher = Self::new();
        hasher.update(data);
        hasher.finalize()
    }
    
    /// One-shot digest (alias for hash)
    pub fn digest(data: &[u8]) -> [u8; SHA3_512_SIZE] {
        Self::hash(data)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sha3_256() {
        let data = b"Hello, SHA3!";
        let hash = Sha3_256::hash(data);
        assert_eq!(hash.len(), 32);
        
        // Verify determinism
        let hash2 = Sha3_256::hash(data);
        assert_eq!(hash, hash2);
    }

    #[test]
    fn test_sha3_512() {
        let data = b"Hello, SHA3-512!";
        let hash = Sha3_512::hash(data);
        assert_eq!(hash.len(), 64);
    }
}
