#!/usr/bin/env python3
"""
Bots EDI First-Time Setup Interface

This script provides a web-based interface for first-time Bots EDI setup,
allowing users to configure database settings and create admin users.
"""

import os
import sys
import json
import sqlite3
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import threading
import time
import socket

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class SetupHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Override to reduce logging noise"""
        pass
    
    def do_GET(self):
        if self.path == '/':
            self.serve_setup_page()
        elif self.path == '/status':
            self.serve_status()
        else:
            self.send_error(404)
    
    def do_POST(self):
        print(f"DEBUG: POST request to {self.path}", flush=True)
        print(f"DEBUG: Headers: {dict(self.headers)}", flush=True)
        if self.path == '/setup':
            self.handle_setup()
        else:
            self.send_error(404)
    
    def serve_setup_page(self):
        setup_html = '''<!DOCTYPE html>
<html>
<head>
    <title>Bots EDI First-Time Setup</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
        .section { margin-bottom: 25px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
        .section h2 { color: #34495e; margin-top: 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; color: #555; }
        input, select, textarea { width: 100%; padding: 8px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        input[type="radio"] { width: auto; margin-right: 8px; }
        .radio-group { margin-bottom: 15px; }
        .radio-option { margin-bottom: 10px; }
        button { background: #3498db; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #2980b9; }
        .postgres-config { display: none; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        .info { background: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        .error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        .hidden { display: none; }
        #setupResult { margin-top: 20px; }
    </style>
    <script>
        function toggleDatabaseConfig() {
            const dbType = document.querySelector('input[name="db_type"]:checked').value;
            const postgresConfig = document.querySelector('.postgres-config');
            if (dbType === 'postgres') {
                postgresConfig.style.display = 'block';
            } else {
                postgresConfig.style.display = 'none';
            }
        }
        
        async function submitSetup() {
            const form = document.getElementById('setupForm');
            const formData = new FormData(form);
            const setupResult = document.getElementById('setupResult');
            const submitBtn = document.getElementById('submitBtn');
            
            submitBtn.disabled = true;
            submitBtn.textContent = 'Setting up...';
            setupResult.innerHTML = '<div class="info">Setting up Bots EDI system, please wait...</div>';
            
            // Convert FormData to URL-encoded string for better compatibility
            const urlEncoded = new URLSearchParams();
            for (const [key, value] of formData) {
                urlEncoded.append(key, value);
                console.log(`Form field: ${key} = ${value} (length: ${value.length})`);
            }
            
            console.log('Form data to submit:', urlEncoded.toString());
            
            try {
                // Use current location to ensure proper URL resolution
                const setupUrl = `${window.location.protocol}//${window.location.host}/setup`;
                console.log('Submitting to URL:', setupUrl);
                
                const response = await fetch(setupUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: urlEncoded.toString()
                });
                
                console.log('Response status:', response.status);
                console.log('Response headers:', response.headers);
                
                const result = await response.text();
                setupResult.innerHTML = result;
                
                if (response.ok && result.includes('success')) {
                    setTimeout(() => {
                        setupResult.innerHTML += '<div class="info">Setup complete! Redirecting to login page...</div>';
                        setTimeout(() => {
                            // Use the same host but port 8080 for the main interface
                            const mainUrl = `${window.location.protocol}//${window.location.hostname}:8080`;
                            window.location.href = mainUrl;
                        }, 3000);
                    }, 2000);
                }
            } catch (error) {
                setupResult.innerHTML = '<div class="error">Setup failed: ' + error.message + '</div>';
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Complete Setup';
            }
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            toggleDatabaseConfig();
        });
    </script>
</head>
<body>
    <div class="container">
        <h1>🚀 Bots EDI First-Time Setup</h1>
        
        <div class="info">
            <strong>Welcome to Bots EDI!</strong><br>
            This is your first time running the system. Please configure your database and create an admin user to get started.
        </div>
        
        <form id="setupForm" onsubmit="event.preventDefault(); submitSetup();">
            <div class="section">
                <h2>Database Configuration</h2>
                <div class="radio-group">
                    <div class="radio-option">
                        <input type="radio" id="sqlite" name="db_type" value="sqlite" checked onchange="toggleDatabaseConfig()">
                        <label for="sqlite" style="display: inline; font-weight: normal;">
                            <strong>SQLite (Recommended for development)</strong><br>
                            <small style="color: #666;">Simple file-based database. Perfect for testing and small deployments.</small>
                        </label>
                    </div>
                    <div class="radio-option">
                        <input type="radio" id="postgres" name="db_type" value="postgres" onchange="toggleDatabaseConfig()">
                        <label for="postgres" style="display: inline; font-weight: normal;">
                            <strong>PostgreSQL (Recommended for production)</strong><br>
                            <small style="color: #666;">Enterprise-grade database with advanced features and better performance.</small>
                        </label>
                    </div>
                </div>
                
                <div class="postgres-config">
                    <label for="postgres_host">PostgreSQL Host:</label>
                    <input type="text" id="postgres_host" name="postgres_host" placeholder="localhost">
                    
                    <label for="postgres_port">PostgreSQL Port:</label>
                    <input type="number" id="postgres_port" name="postgres_port" value="5432">
                    
                    <label for="postgres_db">Database Name:</label>
                    <input type="text" id="postgres_db" name="postgres_db" placeholder="botsdb">
                    
                    <label for="postgres_user">Username:</label>
                    <input type="text" id="postgres_user" name="postgres_user" placeholder="bots">
                    
                    <label for="postgres_password">Password:</label>
                    <input type="password" id="postgres_password" name="postgres_password" placeholder="Enter database password">
                </div>
            </div>
            
            <div class="section">
                <h2>Admin User Creation</h2>
                <p style="color: #666; margin-bottom: 15px;">Create your administrator account for accessing the Bots EDI web interface.</p>
                
                <label for="admin_username">Admin Username:</label>
                <input type="text" id="admin_username" name="admin_username" value="admin" required>
                
                <label for="admin_email">Admin Email:</label>
                <input type="email" id="admin_email" name="admin_email" placeholder="admin@example.com" required>
                
                <label for="admin_password">Admin Password:</label>
                <input type="password" id="admin_password" name="admin_password" required>
                
                <label for="admin_password_confirm">Confirm Password:</label>
                <input type="password" id="admin_password_confirm" name="admin_password_confirm" required>
            </div>
            
            <button type="submit" id="submitBtn">Complete Setup</button>
        </form>
        
        <div id="setupResult"></div>
    </div>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(setup_html.encode())
    
    def serve_status(self):
        """Return setup status"""
        setup_complete = os.path.exists('/app/.bots_setup_complete')
        status = {'setup_complete': setup_complete}
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status).encode())
    
    def handle_setup(self):
        try:
            # Parse form data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # Check content type to handle both form-urlencoded and multipart data
            content_type = self.headers.get('Content-Type', '')
            print(f"DEBUG: Content-Type: {content_type}")
            
            if 'multipart/form-data' in content_type:
                # Handle multipart form data (from JavaScript FormData)
                import cgi
                import sys
                from io import StringIO
                
                # Parse multipart data using cgi.FieldStorage
                class FakeRequest:
                    def __init__(self, post_data, headers):
                        self.stdin = StringIO(post_data.decode('utf-8', errors='ignore'))
                        self.environ = {
                            'REQUEST_METHOD': 'POST',
                            'CONTENT_TYPE': headers.get('Content-Type', ''),
                            'CONTENT_LENGTH': headers.get('Content-Length', '0')
                        }
                
                # Try a simpler approach - parse multipart manually
                boundary = content_type.split('boundary=')[1] if 'boundary=' in content_type else None
                print(f"DEBUG: Boundary: {boundary}")
                
                if boundary:
                    # Simple multipart parsing
                    parts = post_data.split(f'--{boundary}'.encode())
                    form_values = {}
                    
                    for part in parts:
                        if b'Content-Disposition: form-data' in part:
                            lines = part.split(b'\r\n')
                            name = None
                            value = None
                            
                            for i, line in enumerate(lines):
                                if b'name="' in line:
                                    name = line.split(b'name="')[1].split(b'"')[0].decode()
                                elif line == b'' and i + 1 < len(lines):
                                    # Value is on the next line after empty line
                                    value = lines[i + 1].decode().strip()
                                    break
                            
                            if name and value is not None:
                                form_values[name] = value
                                print(f"DEBUG: Found {name} = '{value}' (length: {len(value)})")
                    
                    # Extract form values from parsed data
                    db_type = form_values.get('db_type', 'sqlite')
                    admin_username = form_values.get('admin_username', 'admin')
                    admin_email = form_values.get('admin_email', '')
                    admin_password = form_values.get('admin_password', '')
                    admin_password_confirm = form_values.get('admin_password_confirm', '')
                    
                    # For PostgreSQL fields
                    postgres_host = form_values.get('postgres_host', 'localhost')
                    postgres_port = form_values.get('postgres_port', '5432')
                    postgres_db = form_values.get('postgres_db', 'botsdb')
                    postgres_user = form_values.get('postgres_user', 'bots')
                    postgres_password = form_values.get('postgres_password', '')
                else:
                    # Fallback if boundary parsing fails
                    db_type = 'sqlite'
                    admin_username = 'admin'
                    admin_email = ''
                    admin_password = ''
                    admin_password_confirm = ''
                    postgres_host = 'localhost'
                    postgres_port = '5432'
                    postgres_db = 'botsdb'
                    postgres_user = 'bots'
                    postgres_password = ''
                
            else:
                # Handle URL-encoded form data (from curl/standard forms)
                form_data = parse_qs(post_data.decode('utf-8'))
                
                # Extract form values
                db_type = form_data.get('db_type', ['sqlite'])[0]
                admin_username = form_data.get('admin_username', ['admin'])[0]
                admin_email = form_data.get('admin_email', [''])[0]
                admin_password = form_data.get('admin_password', [''])[0]
                admin_password_confirm = form_data.get('admin_password_confirm', [''])[0]
                
                # For PostgreSQL fields
                postgres_host = form_data.get('postgres_host', ['localhost'])[0]
                postgres_port = form_data.get('postgres_port', ['5432'])[0]
                postgres_db = form_data.get('postgres_db', ['botsdb'])[0]
                postgres_user = form_data.get('postgres_user', ['bots'])[0]
                postgres_password = form_data.get('postgres_password', [''])[0]
            
            # Debug password lengths
            print(f"DEBUG: admin_password='{admin_password}', length={len(admin_password)}")
            print(f"DEBUG: admin_password_confirm='{admin_password_confirm}', length={len(admin_password_confirm)}")
            
            # Validate passwords match
            if admin_password != admin_password_confirm:
                self.send_error_response("Passwords do not match!")
                return
            
            # Validate password length
            if not admin_password or len(admin_password.strip()) < 8:
                self.send_error_response(f"Password must be at least 8 characters long! Current length: {len(admin_password.strip())}")
                return
            
            # Setup database configuration
            db_config = {'type': db_type}
            
            if db_type == 'postgres':
                db_config.update({
                    'host': postgres_host,
                    'port': int(postgres_port),
                    'database': postgres_db,
                    'user': postgres_user,
                    'password': postgres_password
                })
                
                # Test PostgreSQL connection
                if not self.test_postgres_connection(db_config):
                    self.send_error_response("Failed to connect to PostgreSQL database. Please check your settings.")
                    return
            
            # Save database configuration
            self.save_database_config(db_config)
            
            # Initialize database and create admin user
            if self.initialize_system(db_config, admin_username, admin_email, admin_password):
                # Mark setup as complete
                with open('/app/.bots_setup_complete', 'w') as f:
                    f.write('setup completed successfully')
                
                self.send_success_response("Setup completed successfully! You can now log in with your admin credentials.")
            else:
                self.send_error_response("Failed to initialize the system. Please check the logs.")
                
        except Exception as e:
            print(f"ERROR: Setup failed with exception: {str(e)}")
            import traceback
            traceback.print_exc()
            self.send_error_response(f"Setup failed: {str(e)}")
    
    def test_postgres_connection(self, db_config):
        """Test PostgreSQL connection"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password']
            )
            conn.close()
            return True
        except Exception:
            return False
    
    def save_database_config(self, db_config):
        """Save database configuration"""
        with open('/app/bots_database_config.json', 'w') as f:
            json.dump(db_config, f, indent=2)
    
    def initialize_system(self, db_config, admin_username, admin_email, admin_password):
        """Initialize the Bots system with the chosen database"""
        try:
            # Set environment variables based on database type
            if db_config['type'] == 'postgres':
                os.environ['BOTS_DB_ENGINE'] = 'postgres'
                os.environ['POSTGRES_HOST'] = db_config['host']
                os.environ['POSTGRES_PORT'] = str(db_config['port'])
                os.environ['POSTGRES_DB'] = db_config['database']
                os.environ['POSTGRES_USER'] = db_config['user']
                os.environ['POSTGRES_PASSWORD'] = db_config['password']
            else:
                os.environ['BOTS_DB_ENGINE'] = 'sqlite'
                # Ensure SQLite directory exists
                os.makedirs('/app/bots/botssys/sqlitedb', exist_ok=True)
            
            # Import Django and setup
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bots.config.settings')
            import django
            django.setup()
            
            # Run migrations
            from django.core.management import execute_from_command_line
            execute_from_command_line(['manage.py', 'migrate'])
            
            # Create admin user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            if not User.objects.filter(username=admin_username).exists():
                User.objects.create_superuser(admin_username, admin_email, admin_password)
            
            # Create routeschedule table if using SQLite
            if db_config['type'] == 'sqlite':
                self.create_routeschedule_table()
            
            return True
            
        except Exception as e:
            print(f"Initialization error: {e}")
            return False
    
    def create_routeschedule_table(self):
        """Create routeschedule table for SQLite"""
        try:
            db_path = '/app/bots/botssys/sqlitedb/botsdb'
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='routeschedule'")
                if not cursor.fetchone():
                    create_sql = '''
                        CREATE TABLE routeschedule (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name VARCHAR(100) NOT NULL,
                            route_id VARCHAR(35) NOT NULL,
                            active BOOLEAN DEFAULT 1,
                            frequency VARCHAR(20) DEFAULT 'daily',
                            interval INTEGER DEFAULT 1,
                            time_hour INTEGER NULL,
                            time_minute INTEGER DEFAULT 0,
                            weekday VARCHAR(20) NULL,
                            day_of_month INTEGER NULL,
                            created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                            modified_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                            last_run DATETIME NULL,
                            next_run DATETIME NULL,
                            enabled_only_weekdays BOOLEAN DEFAULT 0,
                            max_retries INTEGER DEFAULT 3
                        )
                    '''
                    cursor.execute(create_sql)
                    conn.commit()
                
                conn.close()
        except Exception as e:
            print(f"Error creating routeschedule table: {e}")
    
    def send_success_response(self, message):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        response = f'<div class="info">{message}</div>'
        self.wfile.write(response.encode())
    
    def send_error_response(self, message):
        self.send_response(400)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        response = f'<div class="error">{message}</div>'
        self.wfile.write(response.encode())

def run_setup_server():
    """Run the setup server"""
    # Use port 9000 which is mapped in docker-compose
    port = 9000
    
    # Make sure output is flushed immediately
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    
    server = HTTPServer(('0.0.0.0', port), SetupHandler)
    print(f"🚀 Bots EDI First-Time Setup", flush=True)
    print(f"📋 Open your browser and go to: http://localhost:{port}", flush=True)
    print(f"⏹️  Press Ctrl+C to stop the setup server", flush=True)
    print("", flush=True)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\n🛑 Setup server stopped", flush=True)
        server.shutdown()

if __name__ == '__main__':
    # Check if setup is already complete
    if os.path.exists('/app/.bots_setup_complete'):
        print("✅ Bots EDI setup is already complete!")
        print("🌐 Access the system at: http://localhost:8080")
        sys.exit(0)
    
    run_setup_server()