//! Process Management and Scheduling Subsystem
//! 
//! Implements a priority-based round-robin scheduler with:
//! - Preemptive multitasking
//! - Capability-based security (SYPAS protocol)
//! - Process isolation
//! - Signal handling
//! - Resource limits

#![cfg_attr(not(feature = "std"), no_std)]

use core::sync::atomic::{AtomicU64, Ordering};
use core::cell::UnsafeCell;

#[cfg(not(feature = "std"))]
use alloc::vec::Vec;
#[cfg(not(feature = "std"))]
use alloc::collections::BTreeMap;

#[cfg(feature = "std")]
use std::collections::BTreeMap;

/// Maximum number of processes
pub const MAX_PROCESSES: usize = 256;
/// Default time slice in milliseconds
pub const DEFAULT_TIME_SLICE: u64 = 10;
/// Number of priority levels
pub const NUM_PRIORITIES: usize = 8;
/// Kernel process ID
pub const KERNEL_PID: u64 = 0;

/// Process states
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum ProcessState {
    /// Process is ready to run
    Ready = 0,
    /// Process is currently running
    Running = 1,
    /// Process is blocked waiting for something
    Blocked = 2,
    /// Process is sleeping for a specific time
    Sleeping = 3,
    /// Process has exited but not reaped
    Zombie = 4,
    /// Process is stopped (signal)
    Stopped = 5,
    /// Process is terminated
    Terminated = 6,
}

/// Process priorities (lower number = higher priority)
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum Priority {
    Realtime = 0,
    High = 1,
    AboveNormal = 2,
    Normal = 3,
    BelowNormal = 4,
    Low = 5,
    Idle = 6,
    Kernel = 7,
}

impl Priority {
    pub fn time_slice_ms(&self) -> u64 {
        match self {
            Priority::Realtime => 1,
            Priority::High => 5,
            Priority::AboveNormal => 8,
            Priority::Normal => DEFAULT_TIME_SLICE,
            Priority::BelowNormal => 20,
            Priority::Low => 50,
            Priority::Idle => 100,
            Priority::Kernel => 1,
        }
    }
}

/// Process capabilities (SYPAS protocol)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Capabilities {
    /// Raw capability bits
    bits: u64,
}

/// Capability types
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum Capability {
    /// Can read from files
    FileRead = 0,
    /// Can write to files
    FileWrite = 1,
    /// Can create files
    FileCreate = 2,
    /// Can delete files
    FileDelete = 3,
    /// Can open network sockets
    Network = 4,
    /// Can spawn new processes
    ProcessSpawn = 5,
    /// Can kill other processes
    ProcessKill = 6,
    /// Can allocate memory
    MemoryAlloc = 7,
    /// Can execute code
    Execute = 8,
    /// Can access hardware devices
    HardwareAccess = 9,
    /// Can modify system time
    SetTime = 10,
    /// Can load kernel modules
    LoadModule = 11,
    /// Can send signals
    SignalSend = 12,
    /// Can create IPC channels
    IpcCreate = 13,
    /// Can join IPC channels
    IpcJoin = 14,
    /// Administrator capability (all permissions)
    Admin = 63,
}

impl Capabilities {
    pub const fn new() -> Self {
        Capabilities { bits: 0 }
    }

    pub fn set(&mut self, cap: Capability) {
        self.bits |= 1u64 << (cap as u64);
    }

    pub fn clear(&mut self, cap: Capability) {
        self.bits &= !(1u64 << (cap as u64));
    }

    pub fn has(&self, cap: Capability) -> bool {
        self.has_admin() || (self.bits & (1u64 << (cap as u64))) != 0
    }

    pub fn has_admin(&self) -> bool {
        (self.bits & (1u64 << (Capability::Admin as u64))) != 0
    }

    pub fn grant_all(&mut self) {
        self.bits = u64::MAX;
    }

    pub fn revoke_all(&mut self) {
        self.bits = 0;
    }

    /// Derive a subset of capabilities (capability attenuation)
    pub fn derive(&self, caps: &[Capability]) -> Self {
        let mut derived = Capabilities::new();
        for &cap in caps {
            if self.has(cap) {
                derived.set(cap);
            }
        }
        derived
    }

    /// Check if this set of capabilities is a subset of another
    pub fn is_subset_of(&self, other: &Capabilities) -> bool {
        (self.bits & !other.bits) == 0
    }
}

