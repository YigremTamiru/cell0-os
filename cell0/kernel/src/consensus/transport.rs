//! Raft Network Transport Module
//! 
//! Provides network primitives for Raft consensus communication.
//! Handles RPC serialization/deserialization and reliable message delivery.

use super::{RequestVoteArgs, RequestVoteReply, AppendEntriesArgs, AppendEntriesReply, NodeId};
use core::fmt::Debug;

#[cfg(not(feature = "std"))]
use alloc::vec::Vec;
#[cfg(not(feature = "std"))]
use alloc::string::String;

#[cfg(feature = "std")]
use std::vec::Vec;
#[cfg(feature = "std")]
use std::string::String;

/// Maximum RPC message size
pub const MAX_RPC_SIZE: usize = 65536;

/// RPC message types
#[derive(Debug, Clone)]
pub enum RpcMessage<T: Clone + Debug> {
    /// RequestVote RPC
    RequestVote(RequestVoteArgs),
    /// RequestVote RPC reply
    RequestVoteReply(RequestVoteReply),
    /// AppendEntries RPC  
    AppendEntries(AppendEntriesArgs<T>),
    /// AppendEntries RPC reply
    AppendEntriesReply(NodeId, AppendEntriesReply), // Include sender
    /// InstallSnapshot RPC (for log compaction)
    InstallSnapshot(InstallSnapshotArgs),
    /// InstallSnapshot RPC reply
    InstallSnapshotReply(InstallSnapshotReply),
}

/// InstallSnapshot RPC arguments
#[derive(Debug, Clone)]
pub struct InstallSnapshotArgs {
    /// Leader's term
    pub term: u64,
    /// Leader ID
    pub leader_id: NodeId,
    /// Snapshot replaces all entries up through and including this index
    pub last_included_index: u64,
    /// Term of last_included_index
    pub last_included_term: u64,
    /// Byte offset where chunk is positioned in the snapshot file
    pub offset: u64,
    /// Raw bytes of the snapshot chunk
    pub data: Vec<u8>,
    /// True if this is the last chunk
    pub done: bool,
}

/// InstallSnapshot RPC reply
#[derive(Debug, Clone)]
pub struct InstallSnapshotReply {
    /// Current term for leader
    pub term: u64,
}

/// Network transport trait for Raft
/// 
/// Implementations must provide reliable delivery guarantees.
/// Messages may be lost but should not be corrupted.
pub trait Transport<T: Clone + Debug> {
    /// Error type for transport operations
    type Error: Debug;
    
    /// Send RPC to target node
    fn send_rpc(&mut self, target: NodeId, message: RpcMessage<T>) -> Result<(), Self::Error>;
    
    /// Receive next incoming RPC (non-blocking)
    fn recv_rpc(&mut self) -> Result<Option<(NodeId, RpcMessage<T>)>, Self::Error>;
    
    /// Get this node's ID
    fn node_id(&self) -> NodeId;
    
    /// Get all peer node IDs
    fn peers(&self) -> &[NodeId];
}

/// In-memory transport for testing
pub struct MemoryTransport<T: Clone + Debug> {
    node_id: NodeId,
    peers: Vec<NodeId>,
    inbox: Vec<(NodeId, RpcMessage<T>)>,
}

impl<T: Clone + Debug> MemoryTransport<T> {
    /// Create new in-memory transport
    pub fn new(node_id: NodeId, peers: Vec<NodeId>) -> Self {
        Self {
            node_id,
            peers,
            inbox: Vec::new(),
        }
    }
    
    /// Inject a message into the inbox (used by test harness)
    pub fn inject_message(&mut self, from: NodeId, message: RpcMessage<T>) {
        self.inbox.push((from, message));
    }
    
    /// Get pending outgoing messages (used by test harness)
    pub fn take_outbox(&mut self) -> Vec<(NodeId, RpcMessage<T>)> {
        core::mem::take(&mut self.inbox)
    }
}

impl<T: Clone + Debug> Transport<T> for MemoryTransport<T> {
    type Error = ();
    
    fn send_rpc(&mut self, _target: NodeId, _message: RpcMessage<T>) -> Result<(), Self::Error> {
        // In real implementation, would queue for delivery
        // For memory transport, messages are handled directly by test harness
        Ok(())
    }
    
    fn recv_rpc(&mut self) -> Result<Option<(NodeId, RpcMessage<T>)>, Self::Error> {
        if self.inbox.is_empty() {
            Ok(None)
        } else {
            Ok(Some(self.inbox.remove(0)))
        }
    }
    
    fn node_id(&self) -> NodeId {
        self.node_id
    }
    
