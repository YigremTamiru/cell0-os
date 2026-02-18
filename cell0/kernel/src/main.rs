//! Cell0 Kernel Main Entry Point
//! 
//! Main entry point for the Cell0 operating system.
//! Supports both hosted (std) and bare metal (no_std) environments.

#![cfg_attr(not(feature = "std"), no_std)]
#![cfg_attr(not(feature = "std"), no_main)]

use cell0_kernel::{VERSION, KERNEL_NAME};

/// Main entry point for hosted environments
#[cfg(feature = "std")]
fn main() {
    println!("{} Kernel v{}", KERNEL_NAME, VERSION);
    println!("12-Cryptographic System Initialized");
    
    // Initialize crypto subsystem
    cell0_kernel::init();
    
    println!("Kernel running in hosted mode...");
}

/// Entry point for bare metal environments
#[cfg(all(not(feature = "std"), target_arch = "x86_64"))]
#[no_mangle]
pub extern "C" fn _start() -> ! {
    // Initialize kernel
    cell0_kernel::init();
    
    // Main kernel loop
    loop {
        unsafe {
            core::arch::asm!("hlt", options(nomem, nostack));
        }
    }
}

/// Entry point for non-x86_64 bare metal (stub)
#[cfg(all(not(feature = "std"), not(target_arch = "x86_64")))]
#[no_mangle]
pub extern "C" fn _start() -> ! {
    // Minimal bare metal entry for other architectures
    cell0_kernel::init();
    
    loop {
        core::sync::atomic::fence(core::sync::atomic::Ordering::SeqCst);
    }
}
