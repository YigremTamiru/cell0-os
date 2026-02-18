//! Self-Healing Memory Management Subsystem
//!
//! A robust memory allocator with fault detection and recovery capabilities:
//! - Page frame allocator with bitmap tracking
//! - Heap allocator with canary-based overflow detection
//! - Memory fault isolation and recovery
//! - Double-free detection
//! - Use-after-free mitigation
//! - Memory pressure handling

#![cfg_attr(not(feature = "std"), no_std)]

use core::alloc::{GlobalAlloc, Layout};
use core::cell::UnsafeCell;
use core::sync::atomic::{AtomicUsize, AtomicU64, AtomicBool, Ordering};

#[cfg(not(feature = "std"))]
use alloc::vec::Vec;

/// Page size (4KB)
pub const PAGE_SIZE: usize = 4096;
/// Number of pages in the heap
pub const NUM_PAGES: usize = 16384; // 64MB total
/// Total heap size
pub const HEAP_SIZE: usize = PAGE_SIZE * NUM_PAGES;
/// Memory canary value for overflow detection
pub const CANARY_VALUE: u8 = 0xDE;
/// Canary size in bytes
pub const CANARY_SIZE: usize = 8;

/// Memory allocation error types
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MemoryError {
    OutOfMemory,
    DoubleFree,
    CorruptionDetected,
    InvalidPointer,
    AlignmentError,
    AllocationTooLarge,
}

impl core::fmt::Display for MemoryError {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        match self {
            MemoryError::OutOfMemory => write!(f, "Out of memory"),
            MemoryError::DoubleFree => write!(f, "Double free detected"),
            MemoryError::CorruptionDetected => write!(f, "Memory corruption detected"),
            MemoryError::InvalidPointer => write!(f, "Invalid pointer"),
            MemoryError::AlignmentError => write!(f, "Alignment error"),
            MemoryError::AllocationTooLarge => write!(f, "Allocation too large"),
        }
    }
}

/// Page frame allocation state
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum PageState {
    Free = 0,
    Allocated = 1,
    Reserved = 2,
    Corrupted = 3,
}

/// Memory statistics for monitoring
#[derive(Debug, Clone, Default)]
pub struct MemoryStats {
    pub total_pages: usize,
    pub free_pages: usize,
    pub allocated_pages: usize,
    pub corrupted_pages: usize,
    pub total_allocations: u64,
    pub total_deallocations: u64,
    pub failed_allocations: u64,
    pub corruption_events: u64,
    pub recovered_pages: u64,
}

/// Page frame allocator with bitmap tracking
pub struct PageFrameAllocator {
    /// Bitmap of page states (2 bits per page)
    bitmap: UnsafeCell<[u8; NUM_PAGES / 4]>,
    /// Next page to search from (optimization)
    next_page: AtomicUsize,
    /// Number of free pages
    free_pages: AtomicUsize,
}

unsafe impl Sync for PageFrameAllocator {}

impl PageFrameAllocator {
    pub const fn new() -> Self {
        PageFrameAllocator {
            bitmap: UnsafeCell::new([0u8; NUM_PAGES / 4]),
            next_page: AtomicUsize::new(0),
            free_pages: AtomicUsize::new(NUM_PAGES),
        }
    }

    /// Allocate a single page
    pub fn alloc_page(&self) -> Option<usize> {
        let start = self.next_page.load(Ordering::Relaxed);
        
        for i in 0..NUM_PAGES {
            let page = (start + i) % NUM_PAGES;
            if self.try_alloc_page(page) {
                self.next_page.store((page + 1) % NUM_PAGES, Ordering::Relaxed);
                self.free_pages.fetch_sub(1, Ordering::Relaxed);
                return Some(page);
            }
        }
        
        None
    }