    fn peers(&self) -> &[NodeId] {
        &self.peers
    }
}

/// Simple serialization trait for RPC messages
pub trait RpcCodec<T: Clone + Debug> {
    /// Serialize message to bytes
    fn encode(&self, message: &RpcMessage<T>) -> Vec<u8>;
    /// Deserialize message from bytes
    fn decode(&self, data: &[u8]) -> Result<RpcMessage<T>, CodecError>;
}

/// Codec errors
#[derive(Debug, Clone)]
pub enum CodecError {
    /// Data too short
    TooShort,
    /// Invalid message type
    InvalidType,
    /// Deserialization failed
    DeserializationFailed,
    /// Checksum mismatch
    ChecksumMismatch,
}

/// Simple binary codec for testing
pub struct BinaryCodec;

impl BinaryCodec {
    /// Create new binary codec
    pub fn new() -> Self {
        Self
    }
    
    /// Compute simple checksum
    fn checksum(data: &[u8]) -> u32 {
        data.iter().fold(0u32, |acc, &b| acc.wrapping_add(b as u32))
    }
}

impl Default for BinaryCodec {
    fn default() -> Self {
        Self::new()
    }
}

// For now, placeholder implementations
// Real implementation would use a proper serialization format
impl<T: Clone + Debug + Into<Vec<u8>> + TryFrom<Vec<u8>>> RpcCodec<T> for BinaryCodec {
    fn encode(&self, _message: &RpcMessage<T>) -> Vec<u8> {
        // Placeholder: real impl would use protobuf/bincode/etc
        Vec::new()
    }
    
    fn decode(&self, _data: &[u8]) -> Result<RpcMessage<T>, CodecError> {
        // Placeholder
        Err(CodecError::DeserializationFailed)
    }
}

/// Network address for Raft nodes
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NodeAddress {
    /// Node ID
    pub node_id: NodeId,
    /// Host address (IP or hostname)
    pub host: String,
    /// RPC port
    pub rpc_port: u16,
}

impl NodeAddress {
    /// Create new node address
    pub fn new(node_id: NodeId, host: impl Into<String>, rpc_port: u16) -> Self {
        Self {
            node_id,
            host: host.into(),
            rpc_port,
        }
    }
}

/// Connection manager for TCP transport
pub struct ConnectionManager {
    /// This node's address
    pub local_addr: NodeAddress,
    /// Known peer addresses
    pub peers: Vec<NodeAddress>,
}

impl ConnectionManager {
    /// Create new connection manager
    pub fn new(local_addr: NodeAddress) -> Self {
        Self {
            local_addr,
            peers: Vec::new(),
        }
    }
    
    /// Add a peer
    pub fn add_peer(&mut self, addr: NodeAddress) {
        if !self.peers.iter().any(|p| p.node_id == addr.node_id) {
            self.peers.push(addr);
        }
    }
    
    /// Get address for node
    pub fn get_address(&self, node_id: NodeId) -> Option<&NodeAddress> {
        if node_id == self.local_addr.node_id {
            Some(&self.local_addr)
        } else {
            self.peers.iter().find(|p| p.node_id == node_id)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_memory_transport_creation() {
        let transport: MemoryTransport<u64> = MemoryTransport::new(1, vec![2, 3]);
        assert_eq!(transport.node_id(), 1);
        assert_eq!(transport.peers(), &[2, 3]);
    }
    
    #[test]
    fn test_memory_transport_inject_recv() {
        let mut transport: MemoryTransport<u64> = MemoryTransport::new(1, vec![2, 3]);
        
        let args = RequestVoteArgs {
            term: 1,
            candidate_id: 2,
            last_log_index: 0,
            last_log_term: 0,
        };
        
        transport.inject_message(2, RpcMessage::RequestVote(args.clone()));
        
        let (from, msg) = transport.recv_rpc().unwrap().unwrap();
        assert_eq!(from, 2);
        
        match msg {
            RpcMessage::RequestVote(received) => {
                assert_eq!(received.term, 1);
            }
            _ => panic!("Expected RequestVote message"),
        }
    }
    
    #[test]
    fn test_connection_manager() {
        let local = NodeAddress::new(1, "127.0.0.1", 7000);
        let mut manager = ConnectionManager::new(local);
        
        manager.add_peer(NodeAddress::new(2, "127.0.0.1", 7001));
        manager.add_peer(NodeAddress::new(3, "127.0.0.1", 7002));
        
        assert_eq!(manager.peers.len(), 2);
        
        let addr = manager.get_address(2).unwrap();
        assert_eq!(addr.rpc_port, 7001);
    }
}
