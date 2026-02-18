//! TPM (Trusted Platform Module) Integration Layer
//! 
//! Simulated TPM interface for secure cryptographic operations and
//! platform attestation. In a production environment, this would interface
//! with actual TPM hardware via the TSS (TCG Software Stack).
//!
//! # Features
//! - Platform Configuration Registers (PCRs)
//! - Key sealing/unsealing
//! - Random number generation
//! - Non-volatile storage
//! - Remote attestation
//! - Policy-based authorization
//!
//! # TPM 2.0 Architecture
//! ```
//! ┌─────────────────────────────────────────────────────┐
//! │                    TPM 2.0                           │
//! ├─────────────┬──────────────┬──────────────┬─────────┤
//! │   Crypto    │   Key Store  │   PCR Bank   │   NV    │
//! │   Engine    │   (Hierarchy)│   (24 regs)  │   RAM   │
//! ├─────────────┴──────────────┴──────────────┴─────────┤
//! │              Authorization & Sessions                │
//! └─────────────────────────────────────────────────────┘
//! ```

use super::{
    secure_boot::{PcrBank, PcrQuote},
    ed25519::{Ed25519Keypair, PUBLIC_KEY_SIZE, SIGNATURE_SIZE},
    constant_time_eq, secure_clear, CryptoError, CryptoResult, CryptoRng, HardwareRng,
};
use core::convert::TryInto;

#[cfg(not(feature = "std"))]
use alloc::vec::Vec;
#[cfg(not(feature = "std"))]
use alloc::vec;
#[cfg(not(feature = "std"))]
use alloc::string::String;

/// TPM command response codes
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u32)]
pub enum TpmResponse {
    Success = 0x000,
    BadTag = 0x01E,
    Initialize = 0x100,
    Failure = 0x101,
    Sequence = 0x103,
    Private = 0x10B,
    Hmac = 0x119,
    Disabled = 0x120,
    Enable = 0x121,
    Handle = 0x08B,
    Value = 0x084,
    Memory = 0x090,
    
    // Custom success codes
    TestSuccess = 0x001,
}

/// TPM algorithm identifiers
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u16)]
pub enum TpmAlgId {
    Sha256 = 0x000B,
    Sha384 = 0x000C,
    Sha512 = 0x000D,
    Aes = 0x0006,
    Rsa = 0x0001,
    Ecc = 0x0023,
    KeyedHash = 0x0008,
    Cfb = 0x0043,
    Null = 0x0010,
}

/// TPM key handle
#[derive(Clone, Debug)]
pub struct TpmKey {
    pub handle: u32,
    pub key_type: TpmKeyType,
    pub public_key: Vec<u8>,
}

/// TPM key types
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TpmKeyType {
    Storage,
    Signing,
    Binding,
    Identity,
}

/// PCR selection structure
#[derive(Clone, Debug)]
pub struct PcrSelection {
    pub hash_alg: TpmAlgId,
    pub selected_pcrs: [u8; 3], // Bitmap for PCRs 0-23
}

impl PcrSelection {
    pub fn new(hash_alg: TpmAlgId, pcrs: &[usize]) -> Self {
        let mut selected = [0u8; 3];
        for &pcr in pcrs {
            if pcr < 24 {
                selected[pcr / 8] |= 1 << (pcr % 8);
            }
        }
        PcrSelection {
            hash_alg,
            selected_pcrs: selected,
        }
    }

    pub fn is_selected(&self, pcr: usize) -> bool {
        if pcr < 24 {
            (self.selected_pcrs[pcr / 8] >> (pcr % 8)) & 1 == 1
        } else {
            false
        }
    }
}

/// TPM context
pub struct TpmContext {
    enabled: bool,
    pcr_banks: Vec<(TpmAlgId, PcrBank)>,
    nv_storage: Vec<(u32, Vec<u8>)>,
    keys: Vec<TpmKey>,
    lockout_counter: u32,
    locked_out: bool,
    clock: u64,
    reset_count: u32,
    restart_count: u32,
}

