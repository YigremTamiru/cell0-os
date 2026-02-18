#!/usr/bin/env python3
"""
Cell 0 Distributed Mode & Gateway Performance Profiler
Tests distributed capabilities and profiles gateway performance
"""

import time
import json
import os
import sys
import socket
import subprocess
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
import statistics

@dataclass
class GatewayMetrics:
    timestamp: str
    cpu_percent: float
    memory_mb: float
    rss_mb: float
    
@dataclass
class DistributedTestResult:
    test_name: str
    success: bool
    latency_ms: float
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class GatewayProfiler:
    """Profiles gateway process performance using system tools"""
    
    def __init__(self):
        self.gateway_pid = self._find_gateway_pid()
        self.metrics = []
        
    def _find_gateway_pid(self) -> Optional[int]:
        """Find the gateway process PID"""
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'openclaw-gateway'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip().split('\n')[0])
        except:
            pass
        return None
    
    def _get_process_stats(self, pid: int) -> Dict[str, float]:
        """Get process stats using ps"""
        try:
            result = subprocess.run(
                ['ps', '-p', str(pid), '-o', '%cpu,rss,vsz', '-c'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    values = lines[1].split()
                    return {
                        'cpu': float(values[0]) if values[0].replace('.','').isdigit() else 0.0,
                        'rss_kb': float(values[1]) if values[1].isdigit() else 0.0,
                        'vsz_kb': float(values[2]) if values[2].isdigit() else 0.0
                    }
        except:
            pass
        return {'cpu': 0.0, 'rss_kb': 0.0, 'vsz_kb': 0.0}
    
    def collect_metrics(self, duration_sec: int = 5) -> List[GatewayMetrics]:
        """Collect gateway metrics over time"""
        if not self.gateway_pid:
            print("⚠️ Gateway process not found")
            return []
            
        print(f"📊 Profiling gateway (PID: {self.gateway_pid}) for {duration_sec}s...")
        
        for _ in range(duration_sec):
            stats = self._get_process_stats(self.gateway_pid)
            metrics = GatewayMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=stats['cpu'],
                memory_mb=stats['rss_kb'] / 1024,
                rss_mb=stats['rss_kb'] / 1024
            )
            self.metrics.append(metrics)
            print(f"  CPU: {metrics.cpu_percent:5.1f}% | MEM: {metrics.memory_mb:6.1f}MB")
            time.sleep(1)
            
        return self.metrics
    
    def analyze_metrics(self) -> Dict[str, Any]:
        """Analyze collected metrics"""
        if not self.metrics:
            return {}
            
        cpu_values = [m.cpu_percent for m in self.metrics]
        mem_values = [m.memory_mb for m in self.metrics]
        
        return {
            "cpu_mean": statistics.mean(cpu_values),
            "cpu_max": max(cpu_values),
            "cpu_min": min(cpu_values),
            "memory_mean_mb": statistics.mean(mem_values),
            "memory_max_mb": max(mem_values),
            "memory_min_mb": min(mem_values),
            "memory_stable": max(mem_values) - min(mem_values) < 50,
            "sample_count": len(self.metrics)
        }

class DistributedModeTester:
    """Tests distributed mode capabilities"""
    
    def __init__(self):
        self.gateway_host = "127.0.0.1"
        self.gateway_port = 18789
        self.results = []
        
    def test_local_connectivity(self) -> DistributedTestResult:
        """Test basic connectivity to local gateway"""
        start = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.gateway_host, self.gateway_port))
            sock.close()
            
            if result == 0:
                return DistributedTestResult(
                    test_name="local_connectivity",
                    success=True,
                    latency_ms=(time.time() - start) * 1000
                )
            else:
                return DistributedTestResult(
                    test_name="local_connectivity",
                    success=False,
                    latency_ms=(time.time() - start) * 1000,
                    error=f"Connection failed with code {result}"
                )
        except Exception as e:
            return DistributedTestResult(
                test_name="local_connectivity",
                success=False,
                latency_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    def test_gateway_api(self) -> DistributedTestResult:
        """Test gateway API responsiveness"""
        start = time.time()
        try:
            result = subprocess.run(
                ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 
                 f'http://{self.gateway_host}:{self.gateway_port}/api/v1/status'],
                capture_output=True, text=True, timeout=5
            )
            http_code = result.stdout.strip()
            
            if result.returncode == 0 and http_code in ['200', '404']:
                return DistributedTestResult(
                    test_name="gateway_api",
                    success=True,
                    latency_ms=(time.time() - start) * 1000,
                    error=None if http_code == '200' else f"HTTP {http_code}"
                )
            else:
                return DistributedTestResult(
                    test_name="gateway_api",
                    success=False,
                    latency_ms=(time.time() - start) * 1000,
                    error=f"HTTP {http_code}"
                )
        except Exception as e:
            return DistributedTestResult(
                test_name="gateway_api",
                success=False,
                latency_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    def test_tailscale_mode(self) -> DistributedTestResult:
        """Test if Tailscale distributed mode is available"""
        start = time.time()
        try:
            # Check if tailscale is installed
            result = subprocess.run(['which', 'tailscale'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                return DistributedTestResult(
                    test_name="tailscale_mode",
                    success=False,
                    latency_ms=(time.time() - start) * 1000,
                    error="Tailscale not installed"
                )
            
            # Check tailscale status
            result = subprocess.run(['tailscale', 'status'], 
                                  capture_output=True, text=True, timeout=5)
            
            return DistributedTestResult(
                test_name="tailscale_mode",
                success=result.returncode == 0,
                latency_ms=(time.time() - start) * 1000,
                error=None if result.returncode == 0 else result.stderr[:100]
            )
        except Exception as e:
            return DistributedTestResult(
                test_name="tailscale_mode",
                success=False,
                latency_ms=(time.time() - start) * 1000,
                error=str(e)[:100]
            )
    
    def test_network_latency(self) -> DistributedTestResult:
        """Test network latency to common services"""
        start = time.time()
        try:
            # Test DNS resolution
            socket.gethostbyname('api.moonshot.ai')
            return DistributedTestResult(
                test_name="network_latency",
                success=True,
                latency_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return DistributedTestResult(
                test_name="network_latency",
                success=False,
                latency_ms=(time.time() - start) * 1000,
                error=str(e)[:100]
            )
    
    def run_all_tests(self) -> List[DistributedTestResult]:
        """Run all distributed mode tests"""
        print("\n🔍 Distributed Mode Test Suite")
        print("=" * 60)
        
        tests = [
            self.test_local_connectivity,
            self.test_gateway_api,
            self.test_network_latency,
            self.test_tailscale_mode
        ]
        
        for test in tests:
            print(f"\n  Running {test.__name__}...")
            result = test()
            self.results.append(result)
            status = "✓ PASS" if result.success else "✗ FAIL"
            print(f"    {status} ({result.latency_ms:.1f}ms)")
            if result.error:
                print(f"    Note: {result.error}")
        
        return self.results

def analyze_bottlenecks(metrics: Dict[str, Any], distributed_results: List[DistributedTestResult]) -> List[Dict[str, Any]]:
    """Analyze and identify bottlenecks"""
    bottlenecks = []
    
    # Memory analysis
    if metrics.get('memory_mean_mb', 0) > 1000:
        bottlenecks.append({
            "severity": "HIGH",
            "component": "Memory",
            "issue": f"High memory usage: {metrics['memory_mean_mb']:.1f}MB average",
            "recommendation": "Consider enabling memory compression or increasing swap"
        })
    
    # CPU analysis
    if metrics.get('cpu_mean', 0) > 50:
        bottlenecks.append({
            "severity": "MEDIUM",
            "component": "CPU",
            "issue": f"High CPU usage: {metrics['cpu_mean']:.1f}% average",
            "recommendation": "Consider reducing concurrent agent limit or enabling request batching"
        })
    
    # Connectivity analysis
    for result in distributed_results:
        if not result.success:
            if result.test_name == "tailscale_mode":
                bottlenecks.append({
                    "severity": "LOW",
                    "component": "Distributed Mode",
                    "issue": "Tailscale not configured for distributed mode",
                    "recommendation": "Install and configure Tailscale for multi-node support"
                })
            elif result.test_name == "gateway_api":
                bottlenecks.append({
                    "severity": "LOW",
                    "component": "Gateway API",
                    "issue": "Gateway API endpoint not accessible (may be normal)",
                    "recommendation": "Check gateway configuration if API access needed"
                })
            elif result.test_name == "network_latency":
                bottlenecks.append({
                    "severity": "HIGH",
                    "component": "Network",
                    "issue": "DNS/network resolution issues",
                    "recommendation": "Check network connectivity and DNS configuration"
                })
    
    return bottlenecks

def main():
    print("=" * 70)
    print("CELL 0 DISTRIBUTED MODE & GATEWAY PERFORMANCE PROFILER")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)
    
    # Profile gateway
    profiler = GatewayProfiler()
    if profiler.gateway_pid:
        metrics_list = profiler.collect_metrics(duration_sec=5)
        analysis = profiler.analyze_metrics()
        
        print("\n📈 Gateway Performance Analysis")
        print("-" * 70)
        for key, value in analysis.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
    else:
        analysis = {}
        print("\n⚠️ Gateway process not running - skipping profiling")
    
    # Test distributed mode
    tester = DistributedModeTester()
    distributed_results = tester.run_all_tests()
    
    # Analyze bottlenecks
    bottlenecks = analyze_bottlenecks(analysis, distributed_results)
    
    print("\n" + "=" * 70)
    print("BOTTLENECK ANALYSIS")
    print("=" * 70)
    
    if bottlenecks:
        for b in sorted(bottlenecks, key=lambda x: {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}[x['severity']]):
            print(f"\n[{b['severity']}] {b['component']}")
            print(f"  Issue: {b['issue']}")
            print(f"  Fix: {b['recommendation']}")
    else:
        print("\n✓ No significant bottlenecks detected")
    
    # Generate optimization recommendations
    print("\n" + "=" * 70)
    print("OPTIMIZATION RECOMMENDATIONS")
    print("=" * 70)
    
    recommendations = []
    
    # Check current config
    if analysis.get('memory_max_mb', 0) > 500:
        recommendations.append({
            "priority": "HIGH",
            "action": "Enable log rotation",
            "details": "Current logs may be consuming significant memory/disk",
            "command": "logrotate -f /etc/logrotate.d/openclaw 2>/dev/null || echo 'Manual rotation needed'"
        })
    
    # Check distributed mode
    tailscale_test = next((r for r in distributed_results if r.test_name == "tailscale_mode"), None)
    if tailscale_test and not tailscale_test.success:
        recommendations.append({
            "priority": "MEDIUM",
            "action": "Enable distributed mode",
            "details": "Install Tailscale for multi-node cluster support",
            "command": "brew install tailscale && tailscale up"
        })
    
    # Check API optimization
    api_test = next((r for r in distributed_results if r.test_name == "gateway_api"), None)
    if api_test and not api_test.success:
        recommendations.append({
            "priority": "LOW",
            "action": "Configure API endpoints",
            "details": "Gateway API may need explicit configuration for external access",
            "config_change": "gateway.bind: '0.0.0.0' (currently loopback only)"
        })
    
    if recommendations:
        for rec in sorted(recommendations, key=lambda x: {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}[x['priority']]):
            print(f"\n[{rec['priority']}] {rec['action']}")
            print(f"  {rec['details']}")
            if 'command' in rec:
                print(f"  Run: {rec['command']}")
            if 'config_change' in rec:
                print(f"  Config: {rec['config_change']}")
    else:
        print("\n✓ System is well-optimized")
    
    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "gateway_metrics": analysis,
        "distributed_tests": [asdict(r) for r in distributed_results],
        "bottlenecks": bottlenecks,
        "recommendations": recommendations
    }
    
    report_file = f"/Users/yigremgetachewtamiru/.openclaw/workspace/benchmarks/distributed_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\n✓ Report saved to: {report_file}")

if __name__ == "__main__":
    main()
