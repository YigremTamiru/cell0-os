# Cell 0 Developer Tutorial

## Getting Started

This tutorial will guide you through building your first Cell 0 extension — a custom agent that can interact with the system.

### Prerequisites

- Cell 0 installed and running
- Python 3.10+
- Basic knowledge of async Python

## Tutorial 1: Your First Agent

### Step 1: Create Agent Structure

```bash
cd ~/cell0
mkdir -p extensions/my_first_agent
touch extensions/my_first_agent/__init__.py
touch extensions/my_first_agent/agent.py
```

### Step 2: Write the Agent

```python
# extensions/my_first_agent/agent.py
import asyncio
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class AgentContext:
    """Context passed to the agent on each interaction."""
    message: str
    user_id: str
    conversation_history: list
    tpv_profile: Dict[str, Any]

class MyFirstAgent:
    """
    A simple greeting agent that demonstrates Cell 0 agent structure.
    """
    
    def __init__(self):
        self.name = "Greeting Agent"
        self.version = "1.0.0"
        self.capabilities = ["greeting", "small_talk"]
        self.resonance_threshold = 0.7
    
    async def initialize(self) -> bool:
        """Called when the agent is first loaded."""
        print(f"[{self.name}] Initializing...")
        # Load models, connect to services, etc.
        return True
    
    async def handle_message(self, context: AgentContext) -> Dict[str, Any]:
        """
        Main entry point for agent interactions.
        
        Args:
            context: Contains message and metadata
            
        Returns:
            Response dictionary with content and metadata
        """
        message = context.message.lower()
        
        # Simple intent detection
        if "hello" in message or "hi" in message:
            response = self._generate_greeting(context)
        elif "how are you" in message:
            response = self._generate_status()
        else:
            response = self._generate_default()
        
        return {
            "content": response,
            "confidence": 0.9,
            "capabilities_used": ["greeting"],
            "metadata": {
                "agent_version": self.version,
                "processing_time_ms": 50
            }
        }
    
    def _generate_greeting(self, context: AgentContext) -> str:
        """Generate a personalized greeting."""
        name = context.tpv_profile.get("identity", {}).get("sovereign_name", "friend")
        return f"Hello, {name}! Welcome to Cell 0. How can I assist you today?"
    
    def _generate_status(self) -> str:
        """Generate status response."""
        return "I'm running smoothly on Cell 0's sovereign infrastructure. All systems operational!"
    
    def _generate_default(self) -> str:
        """Default response for unrecognized input."""
        return "I'm a simple greeting agent. Try saying 'hello' or asking how I'm doing!"
    
    async def shutdown(self):
        """Called when the agent is being unloaded."""
        print(f"[{self.name}] Shutting down...")

# Create instance
agent = MyFirstAgent()
```

### Step 3: Register with Cell 0

```python
# extensions/my_first_agent/__init__.py
from .agent import agent

__all__ = ["agent"]
```

Create a registration script:

```python
# scripts/register_agent.py
import sys
import asyncio
from pathlib import Path

# Add Cell 0 to path
sys.path.insert(0, str(Path.home() / 'cell0'))

from engine.mcic_bridge import MCICBridge
from extensions.my_first_agent import agent

async def register():
    bridge = MCICBridge()
    
    # Initialize agent
    success = await agent.initialize()
    if not success:
        print("Failed to initialize agent")
        return
    
    # Register with MCIC
    result = await bridge.register_agent(
        agent_id="greeting_agent_001",
        agent_instance=agent,
        capabilities=agent.capabilities
    )
    
    print(f"Agent registered: {result}")

if __name__ == "__main__":
    asyncio.run(register())
```

### Step 4: Test Your Agent

```bash
# Register the agent
python scripts/register_agent.py

# Test via API
curl -X POST http://localhost:18800/api/agents/greeting_agent_001/send \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

## Tutorial 2: Building a Custom Skill

Skills extend Cell 0's capabilities. Let's build a skill that summarizes web pages.

### Step 1: Create Skill Structure

```bash
mkdir -p skills/web_summarizer
touch skills/web_summarizer/__init__.py
touch skills/web_summarizer/skill.py
touch skills/web_summarizer/requirements.txt
```

### Step 2: Implement the Skill

```python
# skills/web_summarizer/skill.py
import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any
import html

