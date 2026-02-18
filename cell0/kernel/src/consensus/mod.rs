//! Raft Consensus Module
//! 
//! Implements the Raft distributed consensus algorithm for Cell0 kernel.
//! Provides replicated state machine functionality for distributed kernels.
//!
//! # Architecture
//! - Single-decree (log-based) consensus
//! - Leader election with randomized timeouts
//! - Log replication and commitment
//! - Safety guarantees via term numbers and log validation

pub mod transport;

use core::fmt::Debug;

#[cfg(not(feature = "std"))]
use alloc::vec::Vec;
#[cfg(not(feature = "std"))]
use alloc::string::String;

#[cfg(feature = "std")]
use std::vec::Vec;
#[cfg(feature = "std")]
use std::string::String;

/// Unique identifier for a Raft node
pub type NodeId = u64;

/// Term number (monotonically increasing)
pub type Term = u64;

/// Log entry index (1-based)
pub type LogIndex = u64;

/// Raft node states
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NodeState {
    /// Follower: receives RPCs from leader, responds to requests
    Follower,
    /// Candidate: running for election
    Candidate,
    /// Leader: manages log replication and cluster coordination
    Leader,
}

/// A single entry in the Raft log
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LogEntry<T: Clone> {
    /// Term when entry was received by leader
    pub term: Term,
    /// Index position in the log (1-based)
    pub index: LogIndex,
    /// Command to apply to state machine
    pub command: T,
    /// Entry type for special entries
    pub entry_type: EntryType,
}

/// Types of log entries
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EntryType {
    /// Normal user command
    Command,
    /// Configuration change (membership update)
    ConfigChange,
    /// No-op entry from leader (prevents stale reads)
    NoOp,
}

impl Default for EntryType {
    fn default() -> Self {
        EntryType::Command
    }
}

/// Persistent state (must be saved to stable storage)
#[derive(Debug, Clone)]
pub struct PersistentState<T: Clone> {
    /// Latest term server has seen
    pub current_term: Term,
    /// CandidateId that received vote in current term (None if none)
    pub voted_for: Option<NodeId>,
    /// Log entries; each entry contains command for state machine
    pub log: Vec<LogEntry<T>>,
}

impl<T: Clone> PersistentState<T> {
    /// Create new persistent state
    pub fn new() -> Self {
        Self {
            current_term: 0,
            voted_for: None,
            log: Vec::new(),
        }
    }
    
    /// Get last log index
    pub fn last_index(&self) -> LogIndex {
        self.log.len() as LogIndex
    }
    
    /// Get last log term
    pub fn last_term(&self) -> Term {
        self.log.last().map(|e| e.term).unwrap_or(0)
    }
    
    /// Get term at specific index
    pub fn term_at(&self, index: LogIndex) -> Term {
        if index == 0 {
            0
        } else {
            self.log.get((index - 1) as usize)
                .map(|e| e.term)
                .unwrap_or(0)
        }
    }
    
    /// Get entry at specific index
    pub fn entry_at(&self, index: LogIndex) -> Option<&LogEntry<T>> {
        if index == 0 {
            None
        } else {
            self.log.get((index - 1) as usize)
        }
    }
}

impl<T: Clone> Default for PersistentState<T> {
    fn default() -> Self {
        Self::new()
    }
}

/// Volatile state for leaders (reinitialized after election)
#[derive(Debug, Clone)]
pub struct LeaderState {
    /// For each server, index of the next log entry to send
    pub next_index: Vec<LogIndex>,
    /// For each server, index of highest log entry known to be replicated
    pub match_index: Vec<LogIndex>,
}

impl LeaderState {
    /// Create new leader state for given cluster size
    pub fn new(node_count: usize, last_log_index: LogIndex) -> Self {
        Self {
            next_index: vec![last_log_index + 1; node_count],
            match_index: vec![0; node_count],
        }
    }
    
    /// Reset state after election
    pub fn reset(&mut self, last_log_index: LogIndex) {
        for i in 0..self.next_index.len() {
            self.next_index[i] = last_log_index + 1;
            self.match_index[i] = 0;
        }
    }
}