/// Resource limits for a process
#[derive(Debug, Clone, Copy)]
pub struct ResourceLimits {
    /// Maximum memory in bytes
    pub max_memory: usize,
    /// Maximum CPU time in milliseconds
    pub max_cpu_time: u64,
    /// Maximum number of open files
    pub max_open_files: u32,
    /// Maximum number of processes this process can spawn
    pub max_children: u32,
}

impl Default for ResourceLimits {
    fn default() -> Self {
        ResourceLimits {
            max_memory: 256 * 1024 * 1024, // 256MB default
            max_cpu_time: u64::MAX,
            max_open_files: 1024,
            max_children: 32,
        }
    }
}

/// Process statistics
#[derive(Debug, Clone, Default)]
pub struct ProcessStats {
    /// CPU time used in milliseconds
    pub cpu_time_ms: u64,
    /// Number of context switches
    pub context_switches: u64,
    /// Memory currently allocated
    pub memory_used: usize,
    /// Peak memory usage
    pub peak_memory: usize,
    /// Number of syscalls made
    pub syscalls: u64,
    /// Number of page faults
    pub page_faults: u64,
    /// When the process was created
    pub created_at: u64,
}

/// Process control block
#[derive(Debug)]
pub struct Process {
    /// Process ID
    pub pid: u64,
    /// Parent process ID
    pub parent: Option<u64>,
    /// Current state
    pub state: ProcessState,
    /// Priority level
    pub priority: Priority,
    /// Capabilities (SYPAS)
    pub capabilities: Capabilities,
    /// Resource limits
    pub limits: ResourceLimits,
    /// Statistics
    pub stats: ProcessStats,
    /// Exit code (if terminated)
    pub exit_code: Option<i32>,
    /// Time slice remaining (ms)
    pub time_slice_remaining: u64,
    /// Sleep until timestamp
    pub sleep_until: Option<u64>,
    /// Child process IDs
    pub children: Vec<u64>,
    /// Waiting for PID (for waitpid)
    pub waiting_for: Option<u64>,
}

impl Process {
    pub fn new(pid: u64, parent: Option<u64>, priority: Priority) -> Self {
        Process {
            pid,
            parent,
            state: ProcessState::Ready,
            priority,
            capabilities: Capabilities::new(),
            limits: ResourceLimits::default(),
            stats: ProcessStats::default(),
            exit_code: None,
            time_slice_remaining: priority.time_slice_ms(),
            sleep_until: None,
            children: Vec::new(),
            waiting_for: None,
        }
    }

    /// Check if process has a specific capability
    pub fn has_capability(&self, cap: Capability) -> bool {
        self.capabilities.has(cap)
    }

    /// Add a capability
    pub fn grant_capability(&mut self, cap: Capability) {
        self.capabilities.set(cap);
    }

    /// Revoke a capability
    pub fn revoke_capability(&mut self, cap: Capability) {
        self.capabilities.clear(cap);
    }

    /// Check if process can access a resource
    pub fn check_access(&self, required_caps: &[Capability]) -> bool {
        required_caps.iter().all(|&cap| self.has_capability(cap))
    }
}

/// Process table
pub struct ProcessTable {
    /// All processes indexed by PID
    processes: UnsafeCell<BTreeMap<u64, Process>>,
    /// Next available PID
    next_pid: AtomicU64,
    /// Ready queues (one per priority)
    ready_queues: UnsafeCell<[Vec<u64>; NUM_PRIORITIES]>,
    /// Currently running process
    current_pid: UnsafeCell<Option<u64>>,
    /// Zombie processes waiting to be reaped
    zombies: UnsafeCell<Vec<u64>>,
}

unsafe impl Sync for ProcessTable {}

impl ProcessTable {
    pub const fn new() -> Self {
        ProcessTable {
            processes: UnsafeCell::new(BTreeMap::new()),
            next_pid: AtomicU64::new(1),
            ready_queues: UnsafeCell::new([
                Vec::new(), Vec::new(), Vec::new(), Vec::new(),
                Vec::new(), Vec::new(), Vec::new(), Vec::new(),
            ]),
            current_pid: UnsafeCell::new(None),
            zombies: UnsafeCell::new(Vec::new()),
        }
    }

    /// Initialize with kernel process
    pub fn init(&self) {
        let mut kernel = Process::new(KERNEL_PID, None, Priority::Kernel);
        kernel.capabilities.grant_all();
        kernel.state = ProcessState::Running;
        
        unsafe {
            (*self.processes.get()).insert(KERNEL_PID, kernel);
            *self.current_pid.get() = Some(KERNEL_PID);
        }
    }