class WebSummarizerSkill:
    """
    Skill to fetch and summarize web pages.
    """
    
    name = "web_summarizer"
    version = "1.0.0"
    description = "Fetches web pages and extracts key content"
    
    # Define capabilities this skill provides
    capabilities = {
        "fetch_url": {
            "description": "Fetch content from a URL",
            "parameters": {
                "url": "string - The URL to fetch",
                "max_length": "int - Maximum content length (default: 5000)"
            }
        },
        "extract_text": {
            "description": "Extract readable text from HTML",
            "parameters": {
                "html": "string - Raw HTML content"
            }
        },
        "summarize": {
            "description": "Create a brief summary of content",
            "parameters": {
                "text": "string - Text to summarize",
                "max_sentences": "int - Number of sentences (default: 3)"
            }
        }
    }
    
    def __init__(self):
        self.http_client = None
    
    async def initialize(self):
        """Initialize the skill."""
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Cell0-WebSummarizer/1.0"
            }
        )
        return True
    
    async def execute(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a capability.
        
        Args:
            capability: Name of the capability to execute
            params: Parameters for the capability
            
        Returns:
            Result dictionary
        """
        if capability == "fetch_url":
            return await self._fetch_url(params)
        elif capability == "extract_text":
            return await self._extract_text(params)
        elif capability == "summarize":
            return await self._summarize(params)
        else:
            return {"error": f"Unknown capability: {capability}"}
    
    async def _fetch_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch content from URL."""
        url = params.get("url")
        max_length = params.get("max_length", 5000)
        
        if not url:
            return {"error": "URL parameter required"}
        
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            content = response.text[:max_length]
            
            return {
                "success": True,
                "url": url,
                "content": content,
                "content_type": response.headers.get("content-type"),
                "size": len(response.content)
            }
        except Exception as e:
            return {"error": f"Failed to fetch URL: {str(e)}"}
    
    async def _extract_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract readable text from HTML."""
        html_content = params.get("html", "")
        
        if not html_content:
            return {"error": "HTML parameter required"}
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return {
                "success": True,
                "text": text,
                "title": soup.title.string if soup.title else None
            }
        except Exception as e:
            return {"error": f"Failed to extract text: {str(e)}"}
    
    async def _summarize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create simple extractive summary."""
        text = params.get("text", "")
        max_sentences = params.get("max_sentences", 3)
        
        if not text:
            return {"error": "Text parameter required"}
        
        # Simple sentence extraction (in production, use ML model)
        sentences = text.replace('!', '.').replace('?', '.').split('.')
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # Take first N sentences as summary
        summary_sentences = sentences[:max_sentences]
        summary = '. '.join(summary_sentences) + '.'
        
        return {
            "success": True,
            "summary": summary,
            "sentences_in": len(sentences),
            "sentences_out": len(summary_sentences)
        }
    
    async def shutdown(self):
        """Clean up resources."""
        if self.http_client:
            await self.http_client.aclose()

# Create instance
skill = WebSummarizerSkill()
```

### Step 3: Add Dependencies

```text
# skills/web_summarizer/requirements.txt
httpx>=0.25.0
beautifulsoup4>=4.12.0
```

### Step 4: Register and Test

```python
# scripts/test_web_summarizer.py
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / 'cell0'))

from skills.web_summarizer.skill import skill

async def test():
    await skill.initialize()
    
    # Test fetch capability
    result = await skill.execute("fetch_url", {
        "url": "https://example.com",
        "max_length": 2000
    })
    print("Fetch result:", result)
    
    # Test extract capability
    if result.get("success"):
        extract_result = await skill.execute("extract_text", {
            "html": result["content"]
        })
        print("Extract result:", extract_result)
        
        # Test summarize capability
        if extract_result.get("success"):
            summary_result = await skill.execute("summarize", {
                "text": extract_result["text"],
                "max_sentences": 2
            })
            print("Summary:", summary_result)
    
    await skill.shutdown()

if __name__ == "__main__":
    asyncio.run(test())
```

## Tutorial 3: Custom UI Component

Let's create a custom widget for the web UI.

### Step 1: Create Component

```javascript
// service/ui/components/agent-monitor.js
class AgentMonitor extends HTMLElement {
    constructor() {
        super();
        this.agents = [];
        this.attachShadow({ mode: 'open' });
    }
    
    connectedCallback() {
        this.render();
        this.connectWebSocket();
    }
    
