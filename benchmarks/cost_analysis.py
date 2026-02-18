#!/usr/bin/env python3
"""
Cell 0 OS - Cost Analysis Benchmark
Tracks token usage and estimates operational costs per task
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class ModelTier(Enum):
    FAST = "fast"           # GPT-4o-mini, Claude Haiku
    BALANCED = "balanced"   # GPT-4o, Claude Sonnet
    POWER = "power"         # GPT-4 Turbo, Claude Opus


@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int = field(init=False)
    
    def __post_init__(self):
        self.total_tokens = self.prompt_tokens + self.completion_tokens


@dataclass
class CostBreakdown:
    model_tier: ModelTier
    operation: str
    tokens: TokenUsage
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    latency_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class CostAnalyzer:
    """Analyze and track costs per COL operation"""
    
    # Pricing per 1M tokens (USD) - Updated 2024
    PRICING = {
        ModelTier.FAST: {
            "input": 0.15,      # $0.15 per 1M input tokens
            "output": 0.60,     # $0.60 per 1M output tokens
        },
        ModelTier.BALANCED: {
            "input": 2.50,      # $2.50 per 1M input tokens
            "output": 10.00,    # $10.00 per 1M output tokens
        },
        ModelTier.POWER: {
            "input": 10.00,     # $10.00 per 1M input tokens
            "output": 30.00,    # $30.00 per 1M output tokens
        }
    }
    
    def __init__(self):
        self.records: List[CostBreakdown] = []
    
    def calculate_cost(
        self, 
        model_tier: ModelTier,
        prompt_tokens: int,
        completion_tokens: int,
        operation: str = "unknown",
        latency_ms: float = 0
    ) -> CostBreakdown:
        """Calculate cost for a single operation"""
        
        tokens = TokenUsage(prompt_tokens, completion_tokens)
        pricing = self.PRICING[model_tier]
        
        # Calculate costs (per 1M tokens)
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        breakdown = CostBreakdown(
            model_tier=model_tier,
            operation=operation,
            tokens=tokens,
            input_cost_usd=input_cost,
            output_cost_usd=output_cost,
            total_cost_usd=total_cost,
            latency_ms=latency_ms
        )
        
        self.records.append(breakdown)
        return breakdown
    
    def simulate_task(
        self,
        name: str,
        tier: ModelTier,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float
    ) -> CostBreakdown:
        """Simulate a task and record its cost"""
        return self.calculate_cost(tier, prompt_tokens, completion_tokens, name, latency_ms)
    
    def run_benchmark(self):
        """Run cost analysis for typical COL tasks"""
        
        print("💰 COST ANALYSIS BENCHMARK")
        print("=" * 60)
        print("Simulating typical Cell 0 OS workloads...")
        print()
        
        # Task classification (fast tier)
        self.simulate_task(
            "col_classify_simple",
            ModelTier.FAST,
            prompt_tokens=500,
            completion_tokens=50,
            latency_ms=150
        )
        
        self.simulate_task(
            "col_classify_complex",
            ModelTier.BALANCED,
            prompt_tokens=2000,
            completion_tokens=200,
            latency_ms=800
        )
        
        # Agent operations (balanced tier)
        self.simulate_task(
            "agent_spawn",
            ModelTier.BALANCED,
            prompt_tokens=1500,
            completion_tokens=300,
            latency_ms=1200
        )
        
        self.simulate_task(
            "agent_heartbeat",
            ModelTier.FAST,
            prompt_tokens=800,
            completion_tokens=100,
            latency_ms=200
        )
        
        # Skill execution (varies by complexity)
        self.simulate_task(
            "skill_read_file",
            ModelTier.FAST,
            prompt_tokens=1000,
            completion_tokens=500,
            latency_ms=400
        )
        
        self.simulate_task(
            "skill_web_search",
            ModelTier.BALANCED,
            prompt_tokens=2000,
            completion_tokens=800,
            latency_ms=2500
        )
        
        self.simulate_task(
            "skill_code_review",
            ModelTier.POWER,
            prompt_tokens=5000,
            completion_tokens=1500,
            latency_ms=5000
        )
        
        # Memory operations (fast tier)
        self.simulate_task(
            "memory_read",
            ModelTier.FAST,
            prompt_tokens=300,
            completion_tokens=200,
            latency_ms=100
        )
        
        self.simulate_task(
            "memory_write",
            ModelTier.FAST,
            prompt_tokens=400,
            completion_tokens=100,
            latency_ms=120
        )
        
        # Complex reasoning (power tier)
        self.simulate_task(
            "col_reasoning",
            ModelTier.POWER,
            prompt_tokens=8000,
            completion_tokens=2000,
            latency_ms=8000
        )
        
        return self.records
    
    def print_summary(self):
        """Print cost summary"""
        print("\n📊 COST BREAKDOWN BY OPERATION")
        print("=" * 90)
        print(f"{'Operation':<25} {'Tier':<10} {'Tokens':<10} {'Cost (USD)':<15} {'$/1K tasks':<15}")
        print("-" * 90)
        
        for record in self.records:
            cost_per_1k = record.total_cost_usd * 1000
            print(f"{record.operation:<25} {record.model_tier.value:<10} "
                  f"{record.tokens.total_tokens:<10} ${record.total_cost_usd:<14.6f} "
                  f"${cost_per_1k:<14.2f}")
        
        print("-" * 90)
        
        # Totals by tier
        print("\n📈 COST BY TIER")
        print("-" * 60)
        for tier in ModelTier:
            tier_records = [r for r in self.records if r.model_tier == tier]
            if tier_records:
                total_cost = sum(r.total_cost_usd for r in tier_records)
                total_tokens = sum(r.tokens.total_tokens for r in tier_records)
                avg_cost = total_cost / len(tier_records)
                print(f"{tier.value:<15} Tasks: {len(tier_records):<5} "
                      f"Tokens: {total_tokens:<8} Total: ${total_cost:.6f} "
                      f"Avg: ${avg_cost:.6f}")
        
        # Grand totals
        total_cost = sum(r.total_cost_usd for r in self.records)
        total_tokens = sum(r.tokens.total_tokens for r in self.records)
        
        print("-" * 60)
        print(f"{'TOTAL':<15} Tasks: {len(self.records):<5} "
              f"Tokens: {total_tokens:<8} Cost: ${total_cost:.6f}")
        
        # Projected monthly costs
        print("\n📅 PROJECTED MONTHLY COSTS")
        print("-" * 60)
        
        # Assuming 1000 tasks per day
        daily_tasks = 1000
        daily_cost = total_cost * (daily_tasks / len(self.records))
        monthly_cost = daily_cost * 30
        
        print(f"Light usage (100 tasks/day):   ${daily_cost * 0.1 * 30:.2f}/month")
        print(f"Medium usage (1K tasks/day):   ${monthly_cost:.2f}/month")
        print(f"Heavy usage (10K tasks/day):   ${monthly_cost * 10:.2f}/month")
        print(f"Enterprise (100K tasks/day):   ${monthly_cost * 100:.2f}/month")
        
        print("\n💡 COST OPTIMIZATION TIPS:")
        print("   • Use FAST tier for classification and simple tasks")
        print("   • Cache common operations to reduce token usage")
        print("   • Batch operations when possible")
        print("   • Use streaming for large responses")
    
    def export_json(self, path: str = "benchmarks/cost_results.json"):
        """Export results to JSON"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "pricing_per_1m_tokens": {
                tier.value: pricing for tier, pricing in self.PRICING.items()
            },
            "records": [
                {
                    "operation": r.operation,
                    "model_tier": r.model_tier.value,
                    "tokens": {
                        "prompt": r.tokens.prompt_tokens,
                        "completion": r.tokens.completion_tokens,
                        "total": r.tokens.total_tokens
                    },
                    "cost_usd": {
                        "input": r.input_cost_usd,
                        "output": r.output_cost_usd,
                        "total": r.total_cost_usd
                    },
                    "latency_ms": r.latency_ms,
                    "timestamp": r.timestamp
                }
                for r in self.records
            ],
            "summary": {
                "total_tasks": len(self.records),
                "total_tokens": sum(r.tokens.total_tokens for r in self.records),
                "total_cost_usd": sum(r.total_cost_usd for r in self.records),
                "avg_cost_per_task_usd": sum(r.total_cost_usd for r in self.records) / len(self.records)
            }
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n💾 Results exported to {path}")


def main():
    analyzer = CostAnalyzer()
    analyzer.run_benchmark()
    analyzer.print_summary()
    analyzer.export_json()


if __name__ == "__main__":
    main()
