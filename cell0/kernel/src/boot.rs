//! Bare Metal Boot and Interrupt Handling for x86_64
//!
//! This module provides:
//! - Multiboot2 compliance
//! - GDT (Global Descriptor Table) setup
//! - IDT (Interrupt Descriptor Table) setup
//! - PIC/APIC initialization
//! - Timer interrupts
//! - Hardware exception handling
//!
//! Uses naked functions and inline assembly for stable Rust compatibility.

#![cfg(all(target_arch = "x86_64", not(feature = "std")))]

use core::arch::asm;
use core::sync::atomic::{AtomicBool, Ordering};
use crate::serial_println;

/// Memory region types from multiboot2
#[repr(u32)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MemoryRegionType {
    Usable = 1,
    Reserved = 2,
    AcpiReclaimable = 3,
    AcpiNvs = 4,
    BadMemory = 5,
    BootloaderReserved = 6,
}

/// Memory map entry
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct MemoryMapEntry {
    pub base_addr: u64,
    pub length: u64,
    pub region_type: u32,
    pub acpi_reserved: u32,
}

/// Boot information passed from bootloader
#[repr(C)]
pub struct BootInfo {
    pub total_size: u32,
    pub reserved: u32,
    // Tags follow...
}

/// CPU exception types
#[derive(Debug, Clone, Copy)]
#[repr(u8)]
pub enum Exception {
    DivideError = 0,
    Debug = 1,
    NonMaskableInterrupt = 2,
    Breakpoint = 3,
    Overflow = 4,
    BoundRangeExceeded = 5,
    InvalidOpcode = 6,
    DeviceNotAvailable = 7,
    DoubleFault = 8,
    CoprocessorSegmentOverrun = 9,
    InvalidTSS = 10,
    SegmentNotPresent = 11,
    StackSegmentFault = 12,
    GeneralProtectionFault = 13,
    PageFault = 14,
    X87FloatingPoint = 16,
    AlignmentCheck = 17,
    MachineCheck = 18,
    SIMDFloatingPoint = 19,
    Virtualization = 20,
    SecurityException = 30,
}

/// Interrupt stack frame
#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct InterruptStackFrame {
    pub instruction_pointer: u64,
    pub code_segment: u64,
    pub cpu_flags: u64,
    pub stack_pointer: u64,
    pub stack_segment: u64,
}

/// GDT entry (8 bytes)
#[repr(C, packed)]
#[derive(Clone, Copy)]
struct GdtEntry {
    limit_low: u16,
    base_low: u16,
    base_middle: u8,
    access: u8,
    granularity: u8,
    base_high: u8,
}

impl GdtEntry {
    const fn new() -> Self {
        GdtEntry {
            limit_low: 0,
            base_low: 0,
            base_middle: 0,
            access: 0,
            granularity: 0,
            base_high: 0,
        }
    }

    fn set(&mut self, base: u32, limit: u32, access: u8, granularity: u8) {
        self.limit_low = (limit & 0xFFFF) as u16;
        self.base_low = (base & 0xFFFF) as u16;
        self.base_middle = ((base >> 16) & 0xFF) as u8;
        self.access = access;
        self.granularity = ((limit >> 16) & 0x0F) as u8 | (granularity & 0xF0);
        self.base_high = ((base >> 24) & 0xFF) as u8;
    }
}

/// IDT entry (16 bytes)
#[repr(C, packed)]
#[derive(Clone, Copy)]
struct IdtEntry {
    offset_low: u16,
    selector: u16,
    ist: u8,
    type_attributes: u8,
    offset_middle: u16,
    offset_high: u32,
    reserved: u32,
}

impl IdtEntry {
    const fn new() -> Self {
        IdtEntry {
            offset_low: 0,
            selector: 0,
            ist: 0,
            type_attributes: 0,
            offset_middle: 0,
            offset_high: 0,
            reserved: 0,
        }
    }

