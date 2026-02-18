"""
Locust Load Testing for Cell 0 OS

Production-grade load testing with scenarios for:
- Chat API endpoints
- Status/health checks
- Model listing
- WebSocket connections
- Sustained load benchmarks

Author: KULLU (Cell 0 OS)
"""

import json
import random
import time
from typing import Optional

from locust import HttpUser, TaskSet, task, between, events
from locust.runners import MasterRunner
import websocket
import gevent


# Configuration
class Cell0Config:
    """Load test configuration"""
    HOST = "http://localhost:18800"
    WS_HOST = "ws://localhost:18801"
    
    # Test data
    SAMPLE_MESSAGES = [
        "Hello, how are you?",
        "What is the weather like today?",
        "Tell me a joke",
        "What can you do?",
        "Help me with a task",
        "What is Cell 0 OS?",
        "How does the agent system work?",
        "Explain quantum computing",
        "Write a Python function",
        "Summarize this concept",
    ]
    
    MODEL_IDS = [
        "qwen2.5:7b",
        "llama3.2:3b",
        "mistral:7b",
    ]


class Cell0Metrics:
    """Custom metrics collector"""
    
    def __init__(self):
        self.chat_latency = []
        self.ws_connect_time = []
        self.errors = []
        
    def record_chat_latency(self, latency_ms: float):
        self.chat_latency.append(latency_ms)
        
    def record_ws_connect_time(self, time_ms: float):
        self.ws_connect_time.append(time_ms)
        
    def record_error(self, error_type: str, message: str):
        self.errors.append({"type": error_type, "message": message})
        
    def get_summary(self) -> dict:
        if not self.chat_latency:
            return {}
            
        return {
            "chat_latency_avg_ms": sum(self.chat_latency) / len(self.chat_latency),
            "chat_latency_p95_ms": sorted(self.chat_latency)[int(len(self.chat_latency) * 0.95)],
            "chat_latency_p99_ms": sorted(self.chat_latency)[int(len(self.chat_latency) * 0.99)],
            "ws_connect_avg_ms": sum(self.ws_connect_time) / len(self.ws_connect_time) if self.ws_connect_time else 0,
            "total_errors": len(self.errors),
            "error_types": list(set(e["type"] for e in self.errors)),
        }


# Global metrics instance
metrics = Cell0Metrics()


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Record request metrics"""
    if exception:
        metrics.record_error(type(exception).__name__, str(exception))


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print summary at end of test"""
    summary = metrics.get_summary()
    if summary:
        print("\n" + "="*60)
        print("CELL 0 LOAD TEST SUMMARY")
        print("="*60)
        for key, value in summary.items():
            print(f"  {key}: {value}")
        print("="*60)


