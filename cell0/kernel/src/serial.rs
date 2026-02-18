//! Serial port output for debugging
//! 
//! Uses UART 16550 serial port for early boot output.
//! The serial port is at COM1 (0x3F8).

#![cfg(all(target_arch = "x86_64", not(feature = "std")))]

use core::fmt::{self, Write};

/// Serial port writer
pub struct SerialWriter;

impl SerialWriter {
    pub const fn new() -> Self {
        Self
    }
    
    pub fn init(&mut self) {}
    
    pub fn write_byte(&mut self, _byte: u8) {
        // On x86_64, this writes to port 0x3F8
        #[cfg(all(target_arch = "x86_64", not(test)))]
        unsafe {
            core::arch::asm!(
                "out dx, al",
                in("dx") 0x3F8u16,
                in("al") _byte,
                options(nomem, nostack)
            );
        }
    }
}

impl fmt::Write for SerialWriter {
    fn write_str(&mut self, s: &str) -> fmt::Result {
        for byte in s.bytes() {
            self.write_byte(byte);
        }
        Ok(())
    }
}

/// Initialize the serial port for output
pub fn init() {
    // UART initialization would go here on x86_64
}

/// Internal print function used by macros
#[doc(hidden)]
pub fn _print(args: fmt::Arguments) {
    let mut writer = SerialWriter::new();
    writer.write_fmt(args).ok();
}

/// Print to the serial port
#[macro_export]
macro_rules! serial_print {
    ($($arg:tt)*) => {
        $crate::serial::_print(format_args!($($arg)*))
    };
}

/// Print with newline to the serial port
#[macro_export]
macro_rules! serial_println {
    () => ($crate::serial_print!("\n"));
    ($fmt:expr) => ($crate::serial_print!(concat!($fmt, "\n")));
    ($fmt:expr, $($arg:tt)*) => ($crate::serial_print!(
        concat!($fmt, "\n"), $($arg)*));
}
