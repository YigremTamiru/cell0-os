//! Cell0 Kernel Library
//! 
//! Main library for the Cell0 operating system kernel.
//! Supports both hosted (std) and bare metal (no_std) environments.
//!
//! # Features
//! - 12-Cryptographic System (post-quantum ready)
//! - Self-healing memory management
//! - Capability-based security (SYPAS)
//! - Preemptive multitasking
//! - Bare metal boot support

#![cfg_attr(not(feature = "std"), no_std)]
#![cfg_attr(not(feature = "std"), no_main)]

// Export alloc for no_std environments
#[cfg(not(feature = "std"))]
pub extern crate alloc;

// Prelude exports for no_std - re-export common alloc types
#[cfg(not(feature = "std"))]
pub mod prelude {
    pub use alloc::vec::Vec;
    pub use alloc::vec;
    pub use alloc::string::{String, ToString};
    pub use alloc::boxed::Box;
    pub use alloc::collections::BTreeMap;
    pub use alloc::format;
}

// Print macros for bare metal - defined before modules
#[cfg(all(target_arch = "x86_64", not(feature = "std")))]
#[macro_export]
macro_rules! serial_print {
    ($($arg:tt)*) => {
        if let Some(writer) = $crate::serial::SERIAL_WRITER.lock().as_mut() {
            use core::fmt::Write;
            let _ = write!(writer, $($arg)*);
        }
    };
}

#[cfg(all(target_arch = "x86_64", not(feature = "std")))]
#[macro_export]
macro_rules! serial_println {
    () => ($crate::serial_print!("\n"));
    ($($arg:tt)*) => ($crate::serial_print!("{}\n", format_args!($($arg)*)));
}

// Dummy macros for non-bare metal builds
#[cfg(not(all(target_arch = "x86_64", not(feature = "std"))))]
#[macro_export]
macro_rules! serial_print {
    ($($arg:tt)*) => {};
}

#[cfg(not(all(target_arch = "x86_64", not(feature = "std"))))]
#[macro_export]
macro_rules! serial_println {
    ($($arg:tt)*) => {};
}

// Dummy println! macro for no_std (does nothing since we have no console in bare metal)
#[cfg(not(feature = "std"))]
#[macro_export]
macro_rules! println {
    ($($arg:tt)*) => {};
}

// Println for std builds
#[cfg(feature = "std")]
#[macro_export]
macro_rules! println {
    ($($arg:tt)*) => {
        std::println!($($arg)*)
    };
}

// Core modules
pub mod crypto;
pub mod memory;
pub mod process;
pub mod sypas;
pub mod ipc;
pub mod syscall;
pub mod consensus;

// VGA and serial only available on x86_64 bare metal
#[cfg(all(target_arch = "x86_64", not(feature = "std")))]
pub mod vga_buffer;
#[cfg(all(target_arch = "x86_64", not(feature = "std")))]
pub mod serial;

// Boot module for bare metal
#[cfg(all(target_arch = "x86_64", not(feature = "std")))]
pub mod boot;

// Re-export crypto module for easy access
pub use crypto::*;

/// Kernel version
pub const VERSION: &str = "1.2.0";

/// Kernel name
pub const KERNEL_NAME: &str = "Cell0";

/// Kernel initialization
pub fn init() {
    #[cfg(all(target_arch = "x86_64", not(feature = "std")))]
    {
        serial_println!("[kernel] Cell0 Kernel v{}", VERSION);
        serial_println!("[kernel] Initializing subsystems...");
        
        // Initialize boot subsystems (GDT, IDT, PIC, Timer)
        boot::init();
        
        // Initialize memory subsystem
        serial_println!("[kernel] Initializing memory subsystem...");
        unsafe {
            // In a real system, we'd get the heap location from the bootloader
            // For now, use a static allocation
            static mut HEAP: [u8; 1024 * 1024] = [0; 1024 * 1024]; // 1MB heap
            memory::init(HEAP.as_mut_ptr(), HEAP.len());
        }
        
        // Initialize process subsystem
        serial_println!("[kernel] Initializing process subsystem...");
        process::init();
        
        // Initialize SYPAS security
        serial_println!("[kernel] Initializing SYPAS security...");
        sypas::init();
        
        // Initialize IPC
        serial_println!("[kernel] Initializing IPC subsystem...");
        ipc::init();
        
        // Initialize serial output
        serial::init();
        
        serial_println!("[kernel] All subsystems initialized successfully");
    }
    
    #[cfg(feature = "std")]
    {
        println!("{} Kernel v{}", KERNEL_NAME, VERSION);
        println!("12-Cryptographic System Initialized");
        println!("Kernel running in hosted mode...");
    }
}

/// Run kernel self-tests
pub fn self_test() -> bool {
    #[cfg(all(target_arch = "x86_64", not(feature = "std")))]
    serial_println!("[kernel] Running self-tests...");
    
    // Test memory heap
    let heap_ok = memory::verify_heap().is_ok();
    
    #[cfg(all(target_arch = "x86_64", not(feature = "std")))]
    serial_println!("[kernel] Heap verification: {}", if heap_ok { "OK" } else { "FAIL" });
    
    heap_ok
}

/// Get kernel statistics
pub fn get_stats() -> KernelStats {
    KernelStats {
        version: VERSION,
        memory_stats: memory::get_stats(),
    }
}

/// Kernel statistics structure
#[derive(Debug, Clone)]
pub struct KernelStats {
    pub version: &'static str,
    pub memory_stats: memory::MemoryStats,
}

/// Panic handler for no_std environments
#[cfg(not(feature = "std"))]
#[panic_handler]
fn panic(info: &core::panic::PanicInfo) -> ! {
    #[cfg(all(target_arch = "x86_64", not(feature = "std")))]
    {
        serial_println!("[kernel] PANIC: {}", info);
    }
    
    loop {
        #[cfg(all(target_arch = "x86_64", not(feature = "std")))]
        unsafe {
            core::arch::asm!("hlt", options(nomem, nostack));
        }
        #[cfg(not(all(target_arch = "x86_64", not(feature = "std"))))]
        {
            core::sync::atomic::fence(core::sync::atomic::Ordering::SeqCst);
        }
    }
}