    /// Spawn a new process
    pub fn spawn(&self, parent_pid: u64, priority: Priority) -> Result<u64, ProcessError> {
        unsafe {
            let processes = &mut *self.processes.get();
            
            // Check parent exists
            let parent = processes.get(&parent_pid)
                .ok_or(ProcessError::ParentNotFound)?;
            
            // Check parent has spawn capability
            if !parent.has_capability(Capability::ProcessSpawn) {
                return Err(ProcessError::PermissionDenied);
            }
            
            // Check child limit
            if parent.children.len() >= parent.limits.max_children as usize {
                return Err(ProcessError::ResourceLimit);
            }
            
            // Generate new PID
            let pid = self.next_pid.fetch_add(1, Ordering::SeqCst);
            
            // Create new process with inherited capabilities (attenuated)
            let mut child = Process::new(pid, Some(parent_pid), priority);
            child.capabilities = parent.capabilities.derive(&[
                Capability::FileRead,
                Capability::FileWrite,
                Capability::MemoryAlloc,
                Capability::Execute,
                Capability::SignalSend,
                Capability::IpcCreate,
                Capability::IpcJoin,
            ]);
            
            // Insert into process table
            processes.insert(pid, child);
            
            // Add to parent's children
            if let Some(parent) = processes.get_mut(&parent_pid) {
                parent.children.push(pid);
            }
            
            // Add to ready queue
            let ready_queues = &mut *self.ready_queues.get();
            ready_queues[priority as usize].push(pid);
            
            Ok(pid)
        }
    }

    /// Terminate a process
    pub fn terminate(&self, pid: u64, exit_code: i32) -> Result<(), ProcessError> {
        unsafe {
            let processes = &mut *self.processes.get();
            
            let process = processes.get_mut(&pid)
                .ok_or(ProcessError::ProcessNotFound)?;
            
            process.state = ProcessState::Zombie;
            process.exit_code = Some(exit_code);
            
            // Remove from ready queues
            let ready_queues = &mut *self.ready_queues.get();
            for queue in ready_queues.iter_mut() {
                queue.retain(|&p| p != pid);
            }
            
            // Add to zombies list
            (*self.zombies.get()).push(pid);
            
            // If this process has a parent waiting, wake it up
            if let Some(parent_pid) = process.parent {
                if let Some(parent) = processes.get_mut(&parent_pid) {
                    if parent.waiting_for == Some(pid) {
                        parent.state = ProcessState::Ready;
                        parent.waiting_for = None;
                        ready_queues[parent.priority as usize].push(parent_pid);
                    }
                }
            }
            
            Ok(())
        }
    }

    /// Get next process to run (scheduler)
    pub fn schedule(&self) -> Option<u64> {
        unsafe {
            let ready_queues = &mut *self.ready_queues.get();
            
            // Find highest priority non-empty queue
            for priority in 0..NUM_PRIORITIES {
                if !ready_queues[priority].is_empty() {
                    // Round-robin within priority
                    let pid = ready_queues[priority].remove(0);
                    ready_queues[priority].push(pid); // Put at back for next time
                    return Some(pid);
                }
            }
            
            None
        }
    }

    /// Switch to a new process
    pub fn context_switch(&self, new_pid: u64) {
        unsafe {
            let processes = &mut *self.processes.get();
            
            // Mark current as ready
            if let Some(current) = *self.current_pid.get() {
                if let Some(proc) = processes.get_mut(&current) {
                    if proc.state == ProcessState::Running {
                        proc.state = ProcessState::Ready;
                        proc.stats.context_switches += 1;
                    }
                }
            }
            
            // Mark new as running
            if let Some(proc) = processes.get_mut(&new_pid) {
                proc.state = ProcessState::Running;
                proc.time_slice_remaining = proc.priority.time_slice_ms();
            }
            
            *self.current_pid.get() = Some(new_pid);
        }
    }

    /// Block a process
    pub fn block(&self, pid: u64) -> Result<(), ProcessError> {
        unsafe {
            let processes = &mut *self.processes.get();
            
            let process = processes.get_mut(&pid)
                .ok_or(ProcessError::ProcessNotFound)?;
            
            if process.state == ProcessState::Running {
                process.state = ProcessState::Blocked;
            }
            
            Ok(())
        }
    }

    /// Unblock a process
    pub fn unblock(&self, pid: u64) -> Result<(), ProcessError> {
        unsafe {
            let processes = &mut *self.processes.get();
            let ready_queues = &mut *self.ready_queues.get();
            
            let process = processes.get_mut(&pid)
                .ok_or(ProcessError::ProcessNotFound)?;
            
            if process.state == ProcessState::Blocked {
                process.state = ProcessState::Ready;
                ready_queues[process.priority as usize].push(pid);
            }
            
            Ok(())
        }
    }

