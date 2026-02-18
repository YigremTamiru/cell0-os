#!/usr/bin/env python3
"""
🔍 Provider Integration Test Suite
Tests Moonshot, OpenAI, Anthropic, and Ollama providers
"""

import asyncio
import aiohttp
import json
import os
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Test configuration
@dataclass
class ProviderTest:
    name: str
    provider_id: str
    base_url: str
    api_type: str  # openai-completions, anthropic-messages, ollama
    models_endpoint: str
    chat_endpoint: str
    api_key: Optional[str] = None
    headers: Dict[str, str] = None
    test_model: str = ""
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}

# Test results
@dataclass
class TestResult:
    provider: str
    test_name: str
    status: str  # PASS, FAIL, SKIP
    message: str
    duration_ms: float
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

class ProviderTester:
    """Test AI provider integrations"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.providers: List[ProviderTest] = []
        self.setup_providers()
        
    def setup_providers(self):
        """Configure providers to test"""
        # Moonshot
        moonshot_key = os.getenv("MOONSHOT_API_KEY")
        self.providers.append(ProviderTest(
            name="Moonshot (Kimi)",
            provider_id="moonshot",
            base_url="https://api.moonshot.ai/v1",
            api_type="openai-completions",
            models_endpoint="/models",
            chat_endpoint="/chat/completions",
            api_key=moonshot_key,
            headers={"Authorization": f"Bearer {moonshot_key}"} if moonshot_key else {},
            test_model="kimi-k2.5"
        ))
        
        # OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        self.providers.append(ProviderTest(
            name="OpenAI (GPT)",
            provider_id="openai",
            base_url="https://api.openai.com/v1",
            api_type="openai-completions",
            models_endpoint="/models",
            chat_endpoint="/chat/completions",
            api_key=openai_key,
            headers={"Authorization": f"Bearer {openai_key}"} if openai_key else {},
            test_model="gpt-4o"
        ))
        
        # Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.providers.append(ProviderTest(
            name="Anthropic (Claude)",
            provider_id="anthropic",
            base_url="https://api.anthropic.com/v1",
            api_type="anthropic-messages",
            models_endpoint="/models",
            chat_endpoint="/messages",
            api_key=anthropic_key,
            headers={
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01"
            } if anthropic_key else {},
            test_model="claude-3-5-sonnet-20241022"
        ))
        
        # Ollama (local)
        self.providers.append(ProviderTest(
            name="Ollama (Local)",
            provider_id="ollama",
            base_url="http://localhost:11434",
            api_type="ollama",
            models_endpoint="/api/tags",
            chat_endpoint="/api/chat",
            api_key=None,
            headers={},
            test_model="llama3.2"  # Common default
        ))
    
    async def run_all_tests(self):
        """Run all provider tests"""
        print("🔍 AI PROVIDER INTEGRATION TEST SUITE")
        print("=" * 70)
        print(f"Started: {datetime.now().isoformat()}")
        print()
        
        async with aiohttp.ClientSession() as session:
            for provider in self.providers:
                await self.test_provider(session, provider)
        
        self.print_summary()
        return self.results
    
    async def test_provider(self, session: aiohttp.ClientSession, provider: ProviderTest):
        """Test a single provider"""
        print(f"\n{'='*70}")
        print(f"📦 Testing: {provider.name}")
        print(f"   Base URL: {provider.base_url}")
        print(f"   API Type: {provider.api_type}")
        print(f"   API Key Present: {'Yes' if provider.api_key else 'No'}")
        print("="*70)
        
        # Test 1: API Key Validation
        await self.test_api_key_validation(session, provider)
        
        # Test 2: Model Listing
        await self.test_model_listing(session, provider)
        
        # Test 3: Chat Completion
        await self.test_chat_completion(session, provider)
        
        # Test 4: Error Handling (Invalid Key)
        await self.test_invalid_key_error(session, provider)
        
        # Test 5: Health Check
        await self.test_health_check(session, provider)
    
    async def test_api_key_validation(self, session: aiohttp.ClientSession, provider: ProviderTest):
        """Test API key validation"""
        test_name = "API Key Validation"
        start = asyncio.get_event_loop().time()
        
        try:
            if provider.provider_id == "ollama":
                # Ollama doesn't require API key
                self.add_result(provider, test_name, "PASS", 
                    "Ollama does not require API key (local deployment)", 
                    start, {"note": "Local LLM server"})
                return
            
            if not provider.api_key:
                self.add_result(provider, test_name, "FAIL",
                    f"API key not found. Set {provider.provider_id.upper()}_API_KEY environment variable.",
                    start, {"error": "missing_api_key"})
                return
            
            # Try to access models endpoint to validate key
            url = f"{provider.base_url}{provider.models_endpoint}"
            async with session.get(url, headers=provider.headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    self.add_result(provider, test_name, "PASS",
                        "API key is valid", start, {"status_code": resp.status})
                elif resp.status == 401:
                    text = await resp.text()
                    self.add_result(provider, test_name, "FAIL",
                        f"API key invalid: {text}", start, {"status_code": resp.status})
                elif resp.status == 403:
                    text = await resp.text()
                    self.add_result(provider, test_name, "FAIL",
                        f"API key unauthorized: {text}", start, {"status_code": resp.status})
                else:
                    text = await resp.text()
                    self.add_result(provider, test_name, "FAIL",
                        f"Unexpected response: {resp.status} - {text[:200]}", 
                        start, {"status_code": resp.status})
        
        except aiohttp.ClientConnectorError as e:
            self.add_result(provider, test_name, "FAIL",
                f"Connection error: {str(e)}", start, {"error_type": "connection"})
        except asyncio.TimeoutError:
            self.add_result(provider, test_name, "FAIL",
                "Connection timeout", start, {"error_type": "timeout"})
        except Exception as e:
            self.add_result(provider, test_name, "FAIL",
                f"Error: {str(e)}", start, {"error_type": type(e).__name__})
    
    async def test_model_listing(self, session: aiohttp.ClientSession, provider: ProviderTest):
        """Test model listing endpoint"""
        test_name = "Model Listing"
        start = asyncio.get_event_loop().time()
        
        try:
            url = f"{provider.base_url}{provider.models_endpoint}"
            async with session.get(url, headers=provider.headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Extract models based on provider format
                    models = self.extract_models(data, provider)
                    
                    if models:
                        self.add_result(provider, test_name, "PASS",
                            f"Successfully retrieved {len(models)} models", start,
                            {"model_count": len(models), "models": models[:5]})
                    else:
                        self.add_result(provider, test_name, "FAIL",
                            "No models found in response", start,
                            {"response_preview": str(data)[:200]})
                
                elif resp.status == 401:
                    self.add_result(provider, test_name, "SKIP",
                        "Cannot test - invalid API key", start, {})
                elif resp.status == 429:
                    self.add_result(provider, test_name, "FAIL",
                        "Rate limit exceeded", start, {"status_code": 429})
                else:
                    text = await resp.text()
                    self.add_result(provider, test_name, "FAIL",
                        f"Failed: {resp.status} - {text[:200]}", start,
                        {"status_code": resp.status})
        
        except aiohttp.ClientConnectorError as e:
            self.add_result(provider, test_name, "FAIL",
                f"Connection error: {str(e)}", start, {"error_type": "connection"})
        except asyncio.TimeoutError:
            self.add_result(provider, test_name, "FAIL",
                "Request timeout", start, {"error_type": "timeout"})
        except Exception as e:
            self.add_result(provider, test_name, "FAIL",
                f"Error: {str(e)}", start, {"error_type": type(e).__name__})
    
    async def test_chat_completion(self, session: aiohttp.ClientSession, provider: ProviderTest):
        """Test chat completion"""
        test_name = "Chat Completion"
        start = asyncio.get_event_loop().time()
        
        try:
            # Skip if no API key for cloud providers
            if provider.provider_id != "ollama" and not provider.api_key:
                self.add_result(provider, test_name, "SKIP",
                    "Cannot test - no API key", start, {})
                return
            
            # Build request based on API type
            if provider.api_type == "openai-completions":
                payload = {
                    "model": provider.test_model,
                    "messages": [{"role": "user", "content": "Say 'Hello from test' and nothing else."}],
                    "max_tokens": 20,
                    "temperature": 0.0
                }
            elif provider.api_type == "anthropic-messages":
                payload = {
                    "model": provider.test_model,
                    "messages": [{"role": "user", "content": "Say 'Hello from test' and nothing else."}],
                    "max_tokens": 20
                }
            elif provider.api_type == "ollama":
                payload = {
                    "model": provider.test_model,
                    "messages": [{"role": "user", "content": "Say 'Hello from test' and nothing else."}],
                    "stream": False
                }
            else:
                self.add_result(provider, test_name, "SKIP",
                    f"Unknown API type: {provider.api_type}", start, {})
                return
            
            url = f"{provider.base_url}{provider.chat_endpoint}"
            
            async with session.post(url, headers=provider.headers, json=payload, 
                                   timeout=aiohttp.ClientTimeout(total=30)) as resp:
                
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Extract response content based on provider
                    content = self.extract_completion_content(data, provider)
                    
                    if content and "hello" in content.lower():
                        self.add_result(provider, test_name, "PASS",
                            f"Chat completion successful: '{content[:50]}...'", start,
                            {"response": content[:100], "tokens_used": data.get("usage", {})})
                    elif content:
                        self.add_result(provider, test_name, "PASS",
                            f"Chat completion returned: '{content[:50]}...'", start,
                            {"response": content[:100], "note": "Unexpected content but valid response"})
                    else:
                        self.add_result(provider, test_name, "FAIL",
                            "Empty response content", start, {"response": str(data)[:200]})
                
                elif resp.status == 401:
                    self.add_result(provider, test_name, "FAIL",
                        "Authentication failed - invalid API key", start, {"status_code": 401})
                elif resp.status == 429:
                    retry_after = resp.headers.get("retry-after", "unknown")
                    self.add_result(provider, test_name, "FAIL",
                        f"Rate limit exceeded. Retry after: {retry_after}", start,
                        {"status_code": 429, "retry_after": retry_after})
                elif resp.status == 404:
                    text = await resp.text()
                    self.add_result(provider, test_name, "FAIL",
                        f"Model not found: {provider.test_model}", start,
                        {"status_code": 404, "error": text[:200]})
                else:
                    text = await resp.text()
                    self.add_result(provider, test_name, "FAIL",
                        f"Request failed: {resp.status} - {text[:200]}", start,
                        {"status_code": resp.status})
        
        except aiohttp.ClientConnectorError as e:
            if provider.provider_id == "ollama":
                self.add_result(provider, test_name, "FAIL",
                    f"Ollama not running or not accessible: {str(e)}", start,
                    {"error_type": "connection", "hint": "Ensure Ollama is installed and running"})
            else:
                self.add_result(provider, test_name, "FAIL",
                    f"Connection error: {str(e)}", start, {"error_type": "connection"})
        except asyncio.TimeoutError:
            self.add_result(provider, test_name, "FAIL",
                "Request timeout (30s)", start, {"error_type": "timeout"})
        except Exception as e:
            self.add_result(provider, test_name, "FAIL",
                f"Error: {str(e)}", start, {"error_type": type(e).__name__})
    
    async def test_invalid_key_error(self, session: aiohttp.ClientSession, provider: ProviderTest):
        """Test error handling with invalid key"""
        test_name = "Invalid Key Error Handling"
        start = asyncio.get_event_loop().time()
        
        try:
            if provider.provider_id == "ollama":
                self.add_result(provider, test_name, "SKIP",
                    "Ollama doesn't use API keys", start, {})
                return
            
            # Create request with intentionally invalid key
            bad_headers = dict(provider.headers)
            if "Authorization" in bad_headers:
                bad_headers["Authorization"] = "Bearer invalid_key_12345"
            if "x-api-key" in bad_headers:
                bad_headers["x-api-key"] = "invalid_key_12345"
            
            url = f"{provider.base_url}{provider.models_endpoint}"
            async with session.get(url, headers=bad_headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 401:
                    self.add_result(provider, test_name, "PASS",
                        "Correctly returns 401 for invalid key", start,
                        {"status_code": resp.status})
                elif resp.status == 403:
                    self.add_result(provider, test_name, "PASS",
                        "Correctly returns 403 for invalid key", start,
                        {"status_code": resp.status})
                else:
                    self.add_result(provider, test_name, "WARN",
                        f"Unexpected status for invalid key: {resp.status}", start,
                        {"status_code": resp.status, "expected": "401 or 403"})
        
        except Exception as e:
            self.add_result(provider, test_name, "FAIL",
                f"Error during test: {str(e)}", start, {"error_type": type(e).__name__})
    
    async def test_health_check(self, session: aiohttp.ClientSession, provider: ProviderTest):
        """Test provider health check"""
        test_name = "Health Check"
        start = asyncio.get_event_loop().time()
        
        try:
            url = f"{provider.base_url}{provider.models_endpoint}"
            async with session.get(url, headers=provider.headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                healthy = resp.status == 200
                
                if healthy:
                    self.add_result(provider, test_name, "PASS",
                        "Provider is healthy and accessible", start,
                        {"status_code": resp.status, "healthy": True})
                else:
                    self.add_result(provider, test_name, "FAIL",
                        f"Provider unhealthy: {resp.status}", start,
                        {"status_code": resp.status, "healthy": False})
        
        except Exception as e:
            self.add_result(provider, test_name, "FAIL",
                f"Health check failed: {str(e)}", start,
                {"error_type": type(e).__name__, "healthy": False})
    
    def extract_models(self, data: Dict, provider: ProviderTest) -> List[str]:
        """Extract model list from provider response"""
        models = []
        
        if provider.api_type == "openai-completions":
            # OpenAI/Moonshot format: { "data": [{"id": "model-name"}] }
            for model in data.get("data", []):
                model_id = model.get("id") or model.get("name")
                if model_id:
                    models.append(model_id)
        
        elif provider.api_type == "anthropic-messages":
            # Anthropic format
            for model in data.get("data", []):
                model_id = model.get("id")
                if model_id:
                    models.append(model_id)
        
        elif provider.api_type == "ollama":
            # Ollama format: { "models": [{"name": "model-name"}] }
            for model in data.get("models", []):
                model_name = model.get("name") or model.get("model")
                if model_name:
                    models.append(model_name)
        
        return models
    
    def extract_completion_content(self, data: Dict, provider: ProviderTest) -> str:
        """Extract completion content from response"""
        if provider.api_type == "openai-completions":
            # OpenAI format
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
        
        elif provider.api_type == "anthropic-messages":
            # Anthropic format
            content = data.get("content", [])
            if content:
                return content[0].get("text", "")
        
        elif provider.api_type == "ollama":
            # Ollama format
            return data.get("message", {}).get("content", "")
        
        return ""
    
    def add_result(self, provider: ProviderTest, test_name: str, status: str, 
                   message: str, start_time: float, details: Dict):
        """Add a test result"""
        duration = (asyncio.get_event_loop().time() - start_time) * 1000
        result = TestResult(
            provider=provider.name,
            test_name=test_name,
            status=status,
            message=message,
            duration_ms=duration,
            details=details
        )
        self.results.append(result)
        
        # Print result
        status_icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️", "WARN": "⚠️"}.get(status, "❓")
        print(f"  {status_icon} {test_name}: {message[:80]}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        # Group by provider
        by_provider = {}
        for r in self.results:
            by_provider.setdefault(r.provider, []).append(r)
        
        for provider_name, results in by_provider.items():
            print(f"\n{provider_name}:")
            
            # Count results
            passed = sum(1 for r in results if r.status == "PASS")
            failed = sum(1 for r in results if r.status == "FAIL")
            skipped = sum(1 for r in results if r.status == "SKIP")
            warned = sum(1 for r in results if r.status == "WARN")
            
            status_color = "🟢" if failed == 0 else "🟡" if failed <= 1 else "🔴"
            print(f"  Status: {status_color} {passed} passed, {failed} failed, {skipped} skipped, {warned} warned")
            
            # Show failed tests
            for r in results:
                if r.status in ("FAIL", "WARN"):
                    print(f"    - {r.test_name}: {r.message[:100]}")
        
        # Overall summary
        total = len(self.results)
        total_pass = sum(1 for r in self.results if r.status == "PASS")
        total_fail = sum(1 for r in self.results if r.status == "FAIL")
        
        print(f"\n{'=' * 70}")
        print(f"OVERALL: {total_pass}/{total} tests passed")
        
        if total_fail == 0:
            print("🎉 All providers working perfectly!")
        elif total_fail <= 3:
            print("⚠️  Some tests failed - review needed")
        else:
            print("🔴 Multiple failures - providers need configuration")
        
        print("=" * 70)

async def main():
    """Main entry point"""
    tester = ProviderTester()
    results = await tester.run_all_tests()
    
    # Save detailed results to file
    output_file = "/Users/yigremgetachewtamiru/.openclaw/workspace/provider_test_results.json"
    with open(output_file, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2, default=str)
    
    print(f"\n📁 Detailed results saved to: {output_file}")
    
    # Exit with error code if any critical tests failed
    critical_failures = sum(1 for r in results if r.status == "FAIL" and r.test_name not in ["Invalid Key Error Handling"])
    sys.exit(0 if critical_failures == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())