/// Raft configuration
#[derive(Debug, Clone)]
pub struct Config {
    /// This node's ID
    pub node_id: NodeId,
    /// All node IDs in the cluster (including this one)
    pub peers: Vec<NodeId>,
    /// Election timeout minimum (ms)
    pub election_timeout_min: u64,
    /// Election timeout maximum (ms)
    pub election_timeout_max: u64,
    /// Heartbeat interval (ms)
    pub heartbeat_interval: u64,
    /// Maximum log entries per AppendEntries RPC
    pub max_entries_per_rpc: usize,
}

impl Config {
    /// Create configuration with sensible defaults
    pub fn new(node_id: NodeId, peers: Vec<NodeId>) -> Self {
        Self {
            node_id,
            peers,
            election_timeout_min: 150,
            election_timeout_max: 300,
            heartbeat_interval: 50,
            max_entries_per_rpc: 100,
        }
    }
    
    /// Get index of this node in peers list
    pub fn my_index(&self) -> usize {
        self.peers.iter().position(|&id| id == self.node_id).unwrap_or(0)
    }
    
    /// Get number of nodes in cluster
    pub fn cluster_size(&self) -> usize {
        self.peers.len()
    }
    
    /// Get quorum size (majority)
    pub fn quorum(&self) -> usize {
        (self.peers.len() / 2) + 1
    }
}

/// RequestVote RPC arguments
#[derive(Debug, Clone)]
pub struct RequestVoteArgs {
    /// Candidate's term
    pub term: Term,
    /// Candidate requesting vote
    pub candidate_id: NodeId,
    /// Index of candidate's last log entry
    pub last_log_index: LogIndex,
    /// Term of candidate's last log entry
    pub last_log_term: Term,
}

/// RequestVote RPC reply
#[derive(Debug, Clone)]
pub struct RequestVoteReply {
    /// Current term, for candidate to update itself
    pub term: Term,
    /// True means candidate received vote
    pub vote_granted: bool,
    /// Reason for denial (for debugging)
    pub reason: Option<String>,
}

/// AppendEntries RPC arguments
#[derive(Debug, Clone)]
pub struct AppendEntriesArgs<T: Clone> {
    /// Leader's term
    pub term: Term,
    /// Leader ID so follower can redirect clients
    pub leader_id: NodeId,
    /// Index of log entry immediately preceding new ones
    pub prev_log_index: LogIndex,
    /// Term of prev_log_index entry
    pub prev_log_term: Term,
    /// Log entries to store (empty for heartbeat)
    pub entries: Vec<LogEntry<T>>,
    /// Leader's commit_index
    pub leader_commit: LogIndex,
}

/// AppendEntries RPC reply
#[derive(Debug, Clone)]
pub struct AppendEntriesReply {
    /// Current term, for leader to update itself
    pub term: Term,
    /// True if follower contained entry matching prev_log_index and prev_log_term
    pub success: bool,
    /// Conflict information for log optimization
    pub conflict_info: Option<LogConflict>,
}

/// Log conflict information for AppendEntries optimization
#[derive(Debug, Clone)]
pub struct LogConflict {
    /// Term in conflicting entry (if any)
    pub conflict_term: Term,
    /// First index it stores for conflict_term
    pub conflict_index: LogIndex,
}

/// Events that can be triggered by Raft operations
#[derive(Debug, Clone)]
pub enum Event<T: Clone> {
    /// Become leader (need to initialize leader state)
    BecameLeader,
    /// Step down from leadership
    SteppedDown { new_term: Term },
    /// Entries committed (can apply to state machine)
    Committed { entries: Vec<LogEntry<T>> },
    /// Vote request to send to peer
    SendRequestVote { peer: NodeId, args: RequestVoteArgs },
    /// AppendEntries to send to peer  
    SendAppendEntries { peer: NodeId, args: AppendEntriesArgs<T> },
    /// Save persistent state
    PersistState,
    /// Election timeout should be reset
    ResetElectionTimer,
    /// Leader should send heartbeats
    SendHeartbeats,
}

/// The Raft state machine
pub struct Raft<T: Clone + Debug> {
    /// Configuration
    pub config: Config,
    /// Persistent state
    pub persistent: PersistentState<T>,
    /// Volatile state: commit_index
    pub commit_index: LogIndex,
    /// Volatile state: last_applied
    pub last_applied: LogIndex,
    /// Current node state
    pub state: NodeState,
    /// Leader state (only valid when state == Leader)
    pub leader_state: Option<LeaderState>,
    /// Votes received in current election (only valid when state == Candidate)
    pub votes_received: Vec<NodeId>,
    /// Pending events to process
    pub pending_events: Vec<Event<T>>,
}

