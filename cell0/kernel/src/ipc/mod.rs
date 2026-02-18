//! Inter-Process Communication (IPC) Subsystem
//!
//! Provides secure communication channels between processes:
//! - Message passing
//! - Shared memory regions
//! - Synchronization primitives
//! - Channel-based communication

#![cfg_attr(not(feature = "std"), no_std)]

use core::sync::atomic::{AtomicU64, Ordering};

#[cfg(not(feature = "std"))]
use alloc::vec::Vec;
#[cfg(not(feature = "std"))]
use alloc::collections::VecDeque;
#[cfg(feature = "std")]
use std::collections::VecDeque;

/// Maximum message size
pub const MAX_MESSAGE_SIZE: usize = 4096;
/// Maximum number of channels per process
pub const MAX_CHANNELS_PER_PROCESS: usize = 64;
/// Maximum number of pending messages
pub const MAX_PENDING_MESSAGES: usize = 256;

/// Channel ID
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct ChannelId(u64);

impl ChannelId {
    pub const fn new(id: u64) -> Self {
        ChannelId(id)
    }
    
    pub fn as_u64(&self) -> u64 {
        self.0
    }
}

/// Message header
#[derive(Debug, Clone, Copy)]
#[repr(C)]
pub struct MessageHeader {
    /// Source process ID
    pub source: u64,
    /// Destination process ID
    pub destination: u64,
    /// Message type
    pub msg_type: u32,
    /// Message flags
    pub flags: u32,
    /// Timestamp
    pub timestamp: u64,
}

/// IPC message
#[derive(Debug, Clone)]
pub struct Message {
    pub header: MessageHeader,
    pub payload: Vec<u8>,
}

impl Message {
    pub fn new(source: u64, destination: u64, msg_type: u32, payload: &[u8]) -> Self {
        Message {
            header: MessageHeader {
                source,
                destination,
                msg_type,
                flags: 0,
                timestamp: 0,
            },
            payload: payload.to_vec(),
        }
    }
    
    pub fn size(&self) -> usize {
        core::mem::size_of::<MessageHeader>() + self.payload.len()
    }
}

/// Channel type
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum ChannelType {
    /// One-way communication
    Unidirectional = 0,
    /// Two-way communication
    Bidirectional = 1,
    /// Broadcast to multiple receivers
    Broadcast = 2,
}

/// Channel state
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum ChannelState {
    /// Channel is being set up
    Connecting = 0,
    /// Channel is ready for communication
    Connected = 1,
    /// Channel is closing
    Closing = 2,
    /// Channel is closed
    Closed = 3,
}

/// IPC channel
#[derive(Debug)]
pub struct Channel {
    pub id: ChannelId,
    pub channel_type: ChannelType,
    pub state: ChannelState,
    pub owner: u64,
    pub peer: Option<u64>,
    pub message_queue: VecDeque<Message>,
    pub max_queue_size: usize,
    pub blocking_send: bool,
    pub blocking_recv: bool,
}

impl Channel {
    pub fn new(id: ChannelId, owner: u64, channel_type: ChannelType) -> Self {
        Channel {
            id,
            channel_type,
            state: ChannelState::Connecting,
            owner,
            peer: None,
            message_queue: VecDeque::new(),
            max_queue_size: MAX_PENDING_MESSAGES,
            blocking_send: true,
            blocking_recv: true,
        }
    }
    
    /// Connect to a peer process
    pub fn connect(&mut self, peer: u64) -> Result<(), IpcError> {
        if self.state != ChannelState::Connecting {
            return Err(IpcError::InvalidState);
        }
        
        self.peer = Some(peer);
        self.state = ChannelState::Connected;
        Ok(())
    }
    
    /// Send a message through the channel
    pub fn send(&mut self, message: Message) -> Result<(), IpcError> {
        if self.state != ChannelState::Connected {
            return Err(IpcError::ChannelClosed);
        }
        
        if message.payload.len() > MAX_MESSAGE_SIZE {
            return Err(IpcError::MessageTooLarge);
        }
        
        if self.message_queue.len() >= self.max_queue_size {
            if self.blocking_send {
                return Err(IpcError::WouldBlock);
            } else {
                // Drop oldest message
                self.message_queue.pop_front();
            }
        }
        
        self.message_queue.push_back(message);
        Ok(())
    }
    
    /// Receive a message from the channel
    pub fn recv(&mut self) -> Result<Message, IpcError> {
        if let Some(msg) = self.message_queue.pop_front() {
            Ok(msg)
        } else if self.state == ChannelState::Closed {
            Err(IpcError::ChannelClosed)
        } else if self.blocking_recv {
            Err(IpcError::WouldBlock)
        } else {
            Err(IpcError::NoMessage)
        }
    }
    
