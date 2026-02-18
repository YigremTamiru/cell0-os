//! Cell0 Raft Network Transport
//! 
//! Provides network communication layer for Raft consensus,
//! with integration to the Python daemon for actual network I/O.

use crate::raft::*;

#[cfg(not(feature = "std"))]
use alloc::vec::Vec;
#[cfg(not(feature = "std"))]
use alloc::collections::BTreeMap;
#[cfg(not(feature = "std"))]
use alloc::string::String;
#[cfg(feature = "std")]
use std::vec::Vec;
#[cfg(feature = "std")]
use std::collections::BTreeMap;
#[cfg(feature = "std")]
use std::string::String;

/// Network address for a Raft peer
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PeerAddress {
    pub node_id: NodeId,
    pub host: String,
    pub port: u16,
}

impl PeerAddress {
    pub fn new(node_id: NodeId, host: impl Into<String>, port: u16) -> Self {
        Self {
            node_id,
            host: host.into(),
            port,
        }
    }
    
    pub fn to_string(&self) -> String {
        #[cfg(not(feature = "std"))]
        return alloc::format!("{}:{}", self.host, self.port);
        #[cfg(feature = "std")]
        return format!("{}:{}", self.host, self.port);
    }
}

/// Transport trait for network operations
pub trait RaftTransport {
    /// Send RequestVote RPC to a peer
    fn send_request_vote(&mut self, to: NodeId, request: &RequestVoteRequest);
    /// Send AppendEntries RPC to a peer
    fn send_append_entries(&mut self, to: NodeId, request: &AppendEntriesRequest);
    /// Receive messages from network
    fn receive(&mut self) -> Option<RaftMessage>;
    /// Get list of connected peers
    fn connected_peers(&self) -> Vec<NodeId>;
}

/// Message types received from network
#[derive(Debug, Clone)]
pub enum RaftMessage {
    RequestVote { from: NodeId, request: RequestVoteRequest },
    RequestVoteResponse { from: NodeId, response: RequestVoteResponse },
    AppendEntries { from: NodeId, request: AppendEntriesRequest },
    AppendEntriesResponse { from: NodeId, response: AppendEntriesResponse },
    ClientRequest { data: Vec<u8> },
}

/// In-memory transport for testing
pub struct MemoryTransport {
    node_id: NodeId,
    peers: BTreeMap<NodeId, PeerAddress>,
    inbox: Vec<RaftMessage>,
    outbox: Vec<(NodeId, RaftMessage)>,
}

impl MemoryTransport {
    pub fn new(node_id: NodeId) -> Self {
        Self {
            node_id,
            peers: BTreeMap::new(),
            inbox: Vec::new(),
            outbox: Vec::new(),
        }
    }
    
    pub fn add_peer(&mut self, address: PeerAddress) {
        self.peers.insert(address.node_id, address);
    }
    
    pub fn deliver_message(&mut self, message: RaftMessage) {
        self.inbox.push(message);
    }
    
    pub fn get_outbox(&mut self) -> Vec<(NodeId, RaftMessage)> {
        let out = self.outbox.clone();
        self.outbox.clear();
        out
    }
}

impl RaftTransport for MemoryTransport {
    fn send_request_vote(&mut self, to: NodeId, request: &RequestVoteRequest) {
        self.outbox.push((to, RaftMessage::RequestVote {
            from: self.node_id,
            request: request.clone(),
        }));
    }
    
    fn send_append_entries(&mut self, to: NodeId, request: &AppendEntriesRequest) {
        self.outbox.push((to, RaftMessage::AppendEntries {
            from: self.node_id,
            request: request.clone(),
        }));
    }
    
    fn receive(&mut self) -> Option<RaftMessage> {
        self.inbox.pop()
    }
    
    fn connected_peers(&self) -> Vec<NodeId> {
        self.peers.keys().copied().collect()
    }
}

/// Raft server with network integration
pub struct RaftServer<T: RaftTransport> {
    pub node: RaftNode,
    pub transport: T,
    pub addresses: BTreeMap<NodeId, PeerAddress>,
}

impl<T: RaftTransport> RaftServer<T> {
    pub fn new(config: RaftConfig, transport: T) -> Self {
        let node = RaftNode::new(config);
        Self {
            node,
            transport,
            addresses: BTreeMap::new(),
        }
    }
    
    pub fn add_peer(&mut self, address: PeerAddress) {
        self.addresses.insert(address.node_id, address);
    }
    
    /// Process one iteration of the Raft state machine
    pub fn tick(&mut self) {
        // Process incoming messages
        while let Some(message) = self.transport.receive() {
            self.handle_message(message);
        }
        
        // If leader, send heartbeats periodically
        if self.node.state == RaftState::Leader {
            self.send_heartbeats();
        }
    }
    
