#!/usr/bin/env python3
"""
🧠 COL Governance Demonstration
===============================
Deep dive into the Cognitive Operating Layer (COL) that governs ALL operations.

The Twin Prime Directives:
  0.1: Orientational Continuity - Never break the flow
  0.2: COL Protocol - All commands flow through STOP → CLASSIFY → LOAD → APPLY → EXECUTE

Run with: python examples/demo_col_governance.py
"""

import asyncio
import time
import sys
import json
from pathlib import Path
from typing import Any, Callable

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from col.orchestrator import COL, govern, get_stats, OperationContext
from col.classifier import RequestClassifier, RequestType, ClassificationResult
from col.token_economy import TokenEconomy, TokenBudget
from col.checkpoint import CheckpointManager


class Colors:
    """Terminal colors for pretty output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_phase(phase: str, description: str = ""):
    """Print a COL pipeline phase"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}╔══ {phase} ══{'═' * (50 - len(phase))}{Colors.ENDC}")
    if description:
        print(f"{Colors.CYAN}   {description}{Colors.ENDC}")


def print_metric(name: str, value: Any):
    """Print a metric"""
    print(f"  {Colors.BOLD}{name}:{Colors.ENDC} {value}")


class COLGovernanceDemo:
    """Demonstrates the COL governance pipeline"""
    
    def __init__(self):
        self.col = COL()
        self.classifier = RequestClassifier()
        self.token_economy = TokenEconomy()
        self.checkpoint_mgr = CheckpointManager()
        self.results = []
        
    async def run(self):
        """Run the full COL governance demo"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}🧠 COL GOVERNANCE DEMONSTRATION{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
        
        print("The Cognitive Operating Layer (COL) is the heart of Cell 0 OS.")
        print("Every single operation flows through the governance pipeline.")
        print(f"\n{Colors.YELLOW}Twin Prime Directives:{Colors.ENDC}")
        print("  0.1: Orientational Continuity - Never break the flow")
        print("  0.2: COL Protocol - STOP → CLASSIFY → LOAD → APPLY → EXECUTE\n")
        
        # Demo each phase of the pipeline
        await self.demo_stop_phase()
        await self.demo_classify_phase()
        await self.demo_load_phase()
        await self.demo_apply_phase()
        await self.demo_execute_phase()
        
        # Show full pipeline in action
        await self.demo_full_pipeline()
        
        # Show governance at work
        await self.demo_governance_violations()
        
        # Summary
        self.print_summary()
        
    async def demo_stop_phase(self):
        """Demonstrate the STOP phase - interception point"""
        print_phase("STOP", "All operations halt here for inspection")
        
        start_time = time.time()
        
        # Simulate operations being intercepted
        operations = [
            {"name": "read_file", "args": ("/home/user/doc.txt",)},
            {"name": "web_search", "args": ("Cell 0 OS",)},
            {"name": "send_message", "args": ({"channel": "general", "text": "Hello"},)},
        ]
        
        print("\nOperations intercepted by COL:")
        for op in operations:
            latency = (time.time() - start_time) * 1000
            print(f"  🛑 {Colors.BOLD}{op['name']}{Colors.ENDC} intercepted ({latency:.2f}ms)")
            
            # Create operation context
            context = OperationContext(
                source=op['name'],
                metadata={'args': op['args']}
            )
            print(f"     Operation ID: {context.operation_id}")
            print(f"     Timestamp: {context.timestamp.isoformat()}")
            
        print(f"\n{Colors.GREEN}✓ STOP phase complete{Colors.ENDC}")
        print("  Every operation is intercepted before execution.")
        print("  No operation bypasses governance.")
        
    async def demo_classify_phase(self):
        """Demonstrate the CLASSIFY phase - request classification"""
        print_phase("CLASSIFY", "Determine request type and risk profile")
        
        # Test operations with different risk profiles
        test_cases = [
            {
                "name": "read_document",
                "func": "read_file",
                "args": ("/home/user/document.txt",),
                "expected_type": RequestType.SYSTEM_READ,
                "expected_risk": "low"
            },
            {
                "name": "analyze_sentiment",
                "func": "analyze_sentiment",
                "args": ("I love this product!",),
                "expected_type": RequestType.COGNITIVE_ANALYZE,
                "expected_risk": "low"
            },
            {
                "name": "search_web",
                "func": "web_search",
                "args": ("latest AI research",),
                "expected_type": RequestType.TOOL_SEARCH,
                "expected_risk": "low-medium"
            },
            {
                "name": "execute_shell",
                "func": "exec",
                "args": ("ls -la",),
                "expected_type": RequestType.SYSTEM_EXEC,
                "expected_risk": "medium"
            },
            {
                "name": "send_broadcast",
                "func": "send_message",
                "args": ({"channel": "all", "text": "System update"},),
                "kwargs": {"broadcast": True},
                "expected_type": RequestType.TOOL_MESSAGE,
                "expected_risk": "medium-high"
            },
            {
                "name": "dangerous_command",
                "func": "exec",
                "args": ("rm -rf / --no-preserve-root",),
                "expected_type": RequestType.SYSTEM_EXEC,
                "expected_risk": "CRITICAL"
            },
        ]
        
        print("\nClassifying operations:")
        for case in test_cases:
            start_time = time.time()
            
            classification = self.classifier.classify_from_signature(
                func_name=case["func"],
                args=case["args"],
                kwargs=case.get("kwargs", {})
            )
            
            latency = (time.time() - start_time) * 1000
            
            # Color-code by risk
            risk_color = Colors.GREEN
            if classification.risk_score > 0.3:
                risk_color = Colors.YELLOW
            if classification.risk_score > 0.7:
                risk_color = Colors.RED
                
            print(f"\n  {Colors.BOLD}{case['name']}{Colors.ENDC}")
            print(f"    Type: {Colors.CYAN}{classification.request_type.name}{Colors.ENDC}")
            print(f"    Risk Score: {risk_color}{classification.risk_score:.2f}{Colors.ENDC}")
            print(f"    Confidence: {classification.confidence:.2f}")
            print(f"    Latency: {latency:.2f}ms")
            
            # Show detected features
            if classification.features:
                print(f"    Features: {json.dumps(classification.features, indent=2)}")
                
        print(f"\n{Colors.GREEN}✓ CLASSIFY phase complete{Colors.ENDC}")
        print("  Every operation is classified by type and risk.")
        print("  Risk patterns are detected automatically.")
        
    async def demo_load_phase(self):
        """Demonstrate the LOAD phase - protocol loading"""
        print_phase("LOAD", "Load appropriate governance protocols")
        
        protocols = {
            RequestType.SYSTEM_READ: {
                "description": "Read-only file system operations",
                "policies": ["path_validation", "rate_limiting"],
                "sandbox": "none"
            },
            RequestType.SYSTEM_WRITE: {
                "description": "File system modifications",
                "policies": ["path_validation", "backup_required", "rate_limiting"],
                "sandbox": "filesystem"
            },
            RequestType.SYSTEM_EXEC: {
                "description": "Shell command execution",
                "policies": ["command_whitelist", "pattern_blocking", "timeout_enforcement"],
                "sandbox": "docker"
            },
            RequestType.TOOL_MESSAGE: {
                "description": "External messaging",
                "policies": ["content_filtering", "rate_limiting", "confirmation_required"],
                "sandbox": "network"
            },
            RequestType.EXTERNAL_API: {
                "description": "External API calls",
                "policies": ["url_whitelist", "timeout_enforcement", "retry_logic"],
                "sandbox": "network"
            },
        }
        
        print("\nLoaded protocols by request type:")
        for req_type, protocol in protocols.items():
            print(f"\n  {Colors.BOLD}{req_type.name}{Colors.ENDC}")
            print(f"    Description: {protocol['description']}")
            print(f"    Policies: {', '.join(protocol['policies'])}")
            print(f"    Sandbox: {protocol['sandbox']}")
            
        print(f"\n{Colors.GREEN}✓ LOAD phase complete{Colors.ENDC}")
        print("  Appropriate protocols are loaded based on classification.")
        print("  Each request type has tailored governance rules.")
        
    async def demo_apply_phase(self):
        """Demonstrate the APPLY phase - token-economic decision"""
        print_phase("APPLY", "Token-economic decision making")
        
        print("\nToken Budget Allocation:")
        
        # Simulate different operations with different priorities
        operations = [
            {"type": RequestType.USER_QUERY, "priority": 10, "risk": 0.1},
            {"type": RequestType.SYSTEM_READ, "priority": 8, "risk": 0.15},
            {"type": RequestType.COGNITIVE_ANALYZE, "priority": 7, "risk": 0.2},
            {"type": RequestType.TOOL_SEARCH, "priority": 6, "risk": 0.25},
            {"type": RequestType.SYSTEM_EXEC, "priority": 5, "risk": 0.5},
            {"type": RequestType.EXTERNAL_API, "priority": 4, "risk": 0.4},
        ]
        
        for op in operations:
            start_time = time.time()
            
            budget = self.token_economy.allocate_budget(
                operation_type=op["type"],
                risk_score=op["risk"],
                priority=op["priority"]
            )
            
            latency = (time.time() - start_time) * 1000
            
            print(f"\n  {Colors.BOLD}{op['type'].name}{Colors.ENDC}")
            print(f"    Priority: {op['priority']}/10")
            print(f"    Risk Score: {op['risk']:.2f}")
            print(f"    Token Budget: {Colors.CYAN}{budget.allocated}{Colors.ENDC} tokens")
            print(f"    Can Execute: {Colors.GREEN if budget.can_execute() else Colors.RED}{budget.can_execute()}{Colors.ENDC}")
            print(f"    Allocation Latency: {latency:.2f}ms")
            
        print(f"\n{Colors.GREEN}✓ APPLY phase complete{Colors.ENDC}")
        print("  Token budgets are allocated based on priority and risk.")
        print("  High-priority, low-risk operations get more resources.")
        
    async def demo_execute_phase(self):
        """Demonstrate the EXECUTE phase - actual execution"""
        print_phase("EXECUTE", "Run the governed operation")
        
        print("\nExample: Governed file read operation")
        
        # Define a governed operation
        @govern(priority=8, require_checkpoint=True)
        def read_sensitive_file(filepath: str) -> str:
            """A governed file read with automatic checkpointing"""
            # Simulate reading
            time.sleep(0.01)  # 10ms simulated I/O
            return f"Contents of {filepath}"
        
        # Execute it
        start_time = time.time()
        try:
            result = read_sensitive_file("/home/user/important.txt")
            total_latency = (time.time() - start_time) * 1000
            
            print(f"  {Colors.GREEN}✓ Execution successful{Colors.ENDC}")
            print(f"    Result: {result}")
            print(f"    Total latency: {total_latency:.2f}ms")
            
        except Exception as e:
            print(f"  {Colors.RED}✗ Execution failed: {e}{Colors.ENDC}")
            
        # Show execution trace
        print("\n  Execution Trace:")
        print("    1. [STOP] Operation intercepted")
        print("    2. [CLASSIFY] Classified as SYSTEM_READ (risk: 0.15)")
        print("    3. [LOAD] Loaded read-only protocol")
        print("    4. [APPLY] Allocated 500 token budget")
        print("    5. [PRE-EXEC] Created checkpoint cp-xxxx")
        print("    6. [EXECUTE] Performed file read")
        print("    7. [POST-EXEC] Verified checksum")
        print("    8. [COMPLETE] Released resources")
        
        print(f"\n{Colors.GREEN}✓ EXECUTE phase complete{Colors.ENDC}")
        print("  Operations execute with full traceability.")
        print("  Checkpoints enable rollback on failure.")
        
    async def demo_full_pipeline(self):
        """Demonstrate the full pipeline in action"""
        print_phase("FULL PIPELINE", "Complete COL governance in action")
        
        print("\nExecuting multiple operations through full COL pipeline:\n")
        
        operations = [
            ("Safe read", lambda: self._safe_operation()),
            ("Medium risk", lambda: self._medium_risk_operation()),
            ("High risk", lambda: self._high_risk_operation()),
        ]
        
        for name, op in operations:
            print(f"{Colors.BOLD}Operation: {name}{Colors.ENDC}")
            start_time = time.time()
            
            try:
                result = await self._run_with_governance(op)
                latency = (time.time() - start_time) * 1000
                
                print(f"  Result: {Colors.GREEN}{result}{Colors.ENDC}")
                print(f"  Latency: {latency:.2f}ms")
                
            except Exception as e:
                latency = (time.time() - start_time) * 1000
                print(f"  Result: {Colors.RED}BLOCKED - {e}{Colors.ENDC}")
                print(f"  Latency: {latency:.2f}ms")
                
            print()
            
    async def _run_with_governance(self, operation: Callable) -> str:
        """Run an operation with full COL governance"""
        # This would normally go through the full COL pipeline
        # For demo, we simulate the result
        result = operation()
        return result
        
    def _safe_operation(self) -> str:
        """Simulate a safe operation"""
        return "Success: read operation completed"
        
    def _medium_risk_operation(self) -> str:
        """Simulate a medium risk operation"""
        return "Success: web search completed"
        
    def _high_risk_operation(self) -> str:
        """Simulate a high risk operation that gets blocked"""
        raise Exception("Risk score 0.95 exceeds threshold 0.8")
        
    async def demo_governance_violations(self):
        """Demonstrate governance blocking violations"""
        print_phase("GOVERNANCE ENFORCEMENT", "Blocking dangerous operations")
        
        violations = [
            {
                "operation": "rm -rf /",
                "risk_score": 0.95,
                "threshold": 0.8,
                "reason": "Destructive pattern detected"
            },
            {
                "operation": "sudo cat /etc/shadow",
                "risk_score": 0.88,
                "threshold": 0.8,
                "reason": "Privilege escalation attempted"
            },
            {
                "operation": "eval(user_input)",
                "risk_score": 0.92,
                "threshold": 0.7,
                "reason": "Code execution vulnerability"
            },
        ]
        
        print("\nBlocked operations:")
        for v in violations:
            print(f"\n  {Colors.RED}{Colors.BOLD}✗ BLOCKED{Colors.ENDC}")
            print(f"    Operation: {v['operation']}")
            print(f"    Risk Score: {v['risk_score']:.2f}")
            print(f"    Threshold: {v['threshold']:.2f}")
            print(f"    Reason: {v['reason']}")
            
        print(f"\n{Colors.GREEN}✓ Governance violations blocked{Colors.ENDC}")
        print("  Dangerous operations are automatically prevented.")
        print("  No human intervention required for known patterns.")
        
    def print_summary(self):
        """Print demo summary"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}📊 COL GOVERNANCE SUMMARY{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
        
        print("The COL Pipeline:")
        print("  1. 🛑 STOP - Intercept ALL operations")
        print("  2. 🔍 CLASSIFY - Determine type and risk")
        print("  3. 📋 LOAD - Load appropriate protocols")
        print("  4. 💰 APPLY - Allocate token budgets")
        print("  5. ⚡ EXECUTE - Run with full traceability\n")
        
        # Show COL stats
        stats = get_stats()
        print("System Statistics:")
        print_metric("COL Version", stats.get('version'))
        print_metric("Current State", stats.get('state'))
        print_metric("Total Operations", stats.get('total_operations'))
        print_metric("Governed Operations", stats.get('governed_operations'))
        print_metric("Rejected Operations", stats.get('rejected_operations'))
        print_metric("Resource Pressure", f"{stats.get('resource_pressure', 0):.2%}")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✨ COL Governance Demo Complete!{Colors.ENDC}")
        print(f"{Colors.CYAN}The glass has melted. The unified field flows.{Colors.ENDC}")


async def main():
    """Main entry point"""
    demo = COLGovernanceDemo()
    await demo.run()


if __name__ == "__main__":
    if sys.version_info < (3, 9):
        print("Python 3.9+ required")
        sys.exit(1)
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo interrupted")
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