    /// Try to receive without blocking
    pub fn try_recv(&mut self) -> Result<Message, IpcError> {
        self.message_queue.pop_front().ok_or(IpcError::NoMessage)
    }
    
    /// Close the channel
    pub fn close(&mut self) {
        self.state = ChannelState::Closed;
        self.peer = None;
    }
    
    /// Check if channel has pending messages
    pub fn has_messages(&self) -> bool {
        !self.message_queue.is_empty()
    }
    
    /// Get number of pending messages
    pub fn pending_count(&self) -> usize {
        self.message_queue.len()
    }
}

/// Shared memory region
#[derive(Debug)]
pub struct SharedMemory {
    pub id: u64,
    pub owner: u64,
    pub size: usize,
    pub base_address: *mut u8,
    pub permissions: SharedMemoryPermissions,
    pub mapped_processes: Vec<u64>,
}

/// Shared memory permissions
#[derive(Debug, Clone, Copy)]
pub struct SharedMemoryPermissions {
    pub readable: bool,
    pub writable: bool,
    pub executable: bool,
}

impl SharedMemoryPermissions {
    pub const READ: Self = SharedMemoryPermissions {
        readable: true,
        writable: false,
        executable: false,
    };
    
    pub const READ_WRITE: Self = SharedMemoryPermissions {
        readable: true,
        writable: true,
        executable: false,
    };
}

impl SharedMemory {
    pub fn new(id: u64, owner: u64, size: usize) -> Self {
        SharedMemory {
            id,
            owner,
            size,
            base_address: core::ptr::null_mut(),
            permissions: SharedMemoryPermissions::READ,
            mapped_processes: Vec::new(),
        }
    }
    
    /// Map into process address space
    pub fn map(&mut self, process_id: u64) -> Result<*mut u8, IpcError> {
        if self.mapped_processes.contains(&process_id) {
            return Ok(self.base_address);
        }
        
        self.mapped_processes.push(process_id);
        Ok(self.base_address)
    }
    
    /// Unmap from process address space
    pub fn unmap(&mut self, process_id: u64) {
        self.mapped_processes.retain(|&p| p != process_id);
    }
}

/// IPC manager
pub struct IpcManager {
    channels: Vec<Channel>,
    next_channel_id: AtomicU64,
    shared_memory: Vec<SharedMemory>,
}

impl IpcManager {
    pub const fn new() -> Self {
        IpcManager {
            channels: Vec::new(),
            next_channel_id: AtomicU64::new(1),
            shared_memory: Vec::new(),
        }
    }
    
    /// Create a new channel
    pub fn create_channel(
        &mut self,
        owner: u64,
        channel_type: ChannelType,
    ) -> Result<ChannelId, IpcError> {
        let id = ChannelId(self.next_channel_id.fetch_add(1, Ordering::SeqCst));
        let channel = Channel::new(id, owner, channel_type);
        self.channels.push(channel);
        Ok(id)
    }
    
    /// Get channel by ID
    pub fn get_channel(&mut self, id: ChannelId) -> Option<&mut Channel> {
        self.channels.iter_mut().find(|c| c.id == id)
    }
    
    /// Close and remove a channel
    pub fn close_channel(&mut self, id: ChannelId) -> Result<(), IpcError> {
        if let Some(channel) = self.get_channel(id) {
            channel.close();
            Ok(())
        } else {
            Err(IpcError::ChannelNotFound)
        }
    }
    
    /// Send message through channel
    pub fn send(&mut self, channel_id: ChannelId, message: Message) -> Result<(), IpcError> {
        if let Some(channel) = self.get_channel(channel_id) {
            channel.send(message)
        } else {
            Err(IpcError::ChannelNotFound)
        }
    }
    
    /// Receive message from channel
    pub fn recv(&mut self, channel_id: ChannelId) -> Result<Message, IpcError> {
        if let Some(channel) = self.get_channel(channel_id) {
            channel.recv()
        } else {
            Err(IpcError::ChannelNotFound)
        }
    }
    
    /// Create shared memory region
    pub fn create_shared_memory(
        &mut self,
        owner: u64,
        size: usize,
    ) -> Result<u64, IpcError> {
        let id = self.next_channel_id.fetch_add(1, Ordering::SeqCst);
        let shm = SharedMemory::new(id, owner, size);
        self.shared_memory.push(shm);
        Ok(id)
    }
    
    /// Get shared memory region
    pub fn get_shared_memory(&mut self, id: u64) -> Option<&mut SharedMemory> {
        self.shared_memory.iter_mut().find(|s| s.id == id)
    }
    
