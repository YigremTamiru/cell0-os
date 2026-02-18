"""
Load Test Configuration for Cell 0 OS

Environment-specific configurations for load testing.
"""

import os


class BaseConfig:
    """Base configuration"""
    # API endpoints
    API_HOST = os.getenv("CELL0_API_HOST", "http://localhost:18800")
    WS_HOST = os.getenv("CELL0_WS_HOST", "ws://localhost:18801")
    
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
        "What time is it?",
        "Set a timer for 5 minutes",
        "Who won the game last night?",
        "What are the headlines today?",
        "Translate 'hello' to French",
    ]
    
    MODEL_IDS = [
        "qwen2.5:7b",
        "llama3.2:3b",
        "mistral:7b",
    ]
    
    # Timing
    WAIT_TIME_MIN = 1
    WAIT_TIME_MAX = 5
    
    # Test thresholds (milliseconds)
    THRESHOLD_CHAT_P50 = 500
    THRESHOLD_CHAT_P95 = 1000
    THRESHOLD_CHAT_P99 = 2000
    THRESHOLD_HEALTH = 50
    
    # Error thresholds (%)
    MAX_ERROR_RATE = 1.0


class DevelopmentConfig(BaseConfig):
    """Development environment"""
    API_HOST = "http://localhost:18800"
    WS_HOST = "ws://localhost:18801"
    
    # More lenient thresholds for development
    THRESHOLD_CHAT_P50 = 1000
    THRESHOLD_CHAT_P95 = 3000


class StagingConfig(BaseConfig):
    """Staging environment"""
    API_HOST = os.getenv("CELL0_API_HOST", "https://staging.cell0.io")
    WS_HOST = os.getenv("CELL0_WS_HOST", "wss://staging.cell0.io/ws")
    
    # Production-like thresholds
    THRESHOLD_CHAT_P50 = 500
    THRESHOLD_CHAT_P95 = 1500


class ProductionConfig(BaseConfig):
    """Production environment"""
    API_HOST = os.getenv("CELL0_API_HOST", "https://api.cell0.io")
    WS_HOST = os.getenv("CELL0_WS_HOST", "wss://api.cell0.io/ws")
    
    # Strict thresholds
    THRESHOLD_CHAT_P50 = 300
    THRESHOLD_CHAT_P95 = 800
    THRESHOLD_CHAT_P99 = 1500
    THRESHOLD_HEALTH = 30
    
    MAX_ERROR_RATE = 0.1


# Configuration mapping
CONFIGS = {
    "development": DevelopmentConfig,
    "staging": StagingConfig,
    "production": ProductionConfig,
}


def get_config(env: str = None):
    """Get configuration for environment"""
    env = env or os.getenv("CELL0_ENV", "development")
    return CONFIGS.get(env, DevelopmentConfig)()


# Load current configuration
config = get_config()