class ChatTasks(TaskSet):
    """Chat API tasks"""
    
    @task(10)
    def send_chat_message(self):
        """Send a chat message"""
        message = random.choice(Cell0Config.SAMPLE_MESSAGES)
        
        start_time = time.time()
        
        with self.client.post(
            "/api/chat",
            json={
                "message": message,
                "stream": False,
                "model": random.choice(Cell0Config.MODEL_IDS),
            },
            catch_response=True,
            name="POST /api/chat",
        ) as response:
            latency_ms = (time.time() - start_time) * 1000
            metrics.record_chat_latency(latency_ms)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "response" in data or "content" in data:
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except Exception as e:
                    response.failure(f"JSON parse error: {e}")
            else:
                response.failure(f"HTTP {response.status_code}")
                
    @task(3)
    def send_chat_message_streaming(self):
        """Send a streaming chat message"""
        message = random.choice(Cell0Config.SAMPLE_MESSAGES)
        
        start_time = time.time()
        
        with self.client.post(
            "/api/chat",
            json={
                "message": message,
                "stream": True,
                "model": random.choice(Cell0Config.MODEL_IDS),
            },
            catch_response=True,
            name="POST /api/chat (streaming)",
        ) as response:
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class StatusTasks(TaskSet):
    """Status and health check tasks"""
    
    @task(5)
    def check_health(self):
        """Check health endpoint"""
        with self.client.get(
            "/api/health",
            catch_response=True,
            name="GET /api/health",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "healthy":
                        response.success()
                    else:
                        response.failure("Unhealthy status")
                except Exception:
                    response.success()  # Assume OK if 200
            else:
                response.failure(f"HTTP {response.status_code}")
                
    @task(5)
    def check_status(self):
        """Check status endpoint"""
        self.client.get(
            "/api/status",
            name="GET /api/status",
        )
        
    @task(2)
    def get_system_info(self):
        """Get system information"""
        self.client.get(
            "/api/system/info",
            name="GET /api/system/info",
        )


class ModelTasks(TaskSet):
    """Model management tasks"""
    
    @task(5)
    def list_models(self):
        """List available models"""
        with self.client.get(
            "/api/models",
            catch_response=True,
            name="GET /api/models",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "models" in data or isinstance(data, list):
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except Exception as e:
                    response.failure(f"JSON parse error: {e}")
            else:
                response.failure(f"HTTP {response.status_code}")
                
    @task(2)
    def get_model_details(self):
        """Get details for a specific model"""
        model_id = random.choice(Cell0Config.MODEL_IDS)
        
        self.client.get(
            f"/api/models/{model_id}",
            name="GET /api/models/{id}",
        )


class WebSocketTasks(TaskSet):
    """WebSocket tasks"""
    
    def on_start(self):
        """Initialize WebSocket connection"""
        self.ws = None
        self.ws_id = None
        
    def on_stop(self):
        """Close WebSocket connection"""
        if self.ws:
            self.ws.close()
            
    @task(3)
    def websocket_chat(self):
        """Chat via WebSocket"""
        try:
            start_time = time.time()
            
            # Connect to WebSocket
            self.ws = websocket.create_connection(
                Cell0Config.WS_HOST,
                timeout=10,
            )
            
            connect_time_ms = (time.time() - start_time) * 1000
            metrics.record_ws_connect_time(connect_time_ms)
            
            # Wait for welcome message
            welcome = self.ws.recv()
            welcome_data = json.loads(welcome)
            self.ws_id = welcome_data.get("params", {}).get("connection_id")
            
            # Send chat message
            message = random.choice(Cell0Config.SAMPLE_MESSAGES)
            
            request = {
                "jsonrpc": "2.0",
                "method": "chat.send",
                "params": {
                    "message": message,
                    "model": random.choice(Cell0Config.MODEL_IDS),
                },
                "id": random.randint(1, 1000000),
            }
            
            self.ws.send(json.dumps(request))
            
            # Wait for response
            response = self.ws.recv()
            response_data = json.loads(response)
            
            if "result" in response_data or "method" in response_data:
                self.user.environment.events.request.fire(
                    request_type="WebSocket",
                    name="WS Chat",
                    response_time=(time.time() - start_time) * 1000,
                    response_length=len(response),
                    response=None,
                    context={},
                    exception=None,
                )
            else:
                raise Exception(f"Error response: {response_data}")
                
        except Exception as e:
            self.user.environment.events.request.fire(
                request_type="WebSocket",
                name="WS Chat",
                response_time=(time.time() - start_time) * 1000,
                response_length=0,
                response=None,
                context={},
                exception=e,
            )
        finally:
            if self.ws:
                self.ws.close()
                self.ws = None


class Cell0User(HttpUser):
    """
    Main Locust user class for Cell 0 OS load testing
    
    Simulates realistic user behavior with weighted task distribution.
    """
    
    host = Cell0Config.HOST
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    tasks = {
        ChatTasks: 10,
        StatusTasks: 3,
        ModelTasks: 2,
        WebSocketTasks: 2,
    }
    
    def on_start(self):
        """Called when user starts"""
        # Perform initial health check
        self.client.get("/api/health")
        
    def on_stop(self):
        """Called when user stops"""
        pass


class SustainedLoadUser(HttpUser):
    """
    Sustained load test user
    
    Maintains constant load for soak testing.
    """
    
    host = Cell0Config.HOST
    wait_time = between(0.5, 1.5)
    
    @task
    def sustained_chat(self):
        """Continuous chat requests for sustained load"""
        message = random.choice(Cell0Config.SAMPLE_MESSAGES)
        
        self.client.post(
            "/api/chat",
            json={
                "message": message,
                "stream": False,
            },
            name="POST /api/chat (sustained)",
        )
        
    @task(2)
    def sustained_health_check(self):
        """Frequent health checks during sustained load"""
        self.client.get("/api/health", name="GET /api/health (sustained)")


class BurstLoadUser(HttpUser):
    """
    Burst load test user
    
    Simulates traffic spikes.
    """
    
    host = Cell0Config.HOST
    wait_time = between(0.1, 0.5)  # Very short wait times
    
    @task
    def burst_chat(self):
        """High-frequency chat requests"""
        message = random.choice(Cell0Config.SAMPLE_MESSAGES[:3])  # Use common messages
        
        self.client.post(
            "/api/chat",
            json={
                "message": message,
                "stream": False,
            },
            name="POST /api/chat (burst)",
        )


# Benchmark scenarios
class BenchmarkChatUser(HttpUser):
    """
    Benchmark user for measuring chat performance
    
    Use with: locust -f locustfile.py BenchmarkChatUser -r 10 -t 5m
    """
    
    host = Cell0Config.HOST
    wait_time = between(2, 4)
    
    @task
    def benchmark_chat(self):
        """Consistent chat for benchmarking"""
        start_time = time.time()
        
        with self.client.post(
            "/api/chat",
            json={
                "message": "What is the capital of France?",
                "stream": False,
                "model": "qwen2.5:7b",
            },
            catch_response=True,
            name="Benchmark Chat",
        ) as response:
            latency = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# Stress test scenarios
class StressTestUser(HttpUser):
    """
    Stress test user
    
    Tests system under extreme load to find breaking points.
    """
    
    host = Cell0Config.HOST
    wait_time = between(0.01, 0.1)  # Minimal wait
    
    @task(10)
    def stress_chat(self):
        """Maximum chat load"""
        self.client.post(
            "/api/chat",
            json={"message": "test", "stream": False},
            name="POST /api/chat (stress)",
        )
        
    @task(5)
    def stress_status(self):
        """Maximum status check load"""
        self.client.get("/api/status", name="GET /api/status (stress)")
        
    @task(2)
    def stress_models(self):
        """Maximum model list load"""
        self.client.get("/api/models", name="GET /api/models (stress)")


# Custom commands for specific test scenarios
def run_benchmark():
    """Run a standard benchmark"""
    import subprocess
    import sys
    
    cmd = [
        sys.executable, "-m", "locust",
        "-f", __file__,
        "--host", Cell0Config.HOST,
        "-u", "50",  # 50 users
        "-r", "5",   # Spawn 5 users/second
        "-t", "5m",  # Run for 5 minutes
        "--headless",
        "--only-summary",
        "Cell0User",
    ]
    
    subprocess.run(cmd)


def run_stress_test():
    """Run a stress test"""
    import subprocess
    import sys
    
    cmd = [
        sys.executable, "-m", "locust",
        "-f", __file__,
        "--host", Cell0Config.HOST,
        "-u", "500",  # 500 users
        "-r", "50",   # Spawn 50 users/second
        "-t", "10m",  # Run for 10 minutes
        "--headless",
        "StressTestUser",
    ]
    
    subprocess.run(cmd)


def run_soak_test():
    """Run a long-duration soak test"""
    import subprocess
    import sys
    
    cmd = [
        sys.executable, "-m", "locust",
        "-f", __file__,
        "--host", Cell0Config.HOST,
        "-u", "20",   # 20 users
        "-r", "2",    # Spawn 2 users/second
        "-t", "1h",   # Run for 1 hour
        "--headless",
        "SustainedLoadUser",
    ]
    
    subprocess.run(cmd)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Cell 0 OS Load Testing")
    parser.add_argument(
        "command",
        choices=["benchmark", "stress", "soak"],
        help="Test scenario to run",
    )
    
    args = parser.parse_args()
    
    if args.command == "benchmark":
        run_benchmark()
    elif args.command == "stress":
        run_stress_test()
    elif args.command == "soak":
        run_soak_test()