    /// Destroy shared memory region
    pub fn destroy_shared_memory(&mut self, id: u64) -> Result<(), IpcError> {
        let idx = self.shared_memory.iter().position(|s| s.id == id);
        if let Some(idx) = idx {
            self.shared_memory.remove(idx);
            Ok(())
        } else {
            Err(IpcError::ResourceNotFound)
        }
    }
    
    /// Clean up resources for a terminated process
    pub fn cleanup_process(&mut self, process_id: u64) {
        // Close channels owned by this process
        self.channels.retain(|c| c.owner != process_id);
        
        // Unmap shared memory
        for shm in &mut self.shared_memory {
            shm.unmap(process_id);
        }
    }
}

/// IPC errors
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IpcError {
    ChannelNotFound,
    ChannelClosed,
    InvalidState,
    MessageTooLarge,
    WouldBlock,
    NoMessage,
    PermissionDenied,
    ResourceNotFound,
    ResourceLimit,
}

/// Global IPC manager
static mut IPC_MANAGER: Option<IpcManager> = None;

/// Initialize IPC subsystem
pub fn init() {
    unsafe {
        IPC_MANAGER = Some(IpcManager::new());
    }
}

/// Create a channel
pub fn create_channel(owner: u64, channel_type: ChannelType) -> Result<ChannelId, IpcError> {
    unsafe {
        if let Some(ref mut manager) = IPC_MANAGER {
            manager.create_channel(owner, channel_type)
        } else {
            Err(IpcError::ResourceNotFound)
        }
    }
}

/// Send message
pub fn send(channel_id: ChannelId, message: Message) -> Result<(), IpcError> {
    unsafe {
        if let Some(ref mut manager) = IPC_MANAGER {
            manager.send(channel_id, message)
        } else {
            Err(IpcError::ChannelNotFound)
        }
    }
}

/// Receive message
pub fn recv(channel_id: ChannelId) -> Result<Message, IpcError> {
    unsafe {
        if let Some(ref mut manager) = IPC_MANAGER {
            manager.recv(channel_id)
        } else {
            Err(IpcError::ChannelNotFound)
        }
    }
}

/// Close channel
pub fn close_channel(channel_id: ChannelId) -> Result<(), IpcError> {
    unsafe {
        if let Some(ref mut manager) = IPC_MANAGER {
            manager.close_channel(channel_id)
        } else {
            Err(IpcError::ChannelNotFound)
        }
    }
}

/// Create shared memory
pub fn create_shared_memory(owner: u64, size: usize) -> Result<u64, IpcError> {
    unsafe {
        if let Some(ref mut manager) = IPC_MANAGER {
            manager.create_shared_memory(owner, size)
        } else {
            Err(IpcError::ResourceNotFound)
        }
    }
}

/// Cleanup process resources
pub fn cleanup_process(process_id: u64) {
    unsafe {
        if let Some(ref mut manager) = IPC_MANAGER {
            manager.cleanup_process(process_id);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_channel_id() {
        let id = ChannelId::new(42);
        assert_eq!(id.as_u64(), 42);
    }

    #[test]
    fn test_message() {
        let msg = Message::new(1, 2, 100, b"hello");
        assert_eq!(msg.header.source, 1);
        assert_eq!(msg.header.destination, 2);
        assert_eq!(msg.payload, b"hello");
    }

    #[test]
    fn test_channel_lifecycle() {
        let mut channel = Channel::new(ChannelId::new(1), 1, ChannelType::Unidirectional);
        
        // Initially connecting
        assert_eq!(channel.state, ChannelState::Connecting);
        
        // Connect to peer
        assert!(channel.connect(2).is_ok());
        assert_eq!(channel.state, ChannelState::Connected);
        
        // Send message
        let msg = Message::new(1, 2, 0, b"test");
        assert!(channel.send(msg).is_ok());
        assert_eq!(channel.pending_count(), 1);
        
        // Receive message
        let received = channel.recv().unwrap();
        assert_eq!(received.payload, b"test");
        
        // Close channel
        channel.close();
        assert_eq!(channel.state, ChannelState::Closed);
    }

    #[test]
    fn test_message_size_limit() {
        let mut channel = Channel::new(ChannelId::new(1), 1, ChannelType::Unidirectional);
        channel.connect(2).unwrap();
        
        // Try to send oversized message
        let large_payload = vec![0u8; MAX_MESSAGE_SIZE + 1];
        let msg = Message::new(1, 2, 0, &large_payload);
        
        assert!(matches!(channel.send(msg), Err(IpcError::MessageTooLarge)));
    }

    #[test]
    fn test_shared_memory_permissions() {
        let perms = SharedMemoryPermissions::READ_WRITE;
        assert!(perms.readable);
        assert!(perms.writable);
        assert!(!perms.executable);
    }
}