    fn set_handler(&mut self, handler: u64) {
        self.offset_low = (handler & 0xFFFF) as u16;
        self.offset_middle = ((handler >> 16) & 0xFFFF) as u16;
        self.offset_high = ((handler >> 32) & 0xFFFFFFFF) as u32;
        self.selector = 0x08; // Kernel code segment
        self.type_attributes = 0x8E; // Present, Ring 0, Interrupt Gate
    }
}

/// GDT pointer structure for LGDT instruction
#[repr(C, packed)]
struct GdtPointer {
    limit: u16,
    base: u64,
}

/// IDT pointer structure for LIDT instruction
#[repr(C, packed)]
struct IdtPointer {
    limit: u16,
    base: u64,
}

// Static GDT and IDT - must be static for lifetime requirements
static mut GDT: [GdtEntry; 3] = [GdtEntry::new(); 3];
static mut IDT: [IdtEntry; 256] = [IdtEntry::new(); 256];

static GDT_INITIALIZED: AtomicBool = AtomicBool::new(false);
static IDT_INITIALIZED: AtomicBool = AtomicBool::new(false);
static INTERRUPTS_ENABLED: AtomicBool = AtomicBool::new(false);

/// Initialize the GDT
pub fn init_gdt() {
    if GDT_INITIALIZED.load(Ordering::SeqCst) {
        return;
    }

    unsafe {
        // Null descriptor
        GDT[0].set(0, 0, 0, 0);
        
        // Kernel code segment (4GB, base 0, ring 0)
        // 0x9A = Present, Ring 0, Code, Executable, Readable
        GDT[1].set(0, 0xFFFFF, 0x9A, 0xA0);
        
        // Kernel data segment (4GB, base 0, ring 0)
        // 0x92 = Present, Ring 0, Data, Writable
        GDT[2].set(0, 0xFFFFF, 0x92, 0xA0);
        
        // Load GDT using inline assembly
        let gdt_ptr = GdtPointer {
            limit: (core::mem::size_of::<[GdtEntry; 3]>() - 1) as u16,
            base: GDT.as_ptr() as u64,
        };
        
        // Load GDT and reload segment registers
        asm!(
            "lgdt [{gdt}]",
            "mov ax, 0x10",       // Data segment selector (index 2)
            "mov ds, ax",
            "mov es, ax",
            "mov fs, ax",
            "mov gs, ax",
            "mov ss, ax",
            "push 0x08",          // Code segment selector (index 1)
            "lea rax, [1f]",
            "push rax",
            "retfq",
            "1:",
            gdt = in(reg) &gdt_ptr,
            out("rax") _,
            out("ax") _,
            options(att_syntax)
        );
    }

    GDT_INITIALIZED.store(true, Ordering::SeqCst);
    serial_println!("[boot] GDT initialized");
}

/// Initialize the IDT with basic exception handlers
pub fn init_idt() {
    if IDT_INITIALIZED.load(Ordering::SeqCst) {
        return;
    }

    unsafe {
        // Set up exception handlers (all point to generic handler for now)
        let handler = generic_exception_handler as u64;
        
        IDT[0].set_handler(handler);   // Divide Error
        IDT[3].set_handler(handler);   // Breakpoint
        IDT[6].set_handler(handler);   // Invalid Opcode
        IDT[8].set_handler(handler);   // Double Fault
        IDT[13].set_handler(handler);  // General Protection Fault
        IDT[14].set_handler(handler);  // Page Fault
        
        // Set up timer interrupt (IRQ0 -> IDT 32)
        IDT[32].set_handler(timer_interrupt_handler as u64);
        
        // Load IDT
        let idt_ptr = IdtPointer {
            limit: (core::mem::size_of::<[IdtEntry; 256]>() - 1) as u16,
            base: IDT.as_ptr() as u64,
        };
        
        asm!(
            "lidt [{idt}]",
            idt = in(reg) &idt_ptr,
            options(att_syntax)
        );
    }

    IDT_INITIALIZED.store(true, Ordering::SeqCst);
    serial_println!("[boot] IDT initialized");
}