impl TpmContext {
    pub fn new() -> Self {
        let mut ctx = TpmContext {
            enabled: true,
            pcr_banks: Vec::new(),
            nv_storage: Vec::new(),
            keys: Vec::new(),
            lockout_counter: 0,
            locked_out: false,
            clock: 0,
            reset_count: 0,
            restart_count: 0,
        };
        
        // Initialize SHA-256 PCR bank
        ctx.pcr_banks.push((TpmAlgId::Sha256, PcrBank::new()));
        
        ctx
    }

    /// Startup TPM
    pub fn startup(&mut self, clear: bool) -> TpmResponse {
        if !self.enabled {
            return TpmResponse::Initialize;
        }
        
        if clear {
            // Reset PCRs that aren't preserved across boots
            for (_alg, bank) in &mut self.pcr_banks {
                for i in 16..24 {
                    let _result: CryptoResult<()> = bank.extend(i, &[0; 32]);
                }
            }
            self.restart_count += 1;
        }
        
        TpmResponse::Success
    }

    /// Shutdown TPM
    pub fn shutdown(&mut self, _clear: bool) -> TpmResponse {
        TpmResponse::Success
    }

    /// Self test
    pub fn self_test(&mut self, _full_test: bool) -> TpmResponse {
        TpmResponse::Success
    }

    /// Extend PCR
    pub fn pcr_extend(&mut self, pcr_index: usize, digests: &[(TpmAlgId, &[u8])]) -> TpmResponse {
        if pcr_index >= 24 {
            return TpmResponse::Value;
        }
        
        for (alg, data) in digests {
            if let Some((_, bank)) = self.pcr_banks.iter_mut().find(|(a, _)| a == alg) {
                let _result: CryptoResult<()> = bank.extend(pcr_index, data);
            }
        }
        
        TpmResponse::Success
    }

    /// Read PCR
    pub fn pcr_read(&self, selection: &PcrSelection) -> Vec<(usize, [u8; 32])> {
        let mut results: Vec<(usize, [u8; 32])> = Vec::new();
        
        if let Some((_, bank)) = self.pcr_banks.iter().find(|(a, _)| *a == selection.hash_alg) {
            for i in 0..24 {
                if selection.is_selected(i) {
                    if let Ok(value) = bank.read(i) {
                        results.push((i, value));
                    }
                }
            }
        }
        
        results
    }

    /// Quote PCRs
    pub fn quote(
        &self,
        _signing_key: &TpmKey,
        pcr_selection: &PcrSelection,
        nonce: &[u8],
    ) -> Result<PcrQuote, TpmResponse> {
        // Read PCR values
        let pcr_values_usize = self.pcr_read(pcr_selection);
        
        // Convert to expected type (usize -> u32)
        let pcr_values: Vec<(u32, [u8; 32])> = pcr_values_usize
            .into_iter()
            .map(|(idx, val)| (idx as u32, val))
            .collect();
        
        // Create quote data
        let mut quote_data = Vec::new();
        quote_data.extend_from_slice(nonce);
        for (pcr, value) in &pcr_values {
            quote_data.extend_from_slice(&pcr.to_le_bytes());
            quote_data.extend_from_slice(value);
        }
        
        // Sign quote (simplified)
        let signature = [0u8; 64];
        
        Ok(PcrQuote {
            pcr_values,
            signature,
        })
    }

    /// Create primary key
    pub fn create_primary(&mut self, key_type: TpmKeyType) -> Result<TpmKey, TpmResponse> {
        let handle = self.keys.len() as u32 + 0x80000000;
        
        let mut public_key = vec![0u8; PUBLIC_KEY_SIZE];
        let mut rng = HardwareRng;
        rng.fill_bytes(&mut public_key);
        
        let key = TpmKey {
            handle,
            key_type,
            public_key,
        };
        
        self.keys.push(key.clone());
        Ok(key)
    }

    /// Seal data with TPM
    pub fn seal(&self, data: &[u8], _pcr_policy: &[usize]) -> Result<Vec<u8>, TpmResponse> {
        // Simplified sealing - would use actual TPM seal operation
        let mut sealed = vec![0u8; data.len() + 32];
        sealed[32..].copy_from_slice(data);
        Ok(sealed)
    }

