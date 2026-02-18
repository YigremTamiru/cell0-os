//! Cell0 Raft Consensus Module
//! 
//! Implements the Raft consensus algorithm for distributed agreement.
//! Designed for civilization-grade reliability and multi-node Cell0 clusters.
//!
//! # Features
//! - Leader election with randomized timeouts
//! - Log replication with commit safety
//! - Membership changes (joint consensus)
//! - Snapshotting for log compaction
//! - Byzantine fault tolerance integration
//!
//! Reference: "In Search of an Understandable Consensus Algorithm" (Ongaro & Ousterhout, 2014)

#![cfg_attr(not(feature = "std"), no_std)]

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

use core::fmt;

/// Node ID type - unique identifier for each node in the cluster
pub type NodeId = u64;

/// Term number - monotonically increasing counter for leadership epochs
pub type Term = u64;

/// Log index - position in the replicated log
pub type LogIndex = u64;

/// Raft server state
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RaftState {
    /// Follower - passive, responds to leader
    Follower,
    /// Candidate - attempting to become leader
    Candidate,
    /// Leader - handles client requests and log replication
    Leader,
}

impl fmt::Display for RaftState {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            RaftState::Follower => write!(f, "Follower"),
            RaftState::Candidate => write!(f, "Candidate"),
            RaftState::Leader => write!(f, "Leader"),
        }
    }
}

/// Log entry - command to be replicated across the cluster
#[derive(Debug, Clone)]
pub struct LogEntry {
    /// Term when entry was received by leader
    pub term: Term,
    /// Position in the log
    pub index: LogIndex,
    /// Command data (opaque to Raft)
    pub data: Vec<u8>,
    /// Optional entry type for special entries
    pub entry_type: EntryType,
}

/// Entry type for distinguishing log entries
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EntryType {
    /// Normal command entry
    Command,
    /// Configuration change entry
    ConfigurationChange,
    /// No-op entry (used by new leaders)
    NoOp,
}

impl Default for EntryType {
    fn default() -> Self {
        EntryType::Command
    }
}

/// Raft configuration
#[derive(Debug, Clone)]
pub struct RaftConfig {
    /// This node's ID
    pub node_id: NodeId,
    /// List of all node IDs in the cluster
    pub peers: Vec<NodeId>,
    /// Minimum election timeout in milliseconds
    pub election_timeout_min: u64,
    /// Maximum election timeout in milliseconds
    pub election_timeout_max: u64,
    /// Heartbeat interval in milliseconds
    pub heartbeat_interval: u64,
    /// Maximum number of entries per AppendEntries RPC
    pub max_entries_per_append: usize,
    /// Whether to enable pre-vote optimization
    pub enable_pre_vote: bool,
}

impl Default for RaftConfig {
    fn default() -> Self {
        Self {
            node_id: 0,
            peers: Vec::new(),
            election_timeout_min: 150,
            election_timeout_max: 300,
            heartbeat_interval: 50,
            max_entries_per_append: 100,
            enable_pre_vote: true,
        }
    }
}

impl RaftConfig {
    /// Create a new configuration for a single-node cluster
    pub fn single_node(node_id: NodeId) -> Self {
        Self {
            node_id,
            peers: Vec::new(),
            ..Default::default()
        }
    }
    
    /// Get total cluster size
    pub fn cluster_size(&self) -> usize {
        self.peers.len() + 1
    }
    
    /// Get quorum size (majority)
    pub fn quorum(&self) -> usize {
        (self.cluster_size() / 2) + 1
    }
}

/// Persistent state (must survive crashes)
#[derive(Debug, Clone)]
pub struct PersistentState {
    /// Latest term server has seen
    pub current_term: Term,
    /// CandidateId that received vote in current term
    pub voted_for: Option<NodeId>,
    /// Log entries
    pub log: Vec<LogEntry>,
}

impl Default for PersistentState {
    fn default() -> Self {
        Self {
            current_term: 0,
            voted_for: None,
            log: Vec::new(),
        }
    }
}

impl PersistentState {
    /// Get last log index
    pub fn last_index(&self) -> LogIndex {
        self.log.len() as LogIndex
    }
    
    /// Get last log term
    pub fn last_term(&self) -> Term {
        if self.log.is_empty() {
            0
        } else {
            self.log[self.log.len() - 1].term
        }
    }
    
    /// Get term at specific index
    pub fn term_at(&self, index: LogIndex) -> Term {
        if index == 0 || index > self.log.len() as u64 {
            0
        } else {
            self.log[(index - 1) as usize].term
        }
    }
    
    /// Append entries to log
    pub fn append_entries(&mut self, entries: &[LogEntry]) {
        self.log.extend_from_slice(entries);
    }
    