    /// Put a process to sleep
    pub fn sleep(&self, pid: u64, until: u64) -> Result<(), ProcessError> {
        unsafe {
            let processes = &mut *self.processes.get();
            
            let process = processes.get_mut(&pid)
                .ok_or(ProcessError::ProcessNotFound)?;
            
            process.state = ProcessState::Sleeping;
            process.sleep_until = Some(until);
            
            Ok(())
        }
    }

    /// Wake up sleeping processes whose time has come
    pub fn wake_sleepers(&self, current_time: u64) {
        unsafe {
            let processes = &mut *self.processes.get();
            let ready_queues = &mut *self.ready_queues.get();
            
            for (pid, process) in processes.iter_mut() {
                if process.state == ProcessState::Sleeping {
                    if let Some(until) = process.sleep_until {
                        if current_time >= until {
                            process.state = ProcessState::Ready;
                            process.sleep_until = None;
                            ready_queues[process.priority as usize].push(*pid);
                        }
                    }
                }
            }
        }
    }

    /// Get current process ID
    pub fn current_pid(&self) -> Option<u64> {
        unsafe { *self.current_pid.get() }
    }

    /// Get process by PID
    pub fn get_process(&self, pid: u64) -> Option<&Process> {
        unsafe { (*self.processes.get()).get(&pid) }
    }

    /// Get mutable process by PID
    pub fn get_process_mut(&self, pid: u64) -> Option<&mut Process> {
        unsafe { (*self.processes.get()).get_mut(&pid) }
    }

    /// Get all process IDs
    pub fn all_pids(&self) -> Vec<u64> {
        unsafe {
            (*self.processes.get()).keys().copied().collect()
        }
    }

    /// Reap zombie processes
    pub fn reap_zombies(&self) -> Vec<(u64, i32)> {
        unsafe {
            let processes = &mut *self.processes.get();
            let zombies = &mut *self.zombies.get();
            let mut reaped = Vec::new();
            
            zombies.retain(|&pid| {
                if let Some(process) = processes.get(&pid) {
                    // Check if parent has reaped
                    if let Some(parent_pid) = process.parent {
                        if let Some(parent) = processes.get(&parent_pid) {
                            if parent.waiting_for == Some(pid) {
                                if let Some(exit_code) = process.exit_code {
                                    reaped.push((pid, exit_code));
                                    processes.remove(&pid);
                                    return false; // Remove from zombies
                                }
                            }
                        }
                    }
                }
                true // Keep in zombies
            });
            
            reaped
        }
    }

    /// Send signal to a process
    pub fn send_signal(&self, from: u64, to: u64, signal: Signal) -> Result<(), ProcessError> {
        unsafe {
            let processes = &mut *self.processes.get();
            
            // Check sender exists and has signal capability
            let sender = processes.get(&from)
                .ok_or(ProcessError::ProcessNotFound)?;
            
            if !sender.has_capability(Capability::SignalSend) {
                return Err(ProcessError::PermissionDenied);
            }
            
            // Check if sender can signal target (same user or root)
            // For now, simplified: can signal children or if admin
            let can_signal = sender.capabilities.has_admin() 
                || sender.children.contains(&to);
            
            if !can_signal {
                return Err(ProcessError::PermissionDenied);
            }
            
            // Apply signal
            let target = processes.get_mut(&to)
                .ok_or(ProcessError::ProcessNotFound)?;
            
            match signal {
                Signal::Terminate => {
                    target.state = ProcessState::Terminated;
                }
                Signal::Stop => {
                    target.state = ProcessState::Stopped;
                }
                Signal::Continue => {
                    if target.state == ProcessState::Stopped {
                        target.state = ProcessState::Ready;
                        let ready_queues = &mut *self.ready_queues.get();
                        ready_queues[target.priority as usize].push(to);
                    }
                }
                _ => {}
            }
            
            Ok(())
        }
    }
}

/// Process errors
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProcessError {
    ProcessNotFound,
    ParentNotFound,
    PermissionDenied,
    ResourceLimit,
    InvalidState,
    TableFull,
}

/// Signals
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum Signal {
    Hangup = 1,
    Interrupt = 2,
    Quit = 3,
    Illegal = 4,
    Trap = 5,
    Abort = 6,
    Bus = 7,
    FloatingPoint = 8,
    Kill = 9,
    User1 = 10,
    Segfault = 11,
    User2 = 12,
    Pipe = 13,
    Alarm = 14,
    Terminate = 15,
    Child = 17,
    Continue = 18,
    Stop = 19,
    TerminalStop = 20,
}