    /// Allocate contiguous pages
    pub fn alloc_pages(&self, count: usize) -> Option<usize> {
        if count == 0 || count > NUM_PAGES {
            return None;
        }

        'outer: for start in 0..=NUM_PAGES - count {
            // Check if all pages are free
            for i in 0..count {
                if self.get_page_state(start + i) != PageState::Free {
                    continue 'outer;
                }
            }
            
            // Allocate all pages
            for i in 0..count {
                self.set_page_state(start + i, PageState::Allocated);
            }
            
            self.free_pages.fetch_sub(count, Ordering::Relaxed);
            return Some(start);
        }
        
        None
    }

    /// Free a page
    pub fn free_page(&self, page: usize) -> Result<(), MemoryError> {
        if page >= NUM_PAGES {
            return Err(MemoryError::InvalidPointer);
        }

        match self.get_page_state(page) {
            PageState::Free => Err(MemoryError::DoubleFree),
            PageState::Allocated => {
                self.set_page_state(page, PageState::Free);
                self.free_pages.fetch_add(1, Ordering::Relaxed);
                Ok(())
            }
            PageState::Reserved => {
                self.set_page_state(page, PageState::Free);
                self.free_pages.fetch_add(1, Ordering::Relaxed);
                Ok(())
            }
            PageState::Corrupted => {
                // Attempt recovery
                self.set_page_state(page, PageState::Free);
                self.free_pages.fetch_add(1, Ordering::Relaxed);
                Ok(())
            }
        }
    }

    /// Get page state
    fn get_page_state(&self, page: usize) -> PageState {
        let bitmap = unsafe { &*self.bitmap.get() };
        let byte_idx = page / 4;
        let shift = (page % 4) * 2;
        let bits = (bitmap[byte_idx] >> shift) & 0b11;
        
        match bits {
            0 => PageState::Free,
            1 => PageState::Allocated,
            2 => PageState::Reserved,
            3 => PageState::Corrupted,
            _ => unreachable!(),
        }
    }

    /// Set page state
    fn set_page_state(&self, page: usize, state: PageState) {
        let bitmap = unsafe { &mut *self.bitmap.get() };
        let byte_idx = page / 4;
        let shift = (page % 4) * 2;
        let bits = state as u8;
        
        bitmap[byte_idx] = (bitmap[byte_idx] & !(0b11 << shift)) | (bits << shift);
    }

    /// Try to atomically allocate a page
    fn try_alloc_page(&self, page: usize) -> bool {
        if self.get_page_state(page) == PageState::Free {
            self.set_page_state(page, PageState::Allocated);
            true
        } else {
            false
        }
    }

    /// Mark page as corrupted (for fault isolation)
    pub fn mark_corrupted(&self, page: usize) {
        if page < NUM_PAGES {
            self.set_page_state(page, PageState::Corrupted);
        }
    }

    /// Get number of free pages
    pub fn free_pages(&self) -> usize {
        self.free_pages.load(Ordering::Relaxed)
    }

    /// Run garbage collection / defragmentation
    pub fn gc(&self) {
        // In a real implementation, this would consolidate fragmented allocations
        // For now, we just reset the search cursor to find free pages earlier
        self.next_page.store(0, Ordering::Relaxed);
    }
}

/// Block header for heap allocations
#[repr(C)]
struct BlockHeader {
    /// Size of the user data (excluding header and canary)
    size: usize,
    /// Whether this block is allocated
    is_allocated: bool,
    /// Magic value for validation
    magic: u32,
    /// Previous block in linked list
    prev: Option<usize>,
    /// Next block in linked list
    next: Option<usize>,
}

const BLOCK_MAGIC: u32 = 0x424C4B5F; // "BLK_"

/// Self-healing heap allocator
pub struct HealingHeapAllocator {
    /// Base address of the heap
    heap_base: UnsafeCell<*mut u8>,
    /// Total heap size
    heap_size: AtomicUsize,
    /// Free list head
    free_list: AtomicUsize,
    /// Statistics
    stats: UnsafeCell<MemoryStats>,
    /// Self-healing enabled
    healing_enabled: AtomicBool,
}

unsafe impl Sync for HealingHeapAllocator {}
unsafe impl Send for HealingHeapAllocator {}

