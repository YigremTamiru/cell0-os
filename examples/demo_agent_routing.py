#!/usr/bin/env python3
"""
👥 Multi-Agent Routing Demonstration
====================================
Intelligent agent selection and mesh communication.

Features demonstrated:
- Capability-based agent registration
- Multiple routing strategies (least-loaded, priority, round-robin, sticky)
- Agent mesh pub/sub communication
- Group multicast
- Health monitoring and heartbeats
- Dynamic load balancing

Run with: python examples/demo_agent_routing.py
"""

import asyncio
import time
import sys
import json
import random
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any
from enum import Enum, auto

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


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


class RoutingStrategy(Enum):
    """Strategies for routing messages to agents"""
    ROUND_ROBIN = auto()
    LEAST_LOADED = auto()
    CAPABILITY_PRIORITY = auto()
    RANDOM = auto()
    STICKY = auto()
    BROADCAST = auto()


@dataclass
class AgentCapability:
    """Agent capability definition"""
    name: str
    version: str
    priority: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentInfo:
    """Agent registration information"""
    agent_id: str
    agent_type: str
    capabilities: List[AgentCapability]
    load_score: float = 0.0  # 0.0 - 1.0
    healthy: bool = True
    last_heartbeat: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    
    def has_capability(self, name: str) -> bool:
        """Check if agent has a capability"""
        return any(c.name == name for c in self.capabilities)
    
    def get_capability_priority(self, name: str) -> int:
        """Get priority for a capability"""
        for cap in self.capabilities:
            if cap.name == name:
                return cap.priority
        return 0