/// Global process table
pub static PROCESS_TABLE: ProcessTable = ProcessTable::new();

/// Initialize process subsystem
pub fn init() {
    PROCESS_TABLE.init();
}

/// Spawn a new process
pub fn spawn(parent: u64, priority: Priority) -> Result<u64, ProcessError> {
    PROCESS_TABLE.spawn(parent, priority)
}

/// Get current process ID
pub fn current_pid() -> Option<u64> {
    PROCESS_TABLE.current_pid()
}

/// Check if current process has a capability
pub fn has_capability(cap: Capability) -> bool {
    if let Some(pid) = current_pid() {
        if let Some(proc) = PROCESS_TABLE.get_process(pid) {
            return proc.has_capability(cap);
        }
    }
    false
}

/// Require a capability or fail
pub fn require_capability(cap: Capability) -> Result<(), ProcessError> {
    if has_capability(cap) {
        Ok(())
    } else {
        Err(ProcessError::PermissionDenied)
    }
}

/// Run the scheduler
pub fn schedule() -> Option<u64> {
    PROCESS_TABLE.schedule()
}

/// Yield CPU
pub fn yield_cpu() {
    if let Some(next) = schedule() {
        PROCESS_TABLE.context_switch(next);
    }
}

/// Sleep for a duration
pub fn sleep(duration_ms: u64) -> Result<(), ProcessError> {
    if let Some(pid) = current_pid() {
        let current_time = get_current_time_ms();
        PROCESS_TABLE.sleep(pid, current_time + duration_ms)
    } else {
        Err(ProcessError::ProcessNotFound)
    }
}

/// Get current time in milliseconds (placeholder)
fn get_current_time_ms() -> u64 {
    // In real implementation, this would use hardware timer
    0
}

/// Wait for a child process
pub fn waitpid(pid: u64) -> Result<(u64, i32), ProcessError> {
    if let Some(current) = current_pid() {
        unsafe {
            let processes = &mut *(PROCESS_TABLE.processes.get());
            
            // Check if target is a child
            if let Some(proc) = processes.get(&current) {
                if !proc.children.contains(&pid) {
                    return Err(ProcessError::PermissionDenied);
                }
            }
            
            // Check if already zombie
            if let Some(child) = processes.get(&pid) {
                if child.state == ProcessState::Zombie {
                    if let Some(exit_code) = child.exit_code {
                        // Remove from zombies and process table
                        let zombies = &mut *(PROCESS_TABLE.zombies.get());
                        zombies.retain(|&z| z != pid);
                        processes.remove(&pid);
                        return Ok((pid, exit_code));
                    }
                }
            }
            
            // Block until child exits
            if let Some(proc) = processes.get_mut(&current) {
                proc.waiting_for = Some(pid);
                proc.state = ProcessState::Blocked;
            }
        }
        
        Err(ProcessError::InvalidState)
    } else {
        Err(ProcessError::ProcessNotFound)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_capabilities() {
        let mut caps = Capabilities::new();
        assert!(!caps.has(Capability::FileRead));
        
        caps.set(Capability::FileRead);
        assert!(caps.has(Capability::FileRead));
        
        caps.clear(Capability::FileRead);
        assert!(!caps.has(Capability::FileRead));
        
        // Admin has all caps
        let mut admin = Capabilities::new();
        admin.set(Capability::Admin);
        assert!(admin.has(Capability::FileRead));
        assert!(admin.has(Capability::ProcessSpawn));
    }

    #[test]
    fn test_capability_derivation() {
        let mut parent = Capabilities::new();
        parent.set(Capability::FileRead);
        parent.set(Capability::FileWrite);
        parent.set(Capability::Network);
        
        let child = parent.derive(&[Capability::FileRead, Capability::Network]);
        assert!(child.has(Capability::FileRead));
        assert!(child.has(Capability::Network));
        assert!(!child.has(Capability::FileWrite));
    }

    #[test]
    fn test_process_creation() {
        PROCESS_TABLE.init();
        
        // Grant kernel process spawn capability
        unsafe {
            if let Some(kernel) = (*PROCESS_TABLE.processes.get()).get_mut(&KERNEL_PID) {
                kernel.capabilities.set(Capability::ProcessSpawn);
            }
        }
        
        let child = PROCESS_TABLE.spawn(KERNEL_PID, Priority::Normal);
        assert!(child.is_ok());
        
        let child_pid = child.unwrap();
        assert!(child_pid > KERNEL_PID);
    }
}