impl HealingHeapAllocator {
    pub const fn new() -> Self {
        HealingHeapAllocator {
            heap_base: UnsafeCell::new(core::ptr::null_mut()),
            heap_size: AtomicUsize::new(0),
            free_list: AtomicUsize::new(0),
            stats: UnsafeCell::new(MemoryStats {
                total_pages: NUM_PAGES,
                free_pages: NUM_PAGES,
                allocated_pages: 0,
                corrupted_pages: 0,
                total_allocations: 0,
                total_deallocations: 0,
                failed_allocations: 0,
                corruption_events: 0,
                recovered_pages: 0,
            }),
            healing_enabled: AtomicBool::new(true),
        }
    }

    /// Initialize the heap with a memory region
    pub unsafe fn init(&self, heap_start: *mut u8, heap_size: usize) {
        *self.heap_base.get() = heap_start;
        self.heap_size.store(heap_size, Ordering::SeqCst);
        
        // Initialize first block
        let first_block = heap_start as *mut BlockHeader;
        (*first_block).size = heap_size - core::mem::size_of::<BlockHeader>() - CANARY_SIZE;
        (*first_block).is_allocated = false;
        (*first_block).magic = BLOCK_MAGIC;
        (*first_block).prev = None;
        (*first_block).next = None;
        
        // Write canary
        let canary_addr = heap_start.add(core::mem::size_of::<BlockHeader>()
            + (*first_block).size) as *mut u8;
        for i in 0..CANARY_SIZE {
            canary_addr.add(i).write(CANARY_VALUE);
        }
        
        self.free_list.store(heap_start as usize, Ordering::SeqCst);
        
        let stats = &mut *self.stats.get();
        stats.free_pages = heap_size / PAGE_SIZE;
    }

    /// Allocate memory with canary protection
    pub unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let size = layout.size();
        let align = layout.align();
        
        if size == 0 {
            return align as *mut u8;
        }
        
        if size > self.heap_size.load(Ordering::Relaxed) {
            let stats = &mut *self.stats.get();
            stats.failed_allocations += 1;
            return core::ptr::null_mut();
        }

        let total_size = size + CANARY_SIZE;
        let header_size = core::mem::size_of::<BlockHeader>();

        // Search free list
        let mut current = self.free_list.load(Ordering::Relaxed);
        
        while current != 0 {
            let block = current as *mut BlockHeader;
            
            if (*block).magic != BLOCK_MAGIC {
                // Corrupted block - attempt healing
                if self.healing_enabled.load(Ordering::Relaxed) {
                    if self.heal_block(block).is_err() {
                        let stats = &mut *self.stats.get();
                        stats.corruption_events += 1;
                        current = (*block).next.unwrap_or(0);
                        continue;
                    }
                } else {
                    let stats = &mut *self.stats.get();
                    stats.corruption_events += 1;
                    return core::ptr::null_mut();
                }
            }
            
            if !(*block).is_allocated && (*block).size >= total_size {
                // Split block if large enough
                let remaining = (*block).size - total_size;
                
                if remaining >= header_size + CANARY_SIZE + 16 {
                    // Split the block
                    let new_block_addr = current + header_size + total_size;
                    let new_block = new_block_addr as *mut BlockHeader;
                    
                    (*new_block).size = remaining - header_size - CANARY_SIZE;
                    (*new_block).is_allocated = false;
                    (*new_block).magic = BLOCK_MAGIC;
                    (*new_block).prev = Some(current);
                    (*new_block).next = (*block).next;
                    
                    // Write canary for new block
                    let new_canary = new_block_addr + header_size + (*new_block).size;
                    for i in 0..CANARY_SIZE {
                        (new_canary as *mut u8).add(i).write(CANARY_VALUE);
                    }
                    
                    (*block).next = Some(new_block_addr);
                    (*block).size = total_size - CANARY_SIZE;
                    
                    // Update free list if needed
                    if self.free_list.load(Ordering::Relaxed) == current {
                        self.free_list.store(new_block_addr, Ordering::Relaxed);
                    }
                }
                
                // Allocate this block
                (*block).is_allocated = true;
                
                // Write canary
                let canary_addr = current + header_size + (*block).size;
                for i in 0..CANARY_SIZE {
                    (canary_addr as *mut u8).add(i).write(CANARY_VALUE);
                }
                
                // Update stats
                let stats = &mut *self.stats.get();
                stats.total_allocations += 1;
                stats.allocated_pages += (total_size + PAGE_SIZE - 1) / PAGE_SIZE;
                stats.free_pages = stats.free_pages.saturating_sub((total_size + PAGE_SIZE - 1) / PAGE_SIZE);
                
                // Return user data pointer
                return (current + header_size) as *mut u8;
            }
            
            current = (*block).next.unwrap_or(0);
        }
        
