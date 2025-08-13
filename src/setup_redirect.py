#!/usr/bin/env python3
"""
Simple HTTP redirect server for Bots EDI setup
Redirects any requests to the setup interface on port 9000
"""

import sys
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler

class SetupRedirectHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Override to reduce logging noise"""
        pass
    
    def do_GET(self):
        # Get the host from the request to maintain the same IP/hostname
        host = self.headers.get('Host', 'localhost')
        hostname = host.split(':')[0]  # Remove port if present
        setup_url = f"http://{hostname}:9000"
        
        self.send_response(302)
        self.send_header('Location', setup_url)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        
        redirect_html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Bots EDI Setup Required</title>
    <meta http-equiv="refresh" content="0;url={setup_url}">
</head>
<body>
    <h1>🚀 Bots EDI First-Time Setup Required</h1>
    <p>Redirecting to setup interface...</p>
    <p>If you are not automatically redirected, <a href="{setup_url}">click here</a>.</p>
</body>
</html>'''
        
        self.wfile.write(redirect_html.encode())
    
    def do_POST(self):
        # Redirect POST requests as well
        self.do_GET()

def start_redirect_server(port):
    """Start a redirect server on the specified port"""
    try:
        server = HTTPServer(('0.0.0.0', port), SetupRedirectHandler)
        print(f"🔄 Setup redirect server started on port {port}")
        server.serve_forever()
    except Exception as e:
        print(f"❌ Failed to start redirect server on port {port}: {e}")
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3.12 setup_redirect.py <port>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    start_redirect_server(port)