class AgentRoutingDemo:
    """Demonstrates multi-agent routing and mesh communication"""
    
    def __init__(self):
        self.agents: Dict[str, AgentInfo] = {}
        self.groups: Dict[str, Set[str]] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # topic -> agent_ids
        self.sticky_sessions: Dict[str, str] = {}  # sender -> agent_id
        self.round_robin_counters: Dict[str, int] = {}
        self.message_history: List[Dict] = []
        
    async def run(self):
        """Run the agent routing demo"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}👥 MULTI-AGENT ROUTING DEMONSTRATION{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
        
        print("Cell 0 OS provides intelligent agent routing and mesh communication.")
        print("Agents self-organize based on capabilities and load.\n")
        
        # Demo agent registration
        await self.demo_agent_registration()
        
        # Demo capability discovery
        await self.demo_capability_discovery()
        
        # Demo routing strategies
        await self.demo_routing_strategies()
        
        # Demo agent mesh
        await self.demo_agent_mesh()
        
        # Demo health monitoring
        await self.demo_health_monitoring()
        
        # Summary
        self.print_summary()
        
    async def demo_agent_registration(self):
        """Demonstrate agent registration"""
        print(f"{Colors.BOLD}{Colors.HEADER}╔══ Agent Registration ═══════════════════════════════{Colors.ENDC}\n")
        
        agents_config = [
            {
                "id": "analyzer-alpha",
                "type": "nlp",
                "capabilities": [
                    AgentCapability("sentiment_analysis", "2.0.0", 10),
                    AgentCapability("entity_extraction", "1.5.0", 8),
                    AgentCapability("text_classification", "1.0.0", 7),
                ],
                "load_score": 0.3,
                "tags": {"production", "nlp", "v2"}
            },
            {
                "id": "analyzer-beta",
                "type": "nlp",
                "capabilities": [
                    AgentCapability("sentiment_analysis", "2.1.0", 9),
                    AgentCapability("summarization", "1.5.0", 8),
                    AgentCapability("translation", "1.0.0", 6),
                ],
                "load_score": 0.6,
                "tags": {"production", "nlp", "v2.1"}
            },
            {
                "id": "scraper-gamma",
                "type": "data",
                "capabilities": [
                    AgentCapability("web_scraping", "3.0.0", 10),
                    AgentCapability("data_extraction", "2.0.0", 8),
                    AgentCapability("pdf_parsing", "1.5.0", 7),
                ],
                "load_score": 0.2,
                "tags": {"production", "data", "scraper"}
            },
            {
                "id": "scraper-delta",
                "type": "data",
                "capabilities": [
                    AgentCapability("web_scraping", "2.5.0", 9),
                    AgentCapability("api_integration", "1.0.0", 7),
                ],
                "load_score": 0.4,
                "tags": {"production", "data", "api"}
            },
            {
                "id": "formatter-epsilon",
                "type": "output",
                "capabilities": [
                    AgentCapability("markdown_format", "1.0.0", 8),
                    AgentCapability("pdf_generation", "2.0.0", 7),
                    AgentCapability("html_rendering", "1.5.0", 6),
                ],
                "load_score": 0.1,
                "tags": {"production", "output"}
            },
            {
                "id": "validator-zeta",
                "type": "qa",
                "capabilities": [
                    AgentCapability("content_validation", "1.0.0", 10),
                    AgentCapability("fact_checking", "2.0.0", 9),
                    AgentCapability("quality_score", "1.5.0", 8),
                ],
                "load_score": 0.25,
                "tags": {"production", "qa"}
            },
        ]
        
        print(f"Registering {len(agents_config)} specialized agents:\n")
        
        for config in agents_config:
            agent = AgentInfo(
                agent_id=config["id"],
                agent_type=config["type"],
                capabilities=config["capabilities"],
                load_score=config["load_score"],
                healthy=True,
                last_heartbeat=time.time(),
                tags=config["tags"]
            )
            self.agents[agent.agent_id] = agent
            
            print(f"  {Colors.GREEN}✓{Colors.ENDC} {Colors.BOLD}{agent.agent_id}{Colors.ENDC}")
            print(f"    Type: {agent.agent_type}")
            print(f"    Capabilities: {', '.join(c.name for c in agent.capabilities)}")
            print(f"    Load: {agent.load_score:.0%}")
            print(f"    Tags: {', '.join(agent.tags)}")
            print()
            
        print(f"{Colors.GREEN}✓ All agents registered successfully{Colors.ENDC}")
        
    async def demo_capability_discovery(self):
        """Demonstrate capability-based discovery"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}╔══ Capability Discovery ═════════════════════════════{Colors.ENDC}\n")
        
        # Find by capability
        capabilities_to_find = [
            "sentiment_analysis",
            "web_scraping",
            "content_validation",
            "pdf_generation",
        ]
        
        for cap_name in capabilities_to_find:
            start_time = time.time()
            
            matching = [
                agent for agent in self.agents.values()
                if agent.has_capability(cap_name)
            ]
            
            latency = (time.time() - start_time) * 1000
            
            print(f"{Colors.BOLD}Capability: {cap_name}{Colors.ENDC}")
            print(f"  Matching agents: {len(matching)}")
            print(f"  Discovery latency: {latency:.2f}ms")
            
            for agent in matching:
                priority = agent.get_capability_priority(cap_name)
                print(f"    • {agent.agent_id} (priority: {priority})")
            print()
            
        # Find by type
        print(f"{Colors.BOLD}By Agent Type:{Colors.ENDC}")
        types = set(agent.agent_type for agent in self.agents.values())
        for agent_type in types:
            matching = [a for a in self.agents.values() if a.agent_type == agent_type]
            print(f"  {agent_type}: {len(matching)} agents")
            for agent in matching:
                print(f"    • {agent.agent_id}")
                
        # Find by tag
        print(f"\n{Colors.BOLD}By Tag:{Colors.ENDC}")
        all_tags = set()
        for agent in self.agents.values():
            all_tags.update(agent.tags)
            
        for tag in sorted(all_tags):
            matching = [a for a in self.agents.values() if tag in a.tags]
            print(f"  #{tag}: {len(matching)} agents")
            
    async def demo_routing_strategies(self):
        """Demonstrate different routing strategies"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}╔══ Routing Strategies ═══════════════════════════════{Colors.ENDC}\n")
        
        print("Available strategies:\n")
        
        strategies = [
            (RoutingStrategy.LEAST_LOADED, "Routes to agent with lowest load"),
            (RoutingStrategy.CAPABILITY_PRIORITY, "Routes by capability priority"),
            (RoutingStrategy.ROUND_ROBIN, "Distributes evenly across agents"),
            (RoutingStrategy.RANDOM, "Random selection"),
            (RoutingStrategy.STICKY, "Maintains session affinity"),
            (RoutingStrategy.BROADCAST, "Sends to all matching agents"),
        ]
        
        for strategy, description in strategies:
            print(f"  {Colors.CYAN}{strategy.name}{Colors.ENDC}")
            print(f"    {description}")
        
        # Demonstrate each strategy
        print(f"\n{Colors.BOLD}Strategy Demonstration:{Colors.ENDC}")
        print("(Routing 5 tasks to sentiment_analysis agents)\n")
        
        # Get sentiment analysis agents
        sentiment_agents = [
            a for a in self.agents.values()
            if a.has_capability("sentiment_analysis")
        ]
        
        for strategy, _ in strategies:
            print(f"{Colors.BOLD}{strategy.name}:{Colors.ENDC}")
            
            for i in range(5):
                start_time = time.time()
                selected = self._route_with_strategy(
                    sentiment_agents, strategy, "sentiment_analysis", f"task-{i}"
                )
                latency = (time.time() - start_time) * 1000
                
                print(f"  Task {i+1} → {Colors.GREEN}{selected}{Colors.ENDC} ({latency:.2f}ms)")
                
            print()
            
    def _route_with_strategy(
        self,
        agents: List[AgentInfo],
        strategy: RoutingStrategy,
        capability: str,
        task_id: str
    ) -> str:
        """Route using specified strategy"""
        if not agents:
            return "none"
            
        healthy = [a for a in agents if a.healthy]
        if not healthy:
            return "none"
            
        if strategy == RoutingStrategy.BROADCAST:
            return ", ".join(a.agent_id for a in healthy)
            
        if strategy == RoutingStrategy.LEAST_LOADED:
            return min(healthy, key=lambda a: a.load_score).agent_id
            
        if strategy == RoutingStrategy.CAPABILITY_PRIORITY:
            return max(healthy, key=lambda a: a.get_capability_priority(capability)).agent_id
            
        if strategy == RoutingStrategy.RANDOM:
            return random.choice(healthy).agent_id
            
        if strategy == RoutingStrategy.STICKY:
            if task_id not in self.sticky_sessions:
                self.sticky_sessions[task_id] = random.choice(healthy).agent_id
            return self.sticky_sessions[task_id]
            
        if strategy == RoutingStrategy.ROUND_ROBIN:
            key = capability
            counter = self.round_robin_counters.get(key, 0)
            self.round_robin_counters[key] = (counter + 1) % len(healthy)
            return healthy[counter % len(healthy)].agent_id
            
        return healthy[0].agent_id
        
    async def demo_agent_mesh(self):
        """Demonstrate agent mesh communication"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}╔══ Agent Mesh Communication ═════════════════════════{Colors.ENDC}\n")
        
        print("Agents can communicate via:\n")
        print("  • Pub/Sub (topics)")
        print("  • Groups (multicast)")
        print("  • Direct messaging")
        print("  • Broadcast (all agents)\n")
        
        # Create groups
        print(f"{Colors.BOLD}Creating Agent Groups:{Colors.ENDC}")
        
        groups = {
            "nlp-pipeline": ["analyzer-alpha", "analyzer-beta", "formatter-epsilon"],
            "data-pipeline": ["scraper-gamma", "scraper-delta", "analyzer-alpha"],
            "qa-pipeline": ["validator-zeta", "analyzer-alpha", "analyzer-beta"],
        }
        
        for group_name, members in groups.items():
            self.groups[group_name] = set(members)
            print(f"  {Colors.CYAN}{group_name}{Colors.ENDC}: {', '.join(members)}")
            
        # Pub/Sub
        print(f"\n{Colors.BOLD}Pub/Sub Subscriptions:{Colors.ENDC}")
        
        subscriptions = [
            ("analyzer-alpha", "new-documents"),
            ("analyzer-beta", "new-documents"),
            ("scraper-gamma", "urls-discovered"),
            ("formatter-epsilon", "analysis-complete"),
            ("validator-zeta", "content-ready"),
        ]
        
        for agent_id, topic in subscriptions:
            if topic not in self.subscriptions:
                self.subscriptions[topic] = set()
            self.subscriptions[topic].add(agent_id)
            
        for topic, agents in self.subscriptions.items():
            print(f"  {Colors.CYAN}{topic}{Colors.ENDC}: {len(agents)} subscribers")
            for agent_id in agents:
                print(f"    • {agent_id}")
                
        # Simulate pub/sub
        print(f"\n{Colors.BOLD}Publishing Events:{Colors.ENDC}")
        
        events = [
            ("urls-discovered", {"urls": ["https://example.com/1", "https://example.com/2"]}),
            ("new-documents", {"document_id": "doc-123", "content": "Sample text..."}),
            ("analysis-complete", {"document_id": "doc-123", "sentiment": "positive"}),
        ]
        
        for topic, payload in events:
            start_time = time.time()
            
            subscribers = self.subscriptions.get(topic, set())
            latency = (time.time() - start_time) * 1000
            
            print(f"\n  Publish to '{topic}':")
            print(f"    Payload: {json.dumps(payload)[:50]}...")
            print(f"    Delivered to: {len(subscribers)} agents ({latency:.2f}ms)")
            for agent_id in subscribers:
                print(f"      → {agent_id}")
                
        # Multicast
        print(f"\n{Colors.BOLD}Group Multicast:{Colors.ENDC}")
        
        multicast_msg = {"command": "process_batch", "batch_id": "batch-001"}
        
        for group_name in ["nlp-pipeline", "data-pipeline"]:
            start_time = time.time()
            members = self.groups.get(group_name, set())
            latency = (time.time() - start_time) * 1000
            
            print(f"\n  Multicast to '{group_name}':")
            print(f"    Message: {multicast_msg}")
            print(f"    Delivered to: {len(members)} agents ({latency:.2f}ms)")
            for agent_id in members:
                print(f"      → {agent_id}")
                
    async def demo_health_monitoring(self):
        """Demonstrate health monitoring and heartbeats"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}╔══ Health Monitoring ════════════════════════════════{Colors.ENDC}\n")
        
        print("Health monitoring features:\n")
        print("  • Heartbeat every 30 seconds")
        print("  • Load score reporting")
        print("  • Automatic failure detection")
        print("  • Unhealthy agent exclusion from routing\n")
        
        # Simulate heartbeats
        print(f"{Colors.BOLD}Simulating Heartbeats:{Colors.ENDC}\n")
        
        for agent in self.agents.values():
            # Simulate heartbeat with current load
            agent.last_heartbeat = time.time()
            
            status = Colors.GREEN + "HEALTHY" if agent.healthy else Colors.RED + "UNHEALTHY"
            load_color = Colors.GREEN if agent.load_score < 0.5 else (
                Colors.YELLOW if agent.load_score < 0.8 else Colors.RED
            )
            
            print(f"  {agent.agent_id}:")
            print(f"    Status: {status}{Colors.ENDC}")
            print(f"    Load: {load_color}{agent.load_score:.0%}{Colors.ENDC}")
            print(f"    Last heartbeat: just now")
            print()
            
        # Show system health
        print(f"{Colors.BOLD}System Health:{Colors.ENDC}")
        
        total = len(self.agents)
        healthy = sum(1 for a in self.agents.values() if a.healthy)
        avg_load = sum(a.load_score for a in self.agents.values()) / total
        
        print(f"  Total agents: {total}")
        print(f"  Healthy: {Colors.GREEN}{healthy}{Colors.ENDC}")
        print(f"  Unhealthy: {Colors.RED}{total - healthy}{Colors.ENDC}")
        print(f"  Average load: {avg_load:.1%}")
        print(f"  Health ratio: {healthy/total:.1%}")
        
        # Simulate agent failure
        print(f"\n{Colors.BOLD}Simulating Agent Failure:{Colors.ENDC}")
        
        failed_agent = "analyzer-beta"
        self.agents[failed_agent].healthy = False
        self.agents[failed_agent].load_score = 1.0
        
        print(f"  {Colors.RED}✗ {failed_agent} has failed{Colors.ENDC}")
        print(f"  {Colors.GREEN}✓ Automatically excluded from routing{Colors.ENDC}")
        
        # Show updated routing
        sentiment_agents = [
            a for a in self.agents.values()
            if a.has_capability("sentiment_analysis") and a.healthy
        ]
        
        print(f"\n  Remaining sentiment analysis agents:")
        for agent in sentiment_agents:
            print(f"    • {agent.agent_id} (load: {agent.load_score:.0%})")
            
    def print_summary(self):
        """Print demo summary"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}📊 AGENT ROUTING SUMMARY{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
        
        print("Key Features:")
        print("  ✓ Capability-based agent registration")
        print("  ✓ 6 routing strategies (least-loaded, priority, round-robin, etc.)")
        print("  ✓ Pub/Sub messaging between agents")
        print("  ✓ Group multicast for pipeline coordination")
        print("  ✓ Automatic health monitoring")
        print("  ✓ Dynamic load balancing")
        print("  ✓ Graceful handling of agent failures\n")
        
        print("System Statistics:")
        print(f"  Registered agents: {len(self.agents)}")
        print(f"  Agent types: {len(set(a.agent_type for a in self.agents.values()))}")
        
        all_caps = set()
        for agent in self.agents.values():
            for cap in agent.capabilities:
                all_caps.add(cap.name)
        print(f"  Unique capabilities: {len(all_caps)}")
        
        print(f"  Groups: {len(self.groups)}")
        print(f"  Pub/Sub topics: {len(self.subscriptions)}")
        
        healthy = sum(1 for a in self.agents.values() if a.healthy)
        print(f"  Healthy agents: {healthy}/{len(self.agents)}")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✨ Agent Routing Demo Complete!{Colors.ENDC}")
        print(f"{Colors.CYAN}Agents self-organize for optimal task distribution.{Colors.ENDC}")


async def main():
    """Main entry point"""
    demo = AgentRoutingDemo()
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