impl<T: Clone + Debug> Raft<T> {
    /// Create new Raft node
    pub fn new(config: Config) -> Self {
        let leader_state = None;
        
        Self {
            config,
            persistent: PersistentState::new(),
            commit_index: 0,
            last_applied: 0,
            state: NodeState::Follower,
            leader_state,
            votes_received: Vec::new(),
            pending_events: Vec::new(),
        }
    }
    
    /// Initialize as leader (for single-node clusters or testing)
    pub fn become_leader(&mut self) {
        self.state = NodeState::Leader;
        self.leader_state = Some(LeaderState::new(
            self.config.cluster_size(),
            self.persistent.last_index()
        ));
        self.pending_events.push(Event::BecameLeader);
        self.pending_events.push(Event::SendHeartbeats);
    }
    
    /// Start election (called on election timeout)
    pub fn start_election(&mut self) {
        self.state = NodeState::Candidate;
        self.persistent.current_term += 1;
        self.persistent.voted_for = Some(self.config.node_id);
        self.votes_received = vec![self.config.node_id]; // Vote for self
        
        self.pending_events.push(Event::PersistState);
        
        // Send RequestVote to all peers
        let args = RequestVoteArgs {
            term: self.persistent.current_term,
            candidate_id: self.config.node_id,
            last_log_index: self.persistent.last_index(),
            last_log_term: self.persistent.last_term(),
        };
        
        for &peer in &self.config.peers {
            if peer != self.config.node_id {
                self.pending_events.push(Event::SendRequestVote {
                    peer,
                    args: args.clone(),
                });
            }
        }
        
        // Reset election timer
        self.pending_events.push(Event::ResetElectionTimer);
        
        // Check if we already have majority (single-node cluster)
        if self.votes_received.len() >= self.config.quorum() {
            self.become_leader();
        }
    }
    
    /// Handle RequestVote RPC
    pub fn handle_request_vote(&mut self, args: RequestVoteArgs) -> RequestVoteReply {
        // If term < current_term, reject
        if args.term < self.persistent.current_term {
            return RequestVoteReply {
                term: self.persistent.current_term,
                vote_granted: false,
                reason: Some("Stale term".to_string()),
            };
        }
        
        // If term > current_term, step down
        if args.term > self.persistent.current_term {
            self.step_down(args.term);
        }
        
        // Check if log is up-to-date
        let my_last_term = self.persistent.last_term();
        let my_last_index = self.persistent.last_index();
        
        let log_is_up_to_date = 
            args.last_log_term > my_last_term ||
            (args.last_log_term == my_last_term && args.last_log_index >= my_last_index);
        
        if !log_is_up_to_date {
            return RequestVoteReply {
                term: self.persistent.current_term,
                vote_granted: false,
                reason: Some("Log not up-to-date".to_string()),
            };
        }
        
        // Check if we can grant vote
        let can_vote = self.persistent.voted_for.is_none() ||
            self.persistent.voted_for == Some(args.candidate_id);
        
        if can_vote {
            self.persistent.voted_for = Some(args.candidate_id);
            self.pending_events.push(Event::PersistState);
            self.pending_events.push(Event::ResetElectionTimer);
            
            RequestVoteReply {
                term: self.persistent.current_term,
                vote_granted: true,
                reason: None,
            }
        } else {
            RequestVoteReply {
                term: self.persistent.current_term,
                vote_granted: false,
                reason: Some("Already voted".to_string()),
            }
        }
    }
    
    /// Handle RequestVote reply
    pub fn handle_request_vote_reply(&mut self, from: NodeId, reply: RequestVoteReply) {
        // If term > current_term, step down
        if reply.term > self.persistent.current_term {
            self.step_down(reply.term);
            return;
        }
        
        // Ignore if not candidate or stale term
        if self.state != NodeState::Candidate || reply.term != self.persistent.current_term {
            return;
        }
        
        if reply.vote_granted {
            // Record vote
            if !self.votes_received.contains(&from) {
                self.votes_received.push(from);
            }
            
            // Check if we have majority
            if self.votes_received.len() >= self.config.quorum() {
                self.become_leader();
            }
        }
    }
    
    /// Handle AppendEntries RPC
    pub fn handle_append_entries(&mut self, args: AppendEntriesArgs<T>) -> AppendEntriesReply {
        // If term < current_term, reject
        if args.term < self.persistent.current_term {
            return AppendEntriesReply {
                term: self.persistent.current_term,
                success: false,
                conflict_info: None,
            };
        }
        
        // Reset election timer on valid RPC
        self.pending_events.push(Event::ResetElectionTimer);
        
        // If term > current_term, step down
        if args.term > self.persistent.current_term {
            self.step_down(args.term);
        }
        
        // Step down if we're a leader/candidate receiving valid AppendEntries
        if self.state != NodeState::Follower {
            self.step_down(args.term);
        }
        
        // Check log consistency at prev_log_index
        if args.prev_log_index > 0 {
            if args.prev_log_index > self.persistent.last_index() {
                // We don't have prev_log_index entry
                return AppendEntriesReply {
                    term: self.persistent.current_term,
                    success: false,
                    conflict_info: Some(LogConflict {
                        conflict_term: 0,
                        conflict_index: self.persistent.last_index() + 1,
                    }),
                };
            }
            
            let prev_term = self.persistent.term_at(args.prev_log_index);
            if prev_term != args.prev_log_term {
                // Find first index of conflicting term for optimization
                let conflict_term = prev_term;
                let mut conflict_index = args.prev_log_index;
                
                // Find first index with this term
                while conflict_index > 1 &&
                    self.persistent.term_at(conflict_index - 1) == conflict_term {
                    conflict_index -= 1;
                }
                
                return AppendEntriesReply {
                    term: self.persistent.current_term,
                    success: false,
                    conflict_info: Some(LogConflict {
                        conflict_term,
                        conflict_index,
                    }),
                };
            }
        }
        
        // Append new entries (skip duplicates, delete conflicts)
        let mut entries_added = false;
        for (i, entry) in args.entries.iter().enumerate() {
            let index = args.prev_log_index + 1 + i as u64;
            
            if index <= self.persistent.last_index() {
                // Check for conflict
                let existing = self.persistent.entry_at(index).unwrap();
                if existing.term != entry.term {
                    // Delete this and all following entries
                    self.persistent.log.truncate((index - 1) as usize);
                    entries_added = true;
                }
                // Skip if already exists with same term
            } else {
                // Append new entry
                self.persistent.log.push(entry.clone());
                entries_added = true;
            }
        }
        
        if entries_added {
            self.pending_events.push(Event::PersistState);
        }
        
        // Update commit_index
        if args.leader_commit > self.commit_index {
            self.commit_index = args.leader_commit.min(self.persistent.last_index());
            self.check_apply();
        }
        
        AppendEntriesReply {
            term: self.persistent.current_term,
            success: true,
            conflict_info: None,
        }
    }
    
    /// Handle AppendEntries reply
    pub fn handle_append_entries_reply(&mut self, peer: NodeId, args: &AppendEntriesArgs<T>, reply: AppendEntriesReply) {
        // If term > current_term, step down
        if reply.term > self.persistent.current_term {
            self.step_down(reply.term);
            return;
        }
        
        // Ignore if not leader or stale term
        if self.state != NodeState::Leader || reply.term != self.persistent.current_term {
            return;
        }
        
        let peer_idx = self.config.peers.iter().position(|&id| id == peer).unwrap_or(0);
        let leader_state = self.leader_state.as_mut().unwrap();
        
        if reply.success {
            // Update next_index and match_index
            let new_match = args.prev_log_index + args.entries.len() as u64;
            if new_match > leader_state.match_index[peer_idx] {
                leader_state.match_index[peer_idx] = new_match;
                leader_state.next_index[peer_idx] = new_match + 1;
            }
            
            // Check if we can advance commit_index
            self.advance_commit_index();
        } else {
            // Log inconsistency - back off
            if let Some(conflict) = reply.conflict_info {
                // Optimized backoff using conflict info
                if conflict.conflict_term == 0 {
                    leader_state.next_index[peer_idx] = conflict.conflict_index;
                } else {
                    // Find last entry with conflict_term
                    let mut idx = self.persistent.last_index();
                    while idx > 0 && self.persistent.term_at(idx) != conflict.conflict_term {
                        idx -= 1;
                    }
                    if idx > 0 {
                        leader_state.next_index[peer_idx] = idx;
                    } else {
                        leader_state.next_index[peer_idx] = conflict.conflict_index;
                    }
                }
            } else {
                // Simple backoff
                if leader_state.next_index[peer_idx] > 1 {
                    leader_state.next_index[peer_idx] -= 1;
                }
            }
            
            // Retry AppendEntries - queue event instead of calling directly
            let leader_state = self.leader_state.as_ref().unwrap();
            let next_idx = leader_state.next_index[peer_idx];
            let prev_log_index = next_idx - 1;
            let prev_log_term = self.persistent.term_at(prev_log_index);
            
            let entries: Vec<LogEntry<T>> = self.persistent.log
                .iter()
                .skip((next_idx - 1) as usize)
                .take(self.config.max_entries_per_rpc)
                .cloned()
                .collect();
            
            let retry_args = AppendEntriesArgs {
                term: self.persistent.current_term,
                leader_id: self.config.node_id,
                prev_log_index,
                prev_log_term,
                entries,
                leader_commit: self.commit_index,
            };
            
            self.pending_events.push(Event::SendAppendEntries { peer, args: retry_args });
        }
    }
    
    /// Propose a new entry (client request, only valid for leader)
    pub fn propose(&mut self, command: T) -> Result<LogIndex, ProposeError> {
        if self.state != NodeState::Leader {
            return Err(ProposeError::NotLeader);
        }
        
        let entry = LogEntry {
            term: self.persistent.current_term,
            index: self.persistent.last_index() + 1,
            command,
            entry_type: EntryType::Command,
        };
        
        let index = entry.index;
        self.persistent.log.push(entry);
        self.pending_events.push(Event::PersistState);
        
        // Replicate to all peers - collect peers first to avoid borrow issues
        let peers: Vec<NodeId> = self.config.peers.iter()
            .filter(|&&p| p != self.config.node_id)
            .cloned()
            .collect();
        
        for peer in peers {
            self.send_append_entries_to(peer);
        }
        
        Ok(index)
    }
    
    /// Step down to follower
    fn step_down(&mut self, new_term: Term) {
        self.persistent.current_term = new_term;
        self.persistent.voted_for = None;
        self.state = NodeState::Follower;
        self.leader_state = None;
        self.pending_events.push(Event::SteppedDown { new_term });
        self.pending_events.push(Event::PersistState);
    }
    
    /// Advance commit_index based on match_index
    fn advance_commit_index(&mut self) {
        let leader_state = self.leader_state.as_ref().unwrap();
        let last_index = self.persistent.last_index();
        
        // Find highest N where a majority of match_index >= N
        for n in (self.commit_index + 1)..=last_index {
            let term = self.persistent.term_at(n);
            if term != self.persistent.current_term {
                // Raft only commits entries from current term
                continue;
            }
            
            let replicated_count = leader_state.match_index
                .iter()
                .filter(|&&m| m >= n)
                .count();
            
            // Include leader (self)
            if replicated_count + 1 >= self.config.quorum() {
                self.commit_index = n;
            } else {
                break;
            }
        }
        
        self.check_apply();
    }
    
    /// Check and apply newly committed entries
    fn check_apply(&mut self) {
        if self.commit_index > self.last_applied {
            let entries: Vec<LogEntry<T>> = ((self.last_applied + 1)..=self.commit_index)
                .filter_map(|i| self.persistent.entry_at(i).cloned())
                .collect();
            
            self.last_applied = self.commit_index;
            
            if !entries.is_empty() {
                self.pending_events.push(Event::Committed { entries });
            }
        }
    }
    
    /// Send AppendEntries to specific peer
    fn send_append_entries_to(&mut self, peer: NodeId) {
        let leader_state = self.leader_state.as_ref().unwrap();
        let peer_idx = self.config.peers.iter().position(|&id| id == peer).unwrap_or(0);
        
        let next_idx = leader_state.next_index[peer_idx];
        let prev_log_index = next_idx - 1;
        let prev_log_term = self.persistent.term_at(prev_log_index);
        
        // Get entries to send
        let entries: Vec<LogEntry<T>> = self.persistent.log
            .iter()
            .skip((next_idx - 1) as usize)
            .take(self.config.max_entries_per_rpc)
            .cloned()
            .collect();
        
        let args = AppendEntriesArgs {
            term: self.persistent.current_term,
            leader_id: self.config.node_id,
            prev_log_index,
            prev_log_term,
            entries,
            leader_commit: self.commit_index,
        };
        
        self.pending_events.push(Event::SendAppendEntries { peer, args });
    }
    
