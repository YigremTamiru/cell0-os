"""
Example usage of the Multi-Agent Routing System

Cell 0 OS - Multi-Agent Routing System
"""
import asyncio
from engine.agents.agent_registry import AgentCapability
from service.agent_coordinator import AgentCoordinator, CoordinatorConfig


async def main():
    """
    Example: Building a multi-agent content processing system
    """
    
    # Initialize the coordinator
    config = CoordinatorConfig(
        heartbeat_interval_seconds=30.0,
        health_check_interval_seconds=10.0,
        stale_agent_timeout_seconds=120.0
    )
    
    async with AgentCoordinator(config) as coordinator:
        print("🚀 Cell 0 OS Multi-Agent System Started")
        print("=" * 50)
        
        # Register specialized agents
        
        # 1. Web Scraper Agent
        scraper = await coordinator.register_agent(
            agent_id="web-scraper",
            agent_type="data-collection",
            capabilities=[
                AgentCapability(name="web_scraping", version="2.0.0", priority=10),
                AgentCapability(name="url_parsing", version="1.0.0")
            ],
            metadata={"region": "us-east", "max_rate": "100/min"},
            tags={"production", "data-collection"}
        )
        print(f"✅ Registered: {scraper.agent_id} ({scraper.agent_type})")
        
        # 2. Content Analyzer Agent
        analyzer = await coordinator.register_agent(
            agent_id="content-analyzer",
            agent_type="nlp",
            capabilities=[
                AgentCapability(name="sentiment_analysis", version="3.0.0", priority=8),
                AgentCapability(name="entity_extraction", version="2.5.0", priority=9),
                AgentCapability(name="summarization", version="1.5.0", priority=7)
            ],
            metadata={"model": "gpt-4", "languages": ["en", "es", "fr"]},
            tags={"production", "nlp"}
        )
        print(f"✅ Registered: {analyzer.agent_id} ({analyzer.agent_type})")
        
        # 3. Document Formatter Agent
        formatter = await coordinator.register_agent(
            agent_id="doc-formatter",
            agent_type="output",
            capabilities=[
                AgentCapability(name="markdown_formatting", version="1.0.0"),
                AgentCapability(name="pdf_generation", version="2.0.0", priority=5),
                AgentCapability(name="html_rendering", version="1.5.0")
            ],
            tags={"production", "output"}
        )
        print(f"✅ Registered: {formatter.agent_id} ({formatter.agent_type})")
        
        # 4. Quality Assurance Agent
        qa_agent = await coordinator.register_agent(
            agent_id="qa-validator",
            agent_type="validation",
            capabilities=[
                AgentCapability(name="content_validation", version="1.0.0", priority=10),
                AgentCapability(name="fact_checking", version="2.0.0")
            ],
            tags={"production", "qa"}
        )
        print(f"✅ Registered: {qa_agent.agent_id} ({qa_agent.agent_type})")
        
        print("\n" + "=" * 50)
        print("📊 System Statistics:")
        
        # Show system stats
        stats = coordinator.get_stats()
        registry_stats = stats["registry"]
        print(f"  Total Agents: {registry_stats['total_agents']}")
        print(f"  Healthy Agents: {registry_stats['healthy_agents']}")
        print(f"  By Type: {registry_stats['by_type']}")
        print(f"  By Capability: {registry_stats['by_capability']}")
        
        # Show health
        health = coordinator.get_health()
        print(f"\n  System Health: {health['status'].upper()}")
        print(f"  Healthy Ratio: {health['healthy_ratio']:.1%}")
        
        print("\n" + "=" * 50)
        print("🔍 Agent Discovery Examples:")
        
        # Find agents by capability
        nlp_agents = coordinator.find_agents(capability_name="sentiment_analysis")
        print(f"\n  Agents with 'sentiment_analysis': {[a.agent_id for a in nlp_agents]}")
        
        # Find by type
        data_agents = coordinator.find_agents(agent_type="data-collection")
        print(f"  Agents of type 'data-collection': {[a.agent_id for a in data_agents]}")
        
        # Find by tag
        prod_agents = coordinator.find_agents(tag="production")
        print(f"  Agents with 'production' tag: {[a.agent_id for a in prod_agents]}")
        
        print("\n" + "=" * 50)
        print("📡 Message Routing Examples:")
        
        # Simulate sending messages
        
        # 1. Route to specific capability
        result = await coordinator.route_by_capability(
            source="user",
            content={"url": "https://example.com/article"},
            capability_name="web_scraping"
        )
        print(f"\n  Route to 'web_scraping': {result.success}")
        print(f"    Target: {result.target_agents}")
        print(f"    Time: {result.routing_time_ms:.2f}ms")
        
        # 2. Route to agent with multiple capabilities
        result = await coordinator.route_by_capability(
            source="user",
            content={"text": "This product is amazing!", "analysis_type": "sentiment"},
            capability_name="sentiment_analysis"
        )
        print(f"\n  Route to 'sentiment_analysis': {result.success}")
        print(f"    Target: {result.target_agents}")
        
        # 3. Broadcast to all agents
        results = await coordinator.broadcast(
            source="system",
            content={"type": "config_update", "version": "2.1.0"}
        )
        print(f"\n  Broadcast to all: {len([r for r in results.values() if r])} agents reached")
        
        print("\n" + "=" * 50)
        print("🔔 Pub/Sub Examples:")
        
        # Subscribe agents to topics
        sub1 = coordinator.subscribe("content-analyzer", "new-articles")
        sub2 = coordinator.subscribe("doc-formatter", "analysis-complete")
        sub3 = coordinator.subscribe("qa-validator", "new-articles")  # Same topic, multiple subscribers
        
        print(f"\n  Subscriptions created: {sub1[:8]}..., {sub2[:8]}..., {sub3[:8]}...")
        
        # Publish to topic
        delivered = await coordinator.publish(
            source="web-scraper",
            topic="new-articles",
            payload={"article_id": "12345", "title": "AI Breakthrough", "url": "..."}
        )
        print(f"  Published to 'new-articles': {len([d for d in delivered.values() if d])} subscribers")
        
        print("\n" + "=" * 50)
        print("👥 Group Management:")
        
        # Create groups
        coordinator.join_group("web-scraper", "data-pipeline")
        coordinator.join_group("content-analyzer", "data-pipeline")
        coordinator.join_group("doc-formatter", "data-pipeline")
        coordinator.join_group("qa-validator", "data-pipeline")
        
        members = coordinator.mesh.get_group_members("data-pipeline")
        print(f"\n  Group 'data-pipeline' members: {list(members)}")
        
        # Multicast to group
        results = await coordinator.mesh.multicast(
            source="coordinator",
            groups=["data-pipeline"],
            payload={"command": "prepare_for_batch", "batch_id": "batch-001"}
        )
        print(f"  Multicast to 'data-pipeline': {len([r for r in results.values() if r])} delivered")
        
        print("\n" + "=" * 50)
        print("📈 Load Balancing Demo:")
        
        # Register multiple workers
        for i in range(3):
            await coordinator.register_agent(
                agent_id=f"worker-{i}",
                agent_type="compute",
                capabilities=[AgentCapability(name="batch_processing", priority=5)],
                tags={"workers"}
            )
            # Simulate different loads
            await coordinator.send_heartbeat(f"worker-{i}", load_score=0.2 * i)
        
        # Route multiple tasks - should distribute based on load
        print("\n  Routing 5 tasks with LEAST_LOADED strategy:")
        for i in range(5):
            result = await coordinator.route_by_capability(
                source="scheduler",
                content={"task_id": f"task-{i}", "data": "..."},
                capability_name="batch_processing",
                strategy=__import__('engine.agents.agent_router', fromlist=['RoutingStrategy']).RoutingStrategy.LEAST_LOADED
            )
            print(f"    Task {i} -> {result.target_agents[0] if result.target_agents else 'None'}")
        
        print("\n" + "=" * 50)
        print("💓 Heartbeat & Health Monitoring:")
        
        # Send heartbeats
        for agent_id in ["web-scraper", "content-analyzer", "doc-formatter"]:
            await coordinator.send_heartbeat(agent_id, load_score=0.3)
        
        # Check health
        health = coordinator.get_health()
        print(f"\n  Health Status: {health['status']}")
        print(f"  Agents: {health['agents']['healthy']}/{health['agents']['total']} healthy")
        
        print("\n" + "=" * 50)
        print("✨ System Running Successfully!")
        print("=" * 50)


if __name__ == "__main__":
    # Check if running with proper imports
    try:
        asyncio.run(main())
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure to run from the project root directory")