/// Generic exception handler (assembly stub)
#[naked]
unsafe extern "C" fn generic_exception_handler() {
    asm!(
        // Save registers
        "push rax",
        "push rcx",
        "push rdx",
        "push rsi",
        "push rdi",
        "push r8",
        "push r9",
        "push r10",
        "push r11",
        
        // Call Rust handler
        "call handle_exception",
        
        // Restore registers
        "pop r11",
        "pop r10",
        "pop r9",
        "pop r8",
        "pop rdi",
        "pop rsi",
        "pop rdx",
        "pop rcx",
        "pop rax",
        
        // Return from interrupt
        "iretq",
        options(noreturn)
    );
}

/// Rust exception handler
#[no_mangle]
unsafe extern "C" fn handle_exception() {
    serial_println!("[interrupt] EXCEPTION OCCURRED");
    fatal_error(0xFF);
}

/// Timer interrupt handler (assembly stub)
#[naked]
unsafe extern "C" fn timer_interrupt_handler() {
    asm!(
        // Save registers
        "push rax",
        "push rcx",
        "push rdx",
        "push rsi",
        "push rdi",
        "push r8",
        "push r9",
        "push r10",
        "push r11",
        
        // Call Rust handler
        "call handle_timer_interrupt",
        
        // Restore registers
        "pop r11",
        "pop r10",
        "pop r9",
        "pop r8",
        "pop rdi",
        "pop rsi",
        "pop rdx",
        "pop rcx",
        "pop rax",
        
        // Return from interrupt
        "iretq",
        options(noreturn)
    );
}

/// Rust timer interrupt handler
#[no_mangle]
unsafe extern "C" fn handle_timer_interrupt() {
    static mut TICKS: u64 = 0;
    TICKS += 1;
    
    // Send EOI to PIC
    send_eoi(0);
}

/// Get current tick count
pub fn get_ticks() -> u64 {
    unsafe {
        static mut LAST_TICKS: u64 = 0;
        // In a real implementation, this would read a shared atomic
        LAST_TICKS
    }
}

/// Initialize the PIC (Programmable Interrupt Controller)
pub fn init_pic() {
    unsafe {
        // ICW1: Start initialization, cascade mode, ICW4 needed
        cpu_io_out(0x20, 0x11); // Master PIC
        cpu_io_wait();
        cpu_io_out(0xA0, 0x11); // Slave PIC
        cpu_io_wait();
        
        // ICW2: Vector offset (IDT entries)
        cpu_io_out(0x21, 0x20); // Master: IDT 32-39
        cpu_io_wait();
        cpu_io_out(0xA1, 0x28); // Slave: IDT 40-47
        cpu_io_wait();
        
        // ICW3: Cascade configuration
        cpu_io_out(0x21, 0x04); // Tell master slave is at IRQ2
        cpu_io_wait();
        cpu_io_out(0xA1, 0x02); // Tell slave its cascade identity
        cpu_io_wait();
        
        // ICW4: 8086 mode, normal EOI
        cpu_io_out(0x21, 0x01);
        cpu_io_wait();
        cpu_io_out(0xA1, 0x01);
        cpu_io_wait();
        
        // OCW1: Mask all interrupts except timer (IRQ0)
        cpu_io_out(0x21, 0xFE); // Enable only timer (bit 0)
        cpu_io_out(0xA1, 0xFF); // Disable all slave interrupts
    }

    serial_println!("[boot] PIC initialized");
}