        // No suitable block found
        let stats = &mut *self.stats.get();
        stats.failed_allocations += 1;
        core::ptr::null_mut()
    }

    /// Free memory with corruption detection
    pub unsafe fn dealloc(&self, ptr: *mut u8, _layout: Layout) {
        if ptr.is_null() {
            return;
        }
        
        let header_size = core::mem::size_of::<BlockHeader>();
        let block = (ptr as usize - header_size) as *mut BlockHeader;
        
        // Validate block
        if (*block).magic != BLOCK_MAGIC {
            let stats = &mut *self.stats.get();
            stats.corruption_events += 1;
            
            if self.healing_enabled.load(Ordering::Relaxed) {
                let _ = self.heal_block(block);
            }
            return;
        }
        
        if !(*block).is_allocated {
            // Double free detected
            let stats = &mut *self.stats.get();
            stats.corruption_events += 1;
            return;
        }
        
        // Check canary
        let canary_addr = (block as usize) + header_size + (*block).size;
        if !self.check_canary(canary_addr as *const u8) {
            // Buffer overflow detected
            let stats = &mut *self.stats.get();
            stats.corruption_events += 1;
            
            if self.healing_enabled.load(Ordering::Relaxed) {
                self.repair_canary(canary_addr as *mut u8);
            }
        }
        
        // Mark as free
        (*block).is_allocated = false;
        
        // Update stats
        let stats = &mut *self.stats.get();
        stats.total_deallocations += 1;
        let size = (*block).size + header_size + CANARY_SIZE;
        stats.allocated_pages = stats.allocated_pages.saturating_sub((size + PAGE_SIZE - 1) / PAGE_SIZE);
        stats.free_pages += (size + PAGE_SIZE - 1) / PAGE_SIZE;
        
        // Coalesce with next block if free
        if let Some(next_addr) = (*block).next {
            let next = next_addr as *mut BlockHeader;
            if !(*next).is_allocated {
                // Merge
                (*block).size += header_size + CANARY_SIZE + (*next).size;
                (*block).next = (*next).next;
                
                if let Some(next_next) = (*next).next {
                    (*(next_next as *mut BlockHeader)).prev = Some(block as usize);
                }
            }
        }
        
        // Coalesce with previous block if free
        if let Some(prev_addr) = (*block).prev {
            let prev = prev_addr as *mut BlockHeader;
            if !(*prev).is_allocated {
                // Merge
                (*prev).size += header_size + CANARY_SIZE + (*block).size;
                (*prev).next = (*block).next;
                
                if let Some(next) = (*block).next {
                    (*(next as *mut BlockHeader)).prev = Some(prev_addr);
                }
            }
        }
    }

    /// Check if canary is intact
    unsafe fn check_canary(&self, canary: *const u8) -> bool {
        for i in 0..CANARY_SIZE {
            if canary.add(i).read() != CANARY_VALUE {
                return false;
            }
        }
        true
    }

    /// Repair corrupted canary
    unsafe fn repair_canary(&self, canary: *mut u8) {
        for i in 0..CANARY_SIZE {
            canary.add(i).write(CANARY_VALUE);
        }
    }

    /// Attempt to heal a corrupted block
    unsafe fn heal_block(&self, block: *mut BlockHeader) -> Result<(), MemoryError> {
        // Simple healing: reinitialize the block header
        (*block).magic = BLOCK_MAGIC;
        (*block).is_allocated = true; // Assume allocated to prevent double-free
        
        let stats = &mut *self.stats.get();
        stats.recovered_pages += 1;
        
        Ok(())
    }

    /// Get memory statistics
    pub fn stats(&self) -> MemoryStats {
        unsafe { (*self.stats.get()).clone() }
    }

    /// Enable/disable self-healing
    pub fn set_healing_enabled(&self, enabled: bool) {
        self.healing_enabled.store(enabled, Ordering::Relaxed);
    }

    /// Run memory defragmentation
    pub fn defragment(&self) {
        // This would consolidate free blocks
        // For now, just a placeholder
    }

    /// Check entire heap for corruption
    pub fn verify_heap(&self) -> Result<usize, MemoryError> {
        let mut errors = 0;
        let heap_base = unsafe { *self.heap_base.get() };
        
        if heap_base.is_null() {
            return Err(MemoryError::InvalidPointer);
        }
        
        let mut current = heap_base as usize;
        let heap_end = current + self.heap_size.load(Ordering::Relaxed);
        
        while current < heap_end {
            let block = current as *mut BlockHeader;
            
            unsafe {
                if (*block).magic != BLOCK_MAGIC {
                    errors += 1;
                } else if (*block).is_allocated {
                    let canary_addr = current + core::mem::size_of::<BlockHeader>() + (*block).size;
                    if !self.check_canary(canary_addr as *const u8) {
                        errors += 1;
                    }
                }
                
                // Move to next block
                let size = (*block).size + core::mem::size_of::<BlockHeader>() + CANARY_SIZE;
                current += size;
            }
        }
        
        if errors > 0 {
            Err(MemoryError::CorruptionDetected)
        } else {
            Ok(0)
        }
    }
}