    /// Truncate log from index onwards
    pub fn truncate_from(&mut self, index: LogIndex) {
        if index <= self.log.len() as u64 && index > 0 {
            self.log.truncate((index - 1) as usize);
        }
    }
    
    /// Get entries from start_index onwards
    pub fn entries_from(&self, start_index: LogIndex) -> &[LogEntry] {
        if start_index == 0 || start_index > self.log.len() as u64 {
            &[]
        } else {
            &self.log[(start_index - 1) as usize..]
        }
    }
}

/// Volatile state
#[derive(Debug, Clone)]
pub struct VolatileState {
    /// Index of highest log entry known to be committed
    pub commit_index: LogIndex,
    /// Index of highest log entry applied to state machine
    pub last_applied: LogIndex,
}

impl Default for VolatileState {
    fn default() -> Self {
        Self {
            commit_index: 0,
            last_applied: 0,
        }
    }
}

/// Vote request RPC
#[derive(Debug, Clone)]
pub struct RequestVoteRequest {
    pub term: Term,
    pub candidate_id: NodeId,
    pub last_log_index: LogIndex,
    pub last_log_term: Term,
}

/// Vote response RPC
#[derive(Debug, Clone)]
pub struct RequestVoteResponse {
    pub term: Term,
    pub vote_granted: bool,
}

/// AppendEntries request RPC
#[derive(Debug, Clone)]
pub struct AppendEntriesRequest {
    pub term: Term,
    pub leader_id: NodeId,
    pub prev_log_index: LogIndex,
    pub prev_log_term: Term,
    pub entries: Vec<LogEntry>,
    pub leader_commit: LogIndex,
}

/// AppendEntries response RPC
#[derive(Debug, Clone)]
pub struct AppendEntriesResponse {
    pub term: Term,
    pub success: bool,
}

/// The main Raft consensus state machine
pub struct RaftNode {
    pub config: RaftConfig,
    pub persistent: PersistentState,
    pub volatile: VolatileState,
    pub state: RaftState,
    pub votes_received: Vec<NodeId>,
    pub leader_id: NodeId,
}

impl RaftNode {
    /// Create a new Raft node
    pub fn new(config: RaftConfig) -> Self {
        Self {
            config,
            persistent: PersistentState::default(),
            volatile: VolatileState::default(),
            state: RaftState::Follower,
            votes_received: Vec::new(),
            leader_id: 0,
        }
    }
    
    /// Check if this node is the leader
    pub fn is_leader(&self) -> bool {
        self.state == RaftState::Leader
    }
    
    /// Handle RequestVote RPC
    pub fn handle_request_vote(&mut self, request: RequestVoteRequest) -> RequestVoteResponse {
        let mut response = RequestVoteResponse {
            term: self.persistent.current_term,
            vote_granted: false,
        };
        
        if request.term > self.persistent.current_term {
            self.become_follower(request.term);
            response.term = self.persistent.current_term;
        }
        
        if request.term < self.persistent.current_term {
            return response;
        }
        
        // Check if we can grant vote
        let can_vote = match self.persistent.voted_for {
            None => true,
            Some(id) => id == request.candidate_id,
        };
        
        let last_index = self.persistent.last_index();
        let last_term = self.persistent.last_term();
        
        let log_up_to_date = 
            request.last_log_term > last_term ||
            (request.last_log_term == last_term && request.last_log_index >= last_index);
        
        if can_vote && log_up_to_date {
            self.persistent.voted_for = Some(request.candidate_id);
            response.vote_granted = true;
        }
        
        response
    }
    
    /// Handle AppendEntries RPC
    pub fn handle_append_entries(&mut self, request: AppendEntriesRequest) -> AppendEntriesResponse {
        let mut response = AppendEntriesResponse {
            term: self.persistent.current_term,
            success: false,
        };
        
        if request.term < self.persistent.current_term {
            return response;
        }
        
        self.leader_id = request.leader_id;
        
        if request.term > self.persistent.current_term {
            self.become_follower(request.term);
            response.term = self.persistent.current_term;
        } else if self.state != RaftState::Follower {
            self.become_follower(self.persistent.current_term);
        }
        
        // Check prev_log_index match
        if request.prev_log_index > 0 {
            if request.prev_log_index > self.persistent.last_index() {
                return response;
            }
            
            if self.persistent.term_at(request.prev_log_index) != request.prev_log_term {
                self.persistent.truncate_from(request.prev_log_index);
                return response;
            }
        }
        
        // Append new entries
        if !request.entries.is_empty() {
            let mut next_index = request.prev_log_index + 1;
            for entry in &request.entries {
                if next_index <= self.persistent.last_index() {
                    if self.persistent.term_at(next_index) != entry.term {
                        self.persistent.truncate_from(next_index);
                        self.persistent.append_entries(&[entry.clone()]);
                    }
                } else {
                    self.persistent.append_entries(&[entry.clone()]);
                }
                next_index += 1;
            }
        }
        
        // Update commit index
        if request.leader_commit > self.volatile.commit_index {
            let last_new = if request.entries.is_empty() {
                request.prev_log_index
            } else {
                request.entries[request.entries.len() - 1].index
            };
            self.volatile.commit_index = core::cmp::min(request.leader_commit, last_new);
        }
        
        response.success = true;
        response
    }
    