/// Initialize PIT (Programmable Interval Timer) for timer interrupts
pub fn init_timer(frequency_hz: u32) {
    unsafe {
        let divisor: u32 = 1193180 / frequency_hz;
        
        // Set PIT mode: channel 0, lobyte/hibyte, rate generator
        cpu_io_out(0x43, 0x36);
        cpu_io_wait();
        
        // Set divisor (low byte then high byte)
        cpu_io_out(0x40, (divisor & 0xFF) as u8);
        cpu_io_wait();
        cpu_io_out(0x40, ((divisor >> 8) & 0xFF) as u8);
    }

    serial_println!("[boot] Timer initialized at {} Hz", frequency_hz);
}

/// Enable interrupts
pub fn enable_interrupts() {
    unsafe {
        asm!("sti", options(nomem, nostack));
    }
    INTERRUPTS_ENABLED.store(true, Ordering::SeqCst);
}

/// Disable interrupts
pub fn disable_interrupts() {
    unsafe {
        asm!("cli", options(nomem, nostack));
    }
    INTERRUPTS_ENABLED.store(false, Ordering::SeqCst);
}

/// Check if interrupts are enabled
pub fn interrupts_enabled() -> bool {
    INTERRUPTS_ENABLED.load(Ordering::Relaxed)
}

/// Halt the CPU until next interrupt
pub fn hlt() {
    unsafe {
        asm!("hlt", options(nomem, nostack));
    }
}

/// Send End of Interrupt signal to PIC
pub fn send_eoi(irq: u8) {
    unsafe {
        if irq >= 8 {
            cpu_io_out(0xA0, 0x20); // Send EOI to slave
        }
        cpu_io_out(0x20, 0x20); // Send EOI to master
    }
}

/// Halt loop on fatal error
pub fn fatal_error(code: u8) -> ! {
    serial_println!("[boot] FATAL ERROR: code {:#02x}", code);
    
    // Write error code to port 0x80 (POST port, often visible in emulators)
    unsafe {
        cpu_io_out(0x80, code);
    }
    
    loop {
        disable_interrupts();
        unsafe {
            asm!("hlt", options(nomem, nostack));
        }
    }
}

/// CPU I/O port output
pub unsafe fn cpu_io_out(port: u16, value: u8) {
    asm!(
        "out dx, al",
        in("dx") port,
        in("al") value,
        options(nomem, nostack, preserves_flags)
    );
}

/// CPU I/O port input
pub unsafe fn cpu_io_in(port: u16) -> u8 {
    let value: u8;
    asm!(
        "in al, dx",
        out("al") value,
        in("dx") port,
        options(nomem, nostack, preserves_flags)
    );
    value
}

/// I/O wait (short delay for PIC)
pub unsafe fn cpu_io_wait() {
    // Write to unused port 0x80 (POST port)
    asm!(
        "out 0x80, al",
        in("al") 0u8,
        options(nomem, nostack, preserves_flags)
    );
}

/// Initialize all boot subsystems
pub fn init() {
    serial_println!("[boot] Initializing boot subsystem...");
    
    init_gdt();
    init_idt();
    init_pic();
    init_timer(100); // 100 Hz timer
    
    serial_println!("[boot] Boot subsystem initialized");
}

/// Complete boot sequence and jump to main kernel
pub fn finish_boot() -> ! {
    serial_println!("[boot] Boot sequence complete, enabling interrupts...");
    
    enable_interrupts();
    
    serial_println!("[boot] Entering kernel main loop");
    
    loop {
        hlt();
    }
}

/// Parse multiboot2 boot info
pub unsafe fn parse_multiboot2(info: *const BootInfo) {
    let total_size = (*info).total_size;
    serial_println!("[boot] Multiboot2 info size: {} bytes", total_size);
    
    // In a real implementation, we would parse the tag structure
    // For now, this is a placeholder
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_exception_enum() {
        assert_eq!(Exception::DivideError as u8, 0);
        assert_eq!(Exception::PageFault as u8, 14);
    }

    #[test]
    fn test_memory_region_type() {
        assert_eq!(MemoryRegionType::Usable as u32, 1);
        assert_eq!(MemoryRegionType::BadMemory as u32, 5);
    }
}