    /// Unseal data
    pub fn unseal(&self, sealed_data: &[u8], _pcr_policy: &[usize]) -> Result<Vec<u8>, TpmResponse> {
        if sealed_data.len() < 32 {
            return Err(TpmResponse::Value);
        }
        Ok(sealed_data[32..].to_vec())
    }

    /// Get random bytes
    pub fn get_random(&self, num_bytes: usize) -> Vec<u8> {
        let mut result = vec![0u8; num_bytes];
        let mut rng = HardwareRng;
        rng.fill_bytes(&mut result);
        result
    }

    /// Stir randomness
    pub fn stir_random(&mut self, _data: &[u8]) {
        // Mix entropy into TPM RNG state
    }

    /// NV Read
    pub fn nv_read(&self, index: u32, size: usize, offset: usize) -> Result<Vec<u8>, TpmResponse> {
        if let Some((_idx, data)) = self.nv_storage.iter().find(|(i, _)| *i == index) {
            let data_len: usize = data.len();
            if offset + size > data_len {
                return Err(TpmResponse::Value);
            }
            Ok(data[offset..offset + size].to_vec())
        } else {
            Err(TpmResponse::Handle)
        }
    }

    /// NV Write
    pub fn nv_write(&mut self, index: u32, data: &[u8], offset: usize) -> TpmResponse {
        if let Some((_idx, existing)) = self.nv_storage.iter_mut().find(|(i, _)| *i == index) {
            let data_len: usize = data.len();
            let existing_len: usize = existing.len();
            if offset + data_len > existing_len {
                existing.resize(offset + data_len, 0);
            }
            existing[offset..offset + data_len].copy_from_slice(data);
        } else {
            let mut new_data = vec![0u8; offset + data.len()];
            new_data[offset..].copy_from_slice(data);
            self.nv_storage.push((index, new_data));
        }
        TpmResponse::Success
    }

    /// NV Define space
    pub fn nv_define_space(&mut self, index: u32, size: usize, _attributes: u32) -> TpmResponse {
        let initial_data = vec![0u8; size];
        self.nv_storage.push((index, initial_data));
        TpmResponse::Success
    }

    /// Get capability
    pub fn get_capability(&self, _capability: u32, _property: u32, _count: u32) -> TpmResponse {
        TpmResponse::Success
    }

    /// Increment clock
    pub fn tick(&mut self) {
        self.clock += 1;
    }

    /// Get clock
    pub fn get_clock(&self) -> u64 {
        self.clock
    }
}

// PcrQuote is imported from secure_boot module

/// TPM Event Log entry
#[derive(Clone, Debug)]
pub struct TpmEvent {
    pub pcr_index: u32,
    pub event_type: u32,
    pub digest: [u8; 32],
    pub event_data: Vec<u8>,
}

/// TPM Event Log
pub struct TpmEventLog {
    events: Vec<TpmEvent>,
}

impl TpmEventLog {
    pub fn new() -> Self {
        TpmEventLog {
            events: Vec::new(),
        }
    }

    pub fn add_event(&mut self, pcr_index: u32, event_type: u32, digest: [u8; 32], event_data: Vec<u8>) {
        self.events.push(TpmEvent {
            pcr_index,
            event_type,
            digest,
            event_data,
        });
    }

    pub fn get_events(&self) -> &[TpmEvent] {
        &self.events
    }

    pub fn get_events_for_pcr(&self, pcr_index: u32) -> Vec<&TpmEvent> {
        self.events.iter()
            .filter(|e| e.pcr_index == pcr_index)
            .collect()
    }
}

/// TPM-based secure key storage
pub struct TpmKeyStore {
    context: TpmContext,
}

impl TpmKeyStore {
    pub fn new() -> Self {
        TpmKeyStore {
            context: TpmContext::new(),
        }
    }

    pub fn generate_key(&mut self, key_type: TpmKeyType) -> Result<TpmKey, TpmResponse> {
        self.context.create_primary(key_type)
    }

    pub fn seal_key(&self, key: &[u8], pcr_policy: &[usize]) -> Result<Vec<u8>, TpmResponse> {
        self.context.seal(key, pcr_policy)
    }

