"""
Simple HTTP server to serve the cell0d Web UI
"""
import http.server
import socketserver
import os
import logging
from pathlib import Path

logger = logging.getLogger("cell0d.http")

class Cell0dHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler that serves the static files"""
    
    def __init__(self, *args, static_dir=None, **kwargs):
        self.static_dir = static_dir or Path(__file__).parent.parent / "static"
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        # Serve index.html for root path
        if self.path == '/':
            self.path = '/index.html'
        
        # Try to serve from static directory
        file_path = self.static_dir / self.path.lstrip('/')
        
        if file_path.exists() and file_path.is_file():
            self.send_response(200)
            
            # Set content type
            if self.path.endswith('.html'):
                self.send_header('Content-type', 'text/html')
            elif self.path.endswith('.js'):
                self.send_header('Content-type', 'application/javascript')
            elif self.path.endswith('.css'):
                self.send_header('Content-type', 'text/css')
            else:
                self.send_header('Content-type', 'application/octet-stream')
            
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "File not found")
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.debug(f"{self.address_string()} - {format % args}")


def create_http_server(port: int = 8080, static_dir: Path = None):
    """Create and return HTTP server instance"""
    static_dir = static_dir or Path(__file__).parent.parent / "static"
    
    def handler(*args, **kwargs):
        return Cell0dHTTPHandler(*args, static_dir=static_dir, **kwargs)
    
    server = socketserver.TCPServer(("0.0.0.0", port), handler)
    server.allow_reuse_address = True
    
    return server


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="cell0d HTTP Server")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    parser.add_argument("--static-dir", help="Path to static files directory")
    
    args = parser.parse_args()
    
    static_dir = Path(args.static_dir) if args.static_dir else None
    server = create_http_server(port=args.port, static_dir=static_dir)
    
    print(f"HTTP server running at http://0.0.0.0:{args.port}")
    print(f"Serving files from: {static_dir or Path(__file__).parent.parent / 'static'}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()