    /// Generate heartbeats for all peers (call periodically when leader)
    pub fn send_heartbeats(&mut self) {
        if self.state != NodeState::Leader {
            return;
        }
        
        // Collect peers first to avoid borrow issues
        let peers: Vec<NodeId> = self.config.peers.iter()
            .filter(|&&p| p != self.config.node_id)
            .cloned()
            .collect();
        
        for peer in peers {
            self.send_append_entries_to(peer);
        }
    }
    
    /// Take pending events for processing
    pub fn take_events(&mut self) -> Vec<Event<T>> {
        core::mem::take(&mut self.pending_events)
    }
    
    /// Record vote received from peer
    pub fn record_vote(&mut self, peer: NodeId) {
        if !self.votes_received.contains(&peer) {
            self.votes_received.push(peer);
        }
        
        // Check if we have majority
        if self.state == NodeState::Candidate &&
            self.votes_received.len() >= self.config.quorum() {
            self.become_leader();
        }
    }
}

/// Error types for propose operation
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProposeError {
    NotLeader,
    ClusterNotReady,
    Timeout,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_persistent_state_new() {
        let state: PersistentState<u64> = PersistentState::new();
        assert_eq!(state.current_term, 0);
        assert_eq!(state.voted_for, None);
        assert!(state.log.is_empty());
    }
    
    #[test]
    fn test_persistent_state_last_index() {
        let mut state: PersistentState<u64> = PersistentState::new();
        assert_eq!(state.last_index(), 0);
        
        state.log.push(LogEntry {
            term: 1,
            index: 1,
            command: 42,
            entry_type: EntryType::Command,
        });
        assert_eq!(state.last_index(), 1);
    }
    
    #[test]
    fn test_config_quorum() {
        let config = Config::new(1, vec![1, 2, 3, 4, 5]);
        assert_eq!(config.quorum(), 3);
        
        let config2 = Config::new(1, vec![1, 2, 3]);
        assert_eq!(config2.quorum(), 2);
    }
    
    #[test]
    fn test_raft_start_election() {
        let config = Config::new(1, vec![1, 2, 3]);
        let mut raft: Raft<u64> = Raft::new(config);
        
        raft.start_election();
        
        assert_eq!(raft.state, NodeState::Candidate);
        assert_eq!(raft.persistent.current_term, 1);
        assert_eq!(raft.persistent.voted_for, Some(1));
        
        // Should have events
        assert!(!raft.pending_events.is_empty());
    }
    
    #[test]
    fn test_raft_handle_request_vote_higher_term() {
        let config = Config::new(1, vec![1, 2, 3]);
        let mut raft: Raft<u64> = Raft::new(config);
        
        // Simulate peer with higher term
        let args = RequestVoteArgs {
            term: 5,
            candidate_id: 2,
            last_log_index: 0,
            last_log_term: 0,
        };
        
        let reply = raft.handle_request_vote(args);
        
        assert!(reply.vote_granted);
        assert_eq!(raft.persistent.current_term, 5);
        assert_eq!(raft.persistent.voted_for, Some(2));
    }
    
    #[test]
    fn test_raft_propose_not_leader() {
        let config = Config::new(1, vec![1, 2, 3]);
        let mut raft: Raft<u64> = Raft::new(config);
        
        let result = raft.propose(42);
        assert_eq!(result, Err(ProposeError::NotLeader));
    }
    
    #[test]
    fn test_raft_propose_leader() {
        let config = Config::new(1, vec![1]);
        let mut raft: Raft<u64> = Raft::new(config);
        
        raft.become_leader();
        
        let result = raft.propose(42);
        assert_eq!(result, Ok(1));
        assert_eq!(raft.persistent.last_index(), 1);
    }
    
    #[test]
    fn test_raft_record_vote() {
        let config = Config::new(1, vec![1, 2, 3]);
        let mut raft: Raft<u64> = Raft::new(config);
        
        raft.start_election();
        assert_eq!(raft.state, NodeState::Candidate); // Only self vote, quorum=2
        
        // Simulate receiving vote from peer 2
        raft.record_vote(2);
        // Now have 2 votes (self + peer 2), quorum is 2, should become leader
        assert_eq!(raft.state, NodeState::Leader);
    }
}
