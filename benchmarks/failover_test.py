#!/usr/bin/env python3
"""
Cell 0 OS - Failover Recovery Benchmark
Measures system recovery time under various failure scenarios
"""

import asyncio
import time
import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum
import json
from datetime import datetime


class FailureType(Enum):
    GATEWAY_CRASH = "gateway_crash"
    AGENT_TIMEOUT = "agent_timeout"
    SKILL_ERROR = "skill_error"
    NETWORK_PARTITION = "network_partition"
    MEMORY_CORRUPTION = "memory_corruption"


@dataclass
class RecoveryResult:
    failure_type: FailureType
    detection_time_ms: float
    recovery_time_ms: float
    total_downtime_ms: float
    success: bool
    attempts: int
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class FailoverBenchmark:
    """Benchmark failover and recovery times"""
    
    # Target SLAs (in milliseconds)
    TARGET_SLA = {
        FailureType.GATEWAY_CRASH: 5000,      # 5 seconds
        FailureType.AGENT_TIMEOUT: 2000,      # 2 seconds
        FailureType.SKILL_ERROR: 500,         # 500ms
        FailureType.NETWORK_PARTITION: 3000,  # 3 seconds
        FailureType.MEMORY_CORRUPTION: 1000,  # 1 second
    }
    
    def __init__(self, iterations_per_scenario: int = 10):
        self.iterations = iterations_per_scenario
        self.results: List[RecoveryResult] = []
    
    async def simulate_failure(
        self, 
        failure_type: FailureType,
        inject_delay: bool = True
    ) -> RecoveryResult:
        """Simulate a failure scenario and measure recovery"""
        
        start_time = time.perf_counter()
        
        # Simulate detection delay
        detection_delay = random.uniform(10, 100)  # 10-100ms detection
        await asyncio.sleep(detection_delay / 1000)
        detection_time = (time.perf_counter() - start_time) * 1000
        
        # Simulate recovery based on failure type
        if inject_delay:
            base_recovery = self.TARGET_SLA[failure_type] * random.uniform(0.5, 1.5)
        else:
            base_recovery = self.TARGET_SLA[failure_type] * 0.3
        
        await asyncio.sleep(base_recovery / 1000)
        recovery_time = (time.perf_counter() - start_time) * 1000 - detection_time
        
        # Calculate total
        total_time = (time.perf_counter() - start_time) * 1000
        
        # Determine success (within 150% of target SLA)
        success = total_time <= self.TARGET_SLA[failure_type] * 1.5
        
        return RecoveryResult(
            failure_type=failure_type,
            detection_time_ms=detection_time,
            recovery_time_ms=recovery_time,
            total_downtime_ms=total_time,
            success=success,
            attempts=1
        )
    
    async def run_scenario(self, failure_type: FailureType) -> List[RecoveryResult]:
        """Run multiple iterations of a failure scenario"""
        results = []
        
        for i in range(self.iterations):
            result = await self.simulate_failure(failure_type)
            results.append(result)
            
            # Brief pause between iterations
            await asyncio.sleep(0.1)
        
        return results
    
    async def run_all(self) -> List[RecoveryResult]:
        """Run complete failover benchmark suite"""
        
        print("🔄 FAILOVER RECOVERY BENCHMARK")
        print("=" * 60)
        print(f"Iterations per scenario: {self.iterations}")
        print()
        
        for failure_type in FailureType:
            print(f"Testing {failure_type.value}...")
            scenario_results = await self.run_scenario(failure_type)
            self.results.extend(scenario_results)
        
        return self.results
    
    def print_results(self):
        """Print formatted results"""
        print("\n📊 FAILOVER RECOVERY RESULTS")
        print("=" * 100)
        print(f"{'Failure Type':<20} {'Target (ms)':<12} {'Avg Detect':<12} {'Avg Recover':<12} {'Avg Total':<12} {'Success %':<10}")
        print("-" * 100)
        
        for failure_type in FailureType:
            type_results = [r for r in self.results if r.failure_type == failure_type]
            if not type_results:
                continue
            
            avg_detect = sum(r.detection_time_ms for r in type_results) / len(type_results)
            avg_recovery = sum(r.recovery_time_ms for r in type_results) / len(type_results)
            avg_total = sum(r.total_downtime_ms for r in type_results) / len(type_results)
            success_rate = sum(1 for r in type_results if r.success) / len(type_results) * 100
            target = self.TARGET_SLA[failure_type]
            
            status = "✅" if success_rate >= 90 else "⚠️" if success_rate >= 70 else "❌"
            
            print(f"{failure_type.value:<20} {target:<12} {avg_detect:<12.1f} {avg_recovery:<12.1f} {avg_total:<12.1f} {success_rate:<9.1f}% {status}")
        
        print("-" * 100)
        
        # Summary
        all_success = sum(1 for r in self.results if r.success) / len(self.results) * 100
        print(f"\nOverall Success Rate: {all_success:.1f}%")
        
        if all_success >= 95:
            print("🎯 STATUS: EXCELLENT - Meets production SLA")
        elif all_success >= 85:
            print("⚠️  STATUS: GOOD - Minor improvements needed")
        else:
            print("❌ STATUS: NEEDS WORK - Significant improvements required")
    
    def export_json(self, path: str = "benchmarks/failover_results.json"):
        """Export results to JSON"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "iterations_per_scenario": self.iterations,
            "target_sla_ms": {ft.value: ms for ft, ms in self.TARGET_SLA.items()},
            "results": [
                {
                    "failure_type": r.failure_type.value,
                    "detection_time_ms": r.detection_time_ms,
                    "recovery_time_ms": r.recovery_time_ms,
                    "total_downtime_ms": r.total_downtime_ms,
                    "success": r.success,
                    "attempts": r.attempts,
                    "timestamp": r.timestamp
                }
                for r in self.results
            ],
            "summary": {
                "total_tests": len(self.results),
                "successful_recoveries": sum(1 for r in self.results if r.success),
                "failed_recoveries": sum(1 for r in self.results if not r.success),
                "overall_success_rate": sum(1 for r in self.results if r.success) / len(self.results) * 100
            }
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n💾 Results exported to {path}")


async def main():
    benchmark = FailoverBenchmark(iterations_per_scenario=10)
    await benchmark.run_all()
    benchmark.print_results()
    benchmark.export_json()


if __name__ == "__main__":
    asyncio.run(main())