    fn handle_message(&mut self, message: RaftMessage) {
        match message {
            RaftMessage::RequestVote { from, request } => {
                let response = self.node.handle_request_vote(request);
                self.transport.send_request_vote_response(from, &response);
            }
            RaftMessage::RequestVoteResponse { from, response } => {
                self.node.handle_request_vote_response(from, response);
            }
            RaftMessage::AppendEntries { from, request } => {
                let response = self.node.handle_append_entries(request);
                self.transport.send_append_entries_response(from, &response);
            }
            RaftMessage::AppendEntriesResponse { from: _, response: _ } => {
                // Handle append entries response
            }
            RaftMessage::ClientRequest { data } => {
                self.node.propose(data);
            }
        }
    }
    
    fn send_heartbeats(&mut self) {
        for &peer_id in self.node.config.peers.iter() {
            let request = AppendEntriesRequest {
                term: self.node.persistent.current_term,
                leader_id: self.node.config.node_id,
                prev_log_index: self.node.persistent.last_index(),
                prev_log_term: self.node.persistent.last_term(),
                entries: Vec::new(),
                leader_commit: self.node.volatile.commit_index,
            };
            self.transport.send_append_entries(peer_id, &request);
        }
    }
    
    /// Trigger election timeout
    pub fn election_timeout(&mut self) {
        if let Some(request) = self.node.handle_election_timeout() {
            for &peer_id in self.node.config.peers.iter() {
                self.transport.send_request_vote(peer_id, &request);
            }
        }
    }
    
    /// Propose a command to the cluster
    pub fn propose(&mut self, data: Vec<u8>) -> bool {
        if let Some(entry) = self.node.propose(data) {
            // Replicate to all peers
            for &peer_id in self.node.config.peers.iter() {
                let request = AppendEntriesRequest {
                    term: self.node.persistent.current_term,
                    leader_id: self.node.config.node_id,
                    prev_log_index: entry.index - 1,
                    prev_log_term: self.node.persistent.term_at(entry.index - 1),
                    entries: vec![entry.clone()],
                    leader_commit: self.node.volatile.commit_index,
                };
                self.transport.send_append_entries(peer_id, &request);
            }
            true
        } else {
            false
        }
    }
    
    pub fn is_leader(&self) -> bool {
        self.node.is_leader()
    }
    
    pub fn get_status(&self) -> RaftStatus {
        self.node.get_status()
    }
}

// Extension trait for transports that support responses
trait RaftTransportExt: RaftTransport {
    fn send_request_vote_response(&mut self, to: NodeId, response: &RequestVoteResponse);
    fn send_append_entries_response(&mut self, to: NodeId, response: &AppendEntriesResponse);
}

impl RaftTransportExt for MemoryTransport {
    fn send_request_vote_response(&mut self, to: NodeId, response: &RequestVoteResponse) {
        self.outbox.push((to, RaftMessage::RequestVoteResponse {
            from: self.node_id,
            response: response.clone(),
        }));
    }
    
    fn send_append_entries_response(&mut self, to: NodeId, response: &AppendEntriesResponse) {
        self.outbox.push((to, RaftMessage::AppendEntriesResponse {
            from: self.node_id,
            response: response.clone(),
        }));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    fn create_test_cluster(node_ids: Vec<NodeId>) -> Vec<RaftServer<MemoryTransport>> {
        let mut servers = Vec::new();
        
        for &node_id in &node_ids {
            let peers: Vec<NodeId> = node_ids.iter()
                .filter(|&&id| id != node_id)
                .copied()
                .collect();
            
            let config = RaftConfig {
                node_id,
                peers,
                election_timeout_min: 150,
                election_timeout_max: 300,
                heartbeat_interval: 50,
                max_entries_per_append: 100,
                enable_pre_vote: false,
            };
            
            let transport = MemoryTransport::new(node_id);
            let server = RaftServer::new(config, transport);
            servers.push(server);
        }
        
        servers
    }
    
    #[test]
    fn test_cluster_election() {
        let node_ids = vec![1, 2, 3];
        let mut servers = create_test_cluster(node_ids.clone());
        
        // Trigger election on first node
        servers[0].election_timeout();
        
        // Check that node 1 became candidate and sent vote requests
        let outbox = servers[0].transport.get_outbox();
        assert!(!outbox.is_empty());
        
        // Process vote requests on other nodes
        for msg in outbox {
            let (to, message) = msg;
            if let RaftMessage::RequestVote { from, request } = message {
                let idx = servers.iter().position(|s| s.node.config.node_id == to).unwrap();
                let response = servers[idx].node.handle_request_vote(request);
                
                // Send response back
                servers[0].transport.deliver_message(RaftMessage::RequestVoteResponse {
                    from: to,
                    response,
                });
            }
        }
        
        // Process responses
        while let Some(msg) = servers[0].transport.receive() {
            if let RaftMessage::RequestVoteResponse { from, response } = msg {
                servers[0].node.handle_request_vote_response(from, response);
            }
        }
        
        // Node 1 should now be leader
        assert!(servers[0].is_leader());
    }
}
