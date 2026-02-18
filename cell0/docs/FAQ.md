# Cell 0 OS - Frequently Asked Questions (FAQ)

## Quick Navigation

- [Installation Issues](#installation-issues)
- [Configuration Problems](#configuration-problems)
- [Runtime Errors](#runtime-errors)
- [Performance Issues](#performance-issues)
- [Integration Troubles](#integration-troubles)
- [API and WebSocket](#api-and-websocket)
- [Security Concerns](#security-concerns)

---

## Installation Issues

### Q: "Ollama connection refused" error on startup

**A:** This means Cell 0 cannot connect to the Ollama service. Solutions:

1. **Check if Ollama is running:**
   ```bash
   # macOS
   pgrep -l ollama
   
   # Linux
   systemctl status ollama
   ```

2. **Start Ollama:**
   ```bash
   # macOS (in a terminal)
   ollama serve
   
   # Linux
   sudo systemctl start ollama
   ```

3. **Verify Ollama is accessible:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

4. **If using Docker:**
   ```bash
   docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
   ```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed diagnostics.

---

### Q: Port 18800 already in use

**A:** Another process is using the Cell 0 HTTP API port. Find and stop it:

```bash
# Find the process
lsof -i :18800

# Or on Linux
netstat -tulpn | grep 18800

# Kill the process
kill -9 <PID>
```

Or configure Cell 0 to use a different port in your environment configuration.

---

### Q: Python version mismatch errors

**A:** Cell 0 requires Python 3.9 or higher. Check your version:

```bash
python --version
```

If you need to upgrade:

```bash
# Using pyenv (recommended)
pyenv install 3.11
pyenv local 3.11

# Using conda
conda create -n cell0 python=3.11
conda activate cell0
```

---

### Q: "Module not found" errors after installation

**A:** You likely need to install dependencies or activate your virtual environment:

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration Problems

### Q: Where are configuration files located?

**A:** Cell 0 uses these configuration locations (in order of priority):

1. Environment variables (`CELL0_*`)
2. `.env` file in the project root
3. `config/` directory files
4. Default values

Main config files:
- `config/tool_profiles.yaml` - Tool security profiles
- `integrations/signal_config.yaml` - Signal bot settings
- `integrations/google_chat_config.yaml` - Google Chat settings

---

### Q: How do I change the default ports?

**A:** Set environment variables:

```bash
export CELL0_HTTP_PORT=18800
export CELL0_WS_PORT=18801
export CELL0_OLLAMA_URL=http://localhost:11434
```

Or create a `.env` file:
```
CELL0_HTTP_PORT=18800
CELL0_WS_PORT=18801
```

---

### Q: Signal bot not sending/receiving messages

**A:** Check these common issues:

1. **Verify Signal CLI is running:**
   ```bash
   curl http://localhost:8080/v1/accounts
   ```

2. **Check phone number is configured:**
   ```bash
   # In signal_config.yaml
   phone_number: "+1234567890"
   ```

3. **Verify registration:**
   ```bash
   # Check Signal CLI logs
docker logs signal-cli-rest-api
   ```

4. **Ensure network connectivity:**
   - Signal requires internet access
   - Check firewall rules for port 8080

See [Signal Integration Guide](../integrations/SIGNAL_README.md) for complete setup.

---

## Runtime Errors

### Q: "High memory usage" warnings

**A:** Cell 0 memory usage depends on:
- Number of loaded AI models
- Active agent sessions
- Concurrent connections

**Solutions:**

1. **Limit model concurrency:**
   ```yaml
   # In your config
   max_concurrent_models: 2
   ```

2. **Reduce worker processes:**
   ```bash
   export CELL0_WORKERS=2
   ```

3. **Use smaller models:**
   - Switch from 70B to 7B/13B models
   - Use quantized models (Q4, Q5)

4. **Monitor memory:**
   ```bash
   python scripts/cell0-doctor.py --verbose
   ```

---

### Q: "Slow inference" - responses taking too long

**A:** Common causes and solutions:

| Cause | Solution |
|-------|----------|
| No GPU | Use CPU-optimized models or add GPU |
| Model too large | Use smaller/quantized models |
| High load | Reduce concurrent requests |
| Context too long | Limit conversation history |
| Thermal throttling | Improve cooling |

**Quick fixes:**
```bash
# Use quantized model
ollama pull qwen2.5:7b-q4_K_M

# Limit context window
export CELL0_MAX_CONTEXT=4096
```

---

### Q: Agent crashes or becomes unresponsive

**A:** Try these steps:

1. **Check logs:**
   ```bash
   tail -f logs/cell0.log
   ```

2. **Restart the service:**
   ```bash
   ./stop.sh && ./start.sh
   ```

3. **Check resource usage:**
   ```bash
   python scripts/cell0-doctor.py
   ```

4. **Clear stuck sessions:**
   ```bash
   # Delete session files
   rm -rf data/sessions/*
   ```

5. **Run diagnostic:**
   ```bash
   python scripts/cell0-doctor.py --verbose
   ```

---

### Q: WebSocket connection drops frequently

**A:** Common causes:

1. **Proxy timeout:** Configure your reverse proxy:
   ```nginx
   # Nginx
   proxy_read_timeout 86400;
   proxy_send_timeout 86400;
   ```

2. **Keepalive settings:**
   ```python
   # Client-side
   websocket.enableTrace(True)
   ```

3. **Network instability:** Use reconnection logic:
   ```javascript
   ws.onclose = () => {
     setTimeout(() => connect(), 5000);
   };
   ```

---

## Performance Issues

### Q: How can I improve response times?

**A:** Optimization strategies:

1. **Use GPU acceleration:**
   ```bash
   # Verify GPU is available
   ollama run llama3.1 --verbose
   ```

2. **Enable response caching:**
   ```yaml
   # config/cache.yaml
   enable_caching: true
   cache_ttl: 3600
   ```

3. **Use streaming responses:**
   ```python
   # Request streaming
   response = client.chat(messages, stream=True)
   ```

4. **Profile your setup:**
   ```bash
   python benchmarks/latency_benchmark.py
   ```

---

### Q: Too many concurrent requests causing failures

**A:** Implement rate limiting:

```yaml
# config/rate_limits.yaml
requests_per_minute: 60
concurrent_requests: 10
burst_size: 20
```

Or use API gateway configuration for external facing deployments.

---

## Integration Troubles

### Q: WhatsApp connection failed

**A:** WhatsApp requires QR code authentication:

1. **Check WhatsApp Web is enabled on your phone**
2. **Scan the QR code displayed on first run**
3. **Keep the session file secure:**
   ```bash
   chmod 600 data/whatsapp_session.json
   ```

---

### Q: Search API errors (Brave/Google)

**A:** Verify API keys are set:

```bash
# Check environment
env | grep BRAVE_API_KEY
env | grep GOOGLE_API_KEY

# Or in .env file
echo "BRAVE_API_KEY=your_key_here" >> .env
```

---

### Q: Google Chat bot not responding

**A:** Check:

1. **Credentials file exists:**
   ```bash
   ls -la credentials.json
   ```

2. **Service account has permissions:**
   - Go to Google Cloud Console
   - IAM & Admin → Service Accounts
   - Ensure Chat Bot Invoker role is assigned

3. **Bot is added to the space**

---

## API and WebSocket

### Q: How do I authenticate API requests?

**A:** Cell 0 supports multiple auth methods:

**API Key:**
```bash
curl -H "X-API-Key: your_key" http://localhost:18800/api/status
```

**JWT Token:**
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:18800/api/status
```

**WebSocket Token:**
```javascript
const ws = new WebSocket('ws://localhost:18801', [], {
  headers: { 'Authorization': 'Bearer ' + token }
});
```

---

### Q: "401 Unauthorized" errors

**A:** Check:

1. **Token is valid and not expired**
2. **Correct authentication header format**
3. **Token has required permissions**

Generate new token:
```bash
python -c "from service.gateway_protocol import auth_manager; print(auth_manager.generate_token('user', 'user'))"
```

---

### Q: CORS errors from browser

**A:** Configure CORS in your deployment:

```yaml
# config/cors.yaml
allowed_origins:
  - "https://yourdomain.com"
  - "http://localhost:3000"
allowed_methods: ["GET", "POST", "PUT", "DELETE"]
allowed_headers: ["Content-Type", "Authorization"]
```

---

## Security Concerns

### Q: Is Cell 0 secure for production use?

**A:** Cell 0 includes multiple security layers:

- **Tool Profiles** - Granular permission system
- **Sandboxing** - Isolated execution environments
- **Authentication** - Multiple auth methods
- **Audit Logging** - Complete action trail

For production:
1. Enable authentication
2. Use HTTPS/WSS
3. Configure tool profiles
4. Regular security updates

See [Security Documentation](./SECURITY.md) for details.

---

### Q: How do I rotate API keys?

**A:** Best practice for key rotation:

1. **Generate new key:**
   ```bash
   python scripts/rotate_keys.py --service brave
   ```

2. **Update configuration:**
   ```bash
   # Add to .env
   BRAVE_API_KEY_NEW=xxx
   ```

3. **Test new key:**
   ```bash
   python -c "from engine.search.brave_search import search; search('test')"
   ```

4. **Remove old key:**
   ```bash
   # After confirming new key works
   unset BRAVE_API_KEY_OLD
   ```

---

### Q: Sensitive data in logs

**A:** Configure log redaction:

```yaml
# config/logging.yaml
redact_patterns:
  - "api[_-]?key"
  - "password"
  - "token"
  - "secret"
redact_replacement: "[REDACTED]"
```

---

## Getting More Help

If your question isn't answered here:

1. **Run diagnostics:**
   ```bash
   python scripts/cell0-doctor.py --verbose
   ```

2. **Check troubleshooting guide:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

3. **Review logs:**
   ```bash
   tail -n 100 logs/cell0.log
   ```

4. **Open an issue** with:
   - Cell 0 version
   - Operating system
   - Reproduction steps
   - Relevant log excerpts

---

*Last updated: 2026-02-18*