    render() {
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    font-family: 'Courier New', monospace;
                    background: #0a0a0a;
                    color: #00ff00;
                    padding: 1rem;
                    border: 1px solid #00ff00;
                }
                .header {
                    border-bottom: 1px solid #00ff00;
                    padding-bottom: 0.5rem;
                    margin-bottom: 1rem;
                }
                .agent {
                    display: flex;
                    justify-content: space-between;
                    padding: 0.5rem;
                    margin: 0.25rem 0;
                    background: rgba(0, 255, 0, 0.1);
                }
                .status {
                    display: inline-block;
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                    margin-right: 0.5rem;
                }
                .status.active { background: #00ff00; }
                .status.idle { background: #ffff00; }
                .status.error { background: #ff0000; }
            </style>
            <div class="header">
                <strong>AGENT MONITOR</strong>
                <span id="count">0 agents</span>
            </div>
            <div id="agent-list"></div>
        `;
    }
    
    connectWebSocket() {
        const ws = new WebSocket('ws://localhost:18800/ws');
        
        ws.onopen = () => {
            ws.send(JSON.stringify({
                type: 'subscribe',
                channels: ['agents']
            }));
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'agent.event') {
                this.updateAgents(data.data);
            }
        };
    }
    
    updateAgents(agentData) {
        // Update internal state
        const existing = this.agents.find(a => a.id === agentData.agent_id);
        if (existing) {
            Object.assign(existing, agentData);
        } else {
            this.agents.push(agentData);
        }
        
        // Render updated list
        this.renderAgentList();
    }
    
    renderAgentList() {
        const list = this.shadowRoot.getElementById('agent-list');
        const count = this.shadowRoot.getElementById('count');
        
        count.textContent = `${this.agents.length} agent${this.agents.length !== 1 ? 's' : ''}`;
        
        list.innerHTML = this.agents.map(agent => `
            <div class="agent">
                <span>
                    <span class="status ${agent.status}"></span>
                    ${agent.name || agent.agent_id}
                </span>
                <span>${agent.event || 'idle'}</span>
            </div>
        `).join('');
    }
}

customElements.define('agent-monitor', AgentMonitor);
```

### Step 2: Add to HTML

```html
<!-- service/ui/index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Cell 0 - Agent Monitor</title>
    <script src="components/agent-monitor.js" type="module"></script>
</head>
<body>
    <agent-monitor></agent-monitor>
</body>
</html>
```

## Tutorial 4: Kernel Module (Advanced)

Creating a Rust kernel module for custom syscalls.

### Step 1: Create Module

```rust
// kernel/src/syscalls/custom.rs
use x86_64::structures::idt::InterruptStackFrame;
use crate::print;

/// Custom syscall: Get agent info
/// 
/// Arguments:
///   - rax: syscall number (0x100)
///   - rdi: pointer to agent_id buffer
///   - rsi: buffer length
/// Returns:
///   - rax: 0 on success, error code on failure
pub extern "x86-interrupt" fn syscall_agent_info(
    stack_frame: InterruptStackFrame
) {
    print!("Custom syscall: agent_info\n");
    
    // Implementation would read agent info from kernel structures
    // and write to user buffer
    
    // Return success
    unsafe {
        core::arch::asm!(
            "mov rax, 0",  // Success code
            options(nomem, nostack)
        );
    }
}

/// Register custom syscalls
pub fn register_custom_syscalls() {
    // Would add entries to syscall table
    print!("Custom syscalls registered\n");
}
```

### Step 2: Build and Test

```bash
cd kernel
cargo build --release
./build.sh test
```

## Best Practices

### 1. Error Handling

```python
# Good: Graceful error handling
async def safe_operation(self):
    try:
        result = await risky_call()
        return {"success": True, "data": result}
    except NetworkError as e:
        return {"success": False, "error": f"Network: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected: {e}"}
```

### 2. Resource Management

```python
# Good: Proper cleanup
class MyAgent:
    def __init__(self):
        self.resources = []
    
    async def initialize(self):
        self.http_client = httpx.AsyncClient()
        return True
    
    async def shutdown(self):
        if self.http_client:
            await self.http_client.aclose()
```

### 3. Async Patterns

```python
# Good: Concurrent operations
async def process_batch(self, items):
    tasks = [self.process_item(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]
```

### 4. Testing

```python
# test_my_agent.py
import pytest
from extensions.my_first_agent.agent import MyFirstAgent

@pytest.fixture
async def agent():
    a = MyFirstAgent()
    await a.initialize()
    yield a
    await a.shutdown()

@pytest.mark.asyncio
async def test_greeting(agent):
    context = AgentContext(
        message="Hello!",
        user_id="test_user",
        conversation_history=[],
        tpv_profile={"identity": {"sovereign_name": "Test"}}
    )
    
    result = await agent.handle_message(context)
    assert "Test" in result["content"]
    assert result["confidence"] > 0.5
```

## Debugging Tips

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Kernel Debugging

```bash
# Run kernel in QEMU with GDB
cd kernel
qemu-system-x86_64 \
  -drive format=raw,file=target/x86_64-bootimage-cell0_kernel.bin \
  -serial stdio \
  -s -S  # GDB server on port 1234, wait for connection

# In another terminal
gdb target/x86_64-bootimage-cell0_kernel
(gdb) target remote localhost:1234
(gdb) continue
```

### WebSocket Debugging

```javascript
// Add to browser console
const ws = new WebSocket('ws://localhost:18800/ws');
ws.onmessage = (e) => console.log('WS:', JSON.parse(e.data));
ws.send(JSON.stringify({type: 'ping'}));
```

## Next Steps

- Read the [Architecture Guide](ARCHITECTURE_GUIDE.md)
- Explore [API Reference](API_REFERENCE.md)
- Check out example extensions in `extensions/examples/`
- Join the [Discord community](https://discord.gg/cell0)
