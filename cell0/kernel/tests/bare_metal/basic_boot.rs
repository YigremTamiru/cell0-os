//! Basic kernel test
//! 
//! Tests that the kernel can boot and output to serial.

#![no_std]
#![no_main]
#![feature(custom_test_frameworks)]
#![test_runner(test_runner)]
#![reexport_test_harness_main = "test_main"]

use core::panic::PanicInfo;
use cell0_kernel::{serial_print, serial_println, exit_qemu, QemuExitCode};

#[no_mangle]
pub extern "C" fn _start() -> ! {
    test_main();

    loop {}
}

fn test_runner(tests: &[&dyn Fn()]) {
    serial_println!("Running {} tests", tests.len());
    for test in tests {
        test();
    }
    
    exit_qemu(QemuExitCode::Success);
}

#[panic_handler]
fn panic(info: &PanicInfo) -> ! {
    serial_println!("[failed] {}", info);
    exit_qemu(QemuExitCode::Failed);
    loop {}
}

#[test_case]
fn test_boot() {
    serial_print!("test_boot... ");
    serial_println!("[ok]");
}

#[test_case]
fn test_serial() {
    serial_print!("test_serial... ");
    serial_println!("[ok]");
}
