//! System call interface

// Note: no_std is set at the crate root (lib.rs), not here

/// Syscall numbers
#[repr(u64)]
pub enum Syscall {
    Exit = 0,
    Write = 1,
    Read = 2,
}