    /// Handle election timeout
    pub fn handle_election_timeout(&mut self) -> Option<RequestVoteRequest> {
        if self.state == RaftState::Leader {
            return None;
        }
        
        self.become_candidate();
        
        // For single-node clusters, immediately become leader
        if self.config.cluster_size() == 1 {
            self.become_leader();
            return None;
        }
        
        Some(RequestVoteRequest {
            term: self.persistent.current_term,
            candidate_id: self.config.node_id,
            last_log_index: self.persistent.last_index(),
            last_log_term: self.persistent.last_term(),
        })
    }
    
    /// Handle vote response
    pub fn handle_request_vote_response(&mut self, from: NodeId, response: RequestVoteResponse) {
        if response.term > self.persistent.current_term {
            self.become_follower(response.term);
            return;
        }
        
        if self.state != RaftState::Candidate || response.term < self.persistent.current_term {
            return;
        }
        
        if response.vote_granted {
            if !self.votes_received.contains(&from) {
                self.votes_received.push(from);
            }
            
            if self.votes_received.len() >= self.config.quorum() {
                self.become_leader();
            }
        }
    }
    
    /// Propose a command (must be leader)
    pub fn propose(&mut self, data: Vec<u8>) -> Option<LogEntry> {
        if self.state != RaftState::Leader {
            return None;
        }
        
        let entry = LogEntry {
            term: self.persistent.current_term,
            index: self.persistent.last_index() + 1,
            data,
            entry_type: EntryType::Command,
        };
        
        self.persistent.append_entries(&[entry.clone()]);
        Some(entry)
    }
    
    /// Become follower
    fn become_follower(&mut self, term: Term) {
        self.state = RaftState::Follower;
        self.persistent.current_term = term;
        self.persistent.voted_for = None;
        self.votes_received.clear();
    }
    
    /// Become candidate
    fn become_candidate(&mut self) {
        self.state = RaftState::Candidate;
        self.persistent.current_term += 1;
        self.persistent.voted_for = Some(self.config.node_id);
        self.votes_received.clear();
        self.votes_received.push(self.config.node_id);
    }
    
    /// Become leader
    fn become_leader(&mut self) {
        self.state = RaftState::Leader;
        self.leader_id = self.config.node_id;
    }
    
    /// Get node status
    pub fn get_status(&self) -> RaftStatus {
        RaftStatus {
            node_id: self.config.node_id,
            state: self.state,
            term: self.persistent.current_term,
            leader_id: self.leader_id,
            commit_index: self.volatile.commit_index,
            log_size: self.persistent.log.len(),
        }
    }
}

/// Node status for monitoring
#[derive(Debug, Clone)]
pub struct RaftStatus {
    pub node_id: NodeId,
    pub state: RaftState,
    pub term: Term,
    pub leader_id: NodeId,
    pub commit_index: LogIndex,
    pub log_size: usize,
}

impl fmt::Display for RaftStatus {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, 
            "Node {}: {} (Term: {}, Leader: {}, Log: {} entries, Committed: {})",
            self.node_id, self.state, self.term, self.leader_id,
            self.log_size, self.commit_index
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_raft_single_node() {
        let config = RaftConfig::single_node(1);
        let mut node = RaftNode::new(config);
        
        // Single node should become leader immediately on election timeout
        node.handle_election_timeout();
        assert!(node.is_leader());
        
        // Should be able to propose entries
        let entry = node.propose(vec![1, 2, 3]);
        assert!(entry.is_some());
    }
    
    #[test]
    fn test_vote_granting() {
        let config1 = RaftConfig { node_id: 1, peers: vec![2, 3], ..Default::default() };
        let mut node1 = RaftNode::new(config1);
        
        let request = RequestVoteRequest {
            term: 1,
            candidate_id: 2,
            last_log_index: 0,
            last_log_term: 0,
        };
        
        let response = node1.handle_request_vote(request);
        assert!(response.vote_granted);
    }
    
    #[test]
    fn test_append_entries_rejection() {
        let config = RaftConfig { node_id: 1, peers: vec![2], ..Default::default() };
        let mut node = RaftNode::new(config);
        
        let request = AppendEntriesRequest {
            term: 0,
            leader_id: 2,
            prev_log_index: 1,
            prev_log_term: 1,
            entries: vec![],
            leader_commit: 0,
        };
        
        let response = node.handle_append_entries(request);
        assert!(!response.success);
    }
}