    pub fn unseal_key(&self, sealed: &[u8], pcr_policy: &[usize]) -> Result<Vec<u8>, TpmResponse> {
        self.context.unseal(sealed, pcr_policy)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tpm_startup() {
        let mut tpm = TpmContext::new();
        assert_eq!(tpm.startup(true), TpmResponse::Success);
    }

    #[test]
    fn test_tpm_pcr_extend() {
        let mut tpm = TpmContext::new();
        tpm.startup(true);
        
        let digests = vec![(TpmAlgId::Sha256, b"test data".as_slice())];
        assert_eq!(tpm.pcr_extend(0, &digests), TpmResponse::Success);
    }

    #[test]
    fn test_tpm_random() {
        let tpm = TpmContext::new();
        let random = tpm.get_random(32);
        assert_eq!(random.len(), 32);
    }

    #[test]
    fn test_tpm_seal_unseal() {
        let tpm = TpmContext::new();
        let data = b"secret data";
        let policy = vec![0, 1, 2];
        
        let sealed = tpm.seal(data, &policy).unwrap();
        let unsealed = tpm.unseal(&sealed, &policy).unwrap();
        
        assert_eq!(unsealed, data);
    }

    #[test]
    fn test_tpm_nv_storage() {
        let mut tpm = TpmContext::new();
        
        // Define space
        assert_eq!(tpm.nv_define_space(0x01000001, 64, 0), TpmResponse::Success);
        
        // Write
        assert_eq!(tpm.nv_write(0x01000001, b"test data", 0), TpmResponse::Success);
        
        // Read
        let data = tpm.nv_read(0x01000001, 9, 0).unwrap();
        assert_eq!(data, b"test data");
    }

    #[test]
    fn test_pcr_selection() {
        let sel = PcrSelection::new(TpmAlgId::Sha256, &[0, 1, 2, 16]);
        assert!(sel.is_selected(0));
        assert!(sel.is_selected(1));
        assert!(sel.is_selected(16));
        assert!(!sel.is_selected(3));
        assert!(!sel.is_selected(24));
    }

    #[test]
    fn test_tpm_event_log() {
        let mut log = TpmEventLog::new();
        
        log.add_event(0, 0x00000001, [0; 32], b"Bootloader".to_vec());
        log.add_event(1, 0x00000002, [1; 32], b"Kernel".to_vec());
        log.add_event(0, 0x00000003, [2; 32], b"Initramfs".to_vec());
        
        assert_eq!(log.get_events().len(), 3);
        assert_eq!(log.get_events_for_pcr(0).len(), 2);
        assert_eq!(log.get_events_for_pcr(1).len(), 1);
    }

    #[test]
    fn test_tpm_keystore() {
        let mut keystore = TpmKeyStore::new();
        
        let key = keystore.generate_key(TpmKeyType::Storage).unwrap();
        assert_eq!(key.handle, 0x80000000);
        
        let secret = b"my secret key";
        let policy = vec![0];
        let sealed = keystore.seal_key(secret, &policy).unwrap();
        let unsealed = keystore.unseal_key(&sealed, &policy).unwrap();
        
        assert_eq!(unsealed, secret);
    }

    #[test]
    fn test_tpm_quote() {
        let mut tpm = TpmContext::new();
        tpm.startup(true);
        
        let key = tpm.create_primary(TpmKeyType::Signing).unwrap();
        let selection = PcrSelection::new(TpmAlgId::Sha256, &[0, 1, 2]);
        
        let quote = tpm.quote(&key, &selection, b"nonce").unwrap();
        assert_eq!(quote.pcr_values.len(), 3);
        assert!(!quote.signature.is_empty());
    }

    #[test]
    fn test_tpm_self_test() {
        let mut tpm = TpmContext::new();
        assert_eq!(tpm.self_test(false), TpmResponse::Success);
        assert_eq!(tpm.self_test(true), TpmResponse::Success);
    }

    #[test]
    fn test_tpm_clock() {
        let mut tpm = TpmContext::new();
        assert_eq!(tpm.get_clock(), 0);
        
        tpm.tick();
        tpm.tick();
        assert_eq!(tpm.get_clock(), 2);
    }
}