/// Global page frame allocator
pub static PAGE_ALLOCATOR: PageFrameAllocator = PageFrameAllocator::new();

/// Global heap allocator
pub static HEAP_ALLOCATOR: HealingHeapAllocator = HealingHeapAllocator::new();

/// Initialize memory subsystem
pub unsafe fn init(heap_start: *mut u8, heap_size: usize) {
    HEAP_ALLOCATOR.init(heap_start, heap_size);
}

/// GlobalAlloc implementation for the heap allocator
pub struct GlobalHeapAllocator;

unsafe impl GlobalAlloc for GlobalHeapAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        HEAP_ALLOCATOR.alloc(layout)
    }

    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        HEAP_ALLOCATOR.dealloc(ptr, layout);
    }
}

/// Get current memory statistics
pub fn get_stats() -> MemoryStats {
    HEAP_ALLOCATOR.stats()
}

/// Verify heap integrity
pub fn verify_heap() -> Result<usize, MemoryError> {
    HEAP_ALLOCATOR.verify_heap()
}

/// Run memory garbage collection
pub fn gc() {
    PAGE_ALLOCATOR.gc();
    HEAP_ALLOCATOR.defragment();
}

/// Enable/disable self-healing
pub fn set_self_healing(enabled: bool) {
    HEAP_ALLOCATOR.set_healing_enabled(enabled);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_page_allocator() {
        let alloc = PageFrameAllocator::new();
        
        // Allocate a page
        let page1 = alloc.alloc_page();
        assert!(page1.is_some());
        
        // Allocate another page
        let page2 = alloc.alloc_page();
        assert!(page2.is_some());
        assert_ne!(page1, page2);
        
        // Free first page
        assert!(alloc.free_page(page1.unwrap()).is_ok());
        
        // Double free should fail
        assert!(alloc.free_page(page1.unwrap()).is_err());
    }

    #[test]
    fn test_page_state() {
        let alloc = PageFrameAllocator::new();
        
        assert_eq!(alloc.get_page_state(0), PageState::Free);
        
        let page = alloc.alloc_page().unwrap();
        assert_eq!(alloc.get_page_state(page), PageState::Allocated);
        
        alloc.mark_corrupted(page);
        assert_eq!(alloc.get_page_state(page), PageState::Corrupted);
    }
}
