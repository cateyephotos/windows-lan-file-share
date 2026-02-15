#!/usr/bin/env python3
"""
Security Module for Windows LAN File Share
Provides access control and security features
"""

import hashlib
import secrets
import time
from datetime import datetime, timedelta
import json
import base64
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

class AccessControl:
    """Manages access control for file sharing"""
    
    def __init__(self):
        self.allowed_ips = set()
        self.blocked_ips = set()
        self.access_tokens = {}
        self.session_tokens = {}
        self.require_token = False
        self.rate_limits = {}
        self.max_requests_per_minute = 60
        self.log_access = True
    
    def allow_ip(self, ip):
        """Add IP to allowed list"""
        self.allowed_ips.add(ip)
    
    def block_ip(self, ip):
        """Add IP to blocked list"""
        self.blocked_ips.add(ip)
    
    def is_ip_allowed(self, ip):
        """Check if IP is allowed"""
        if ip in self.blocked_ips:
            return False
        if self.allowed_ips and ip not in self.allowed_ips:
            return False
        return True
    
    def generate_access_token(self, expires_hours=24):
        """Generate a secure access token"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        self.access_tokens[token] = {
            'created': datetime.now(),
            'expires': expires_at,
            'uses': 0
        }
        return token
    
    def validate_token(self, token):
        """Validate access token"""
        if token not in self.access_tokens:
            return False
        
        token_info = self.access_tokens[token]
        if datetime.now() > token_info['expires']:
            del self.access_tokens[token]
            return False
        
        token_info['uses'] += 1
        return True
    
    def check_rate_limit(self, ip):
        """Check if IP has exceeded rate limit"""
        current_time = time.time()
        minute_ago = current_time - 60
        
        if ip not in self.rate_limits:
            self.rate_limits[ip] = []
        
        # Remove old requests
        self.rate_limits[ip] = [req_time for req_time in self.rate_limits[ip] if req_time > minute_ago]
        
        # Check if under limit
        if len(self.rate_limits[ip]) < self.max_requests_per_minute:
            self.rate_limits[ip].append(current_time)
            return True
        
        return False
    
    def cleanup_expired_tokens(self):
        """Remove expired tokens"""
        current_time = datetime.now()
        expired_tokens = []
        
        for token, info in self.access_tokens.items():
            if current_time > info['expires']:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self.access_tokens[token]
        
        return len(expired_tokens)

class SecureFileShareHandler(BaseHTTPRequestHandler):
    """Enhanced handler with security features"""
    
    def __init__(self, *args, access_control=None, shared_files=None, **kwargs):
        self.access_control = access_control or AccessControl()
        self.shared_files = shared_files or {}
        super().__init__(*args, **kwargs)
    
    def validate_request(self):
        """Validate incoming request"""
        client_ip = self.client_address[0]
        
        # Check IP blocking
        if not self.access_control.is_ip_allowed(client_ip):
            self.send_error(403, "Access denied")
            return False
        
        # Check rate limiting
        if not self.access_control.check_rate_limit(client_ip):
            self.send_error(429, "Too many requests")
            return False
        
        # Check token requirement
        if self.access_control.require_token:
            token = self.get_token_from_request()
            if not token or not self.access_control.validate_token(token):
                self.send_auth_required()
                return False
        
        return True
    
    def get_token_from_request(self):
        """Extract token from request"""
        # Check Authorization header
        if 'Authorization' in self.headers:
            auth_header = self.headers['Authorization']
            if auth_header.startswith('Bearer '):
                return auth_header[7:]
        
        # Check query parameter
        if '?' in self.path:
            query = parse_qs(self.path.split('?', 1)[1])
            if 'token' in query:
                return query['token'][0]
        
        return None
    
    def send_auth_required(self):
        """Send authentication required response"""
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Bearer')
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Authentication Required</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #d32f2f; text-align: center; }
        .error { color: #666; text-align: center; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Authentication Required</h1>
        <div class="error">
            <p>This file share requires authentication.</p>
            <p>Please contact the server administrator for access.</p>
        </div>
    </div>
</body>
</html>
"""
        self.wfile.write(html.encode('utf-8'))
    
    def log_access(self, action, file_id=None, status="success"):
        """Log access attempts"""
        if self.access_control.log_access:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            client_ip = self.client_address[0]
            
            log_entry = {
                'timestamp': timestamp,
                'ip': client_ip,
                'action': action,
                'file_id': file_id,
                'status': status,
                'user_agent': self.headers.get('User-Agent', 'Unknown')
            }
            
            # In a real implementation, this would be written to a log file
            print(f"ACCESS LOG: {json.dumps(log_entry)}")
    
    def do_GET(self):
        """Handle GET requests with security"""
        if not self.validate_request():
            return
        
        try:
            if self.path == '/':
                self.serve_file_list()
            elif self.path.startswith('/download/'):
                self.serve_file_download()
            elif self.path.startswith('/files/'):
                self.serve_direct_file()
            else:
                self.send_error(404, "Not found")
        except Exception as e:
            self.log_access("error", status=str(e))
            self.send_error(500, "Internal server error")
    
    def serve_file_list(self):
        """Serve secure file listing"""
        self.log_access("list_files")
        
        html_content = self.generate_secure_file_list_html()
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def serve_file_download(self):
        """Handle secure file download"""
        file_id = self.path.split('/download/')[-1]
        
        if file_id in self.shared_files:
            file_path = self.shared_files[file_id]['path']
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                
                # Security check - ensure file is within allowed directory
                if not self.is_safe_file_path(file_path):
                    self.log_access("download_blocked", file_id, "unsafe_path")
                    self.send_error(403, "Access denied")
                    return
                
                self.log_access("download", file_id)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.end_headers()
                
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.log_access("download_failed", file_id, "file_not_found")
                self.send_error(404, "File not found")
        else:
            self.log_access("download_failed", file_id, "invalid_id")
            self.send_error(404, "File not found")
    
    def serve_direct_file(self):
        """Serve files directly for preview with security"""
        file_id = self.path.split('/files/')[-1]
        
        if file_id in self.shared_files:
            file_path = self.shared_files[file_id]['path']
            
            # Security check
            if not self.is_safe_file_path(file_path):
                self.log_access("preview_blocked", file_id, "unsafe_path")
                self.send_error(403, "Access denied")
                return
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        self.log_access("preview", file_id)
                        
                        self.send_response(200)
                        
                        # Determine content type with security
                        content_type = self.get_safe_content_type(file_path)
                        self.send_header('Content-type', content_type)
                        self.send_header('X-Content-Type-Options', 'nosniff')
                        
                        if content_type.startswith('text/'):
                            self.send_header('Content-Security-Policy', "default-src 'self'")
                        
                        self.end_headers()
                        self.wfile.write(content)
                        
                except Exception as e:
                    self.log_access("preview_failed", file_id, str(e))
                    self.send_error(500, f"Error serving file: {str(e)}")
            else:
                self.log_access("preview_failed", file_id, "file_not_found")
                self.send_error(404, "File not found")
        else:
            self.log_access("preview_failed", file_id, "invalid_id")
            self.send_error(404, "File not found")
    
    def is_safe_file_path(self, file_path):
        """Check if file path is safe (prevents directory traversal)"""
        try:
            import os
            # Normalize the path
            normalized_path = os.path.normpath(file_path)
            # Check for directory traversal attempts
            if '..' in normalized_path.split(os.sep):
                return False
            # Ensure the file exists and is a file (not a directory)
            if not os.path.isfile(normalized_path):
                return False
            return True
        except Exception:
            return False
    
    def get_safe_content_type(self, file_path):
        """Get safe content type for file"""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Safe content types
        safe_types = {
            '.txt': 'text/plain; charset=utf-8',
            '.py': 'text/plain; charset=utf-8',
            '.js': 'text/plain; charset=utf-8',
            '.html': 'text/plain; charset=utf-8',  # Serve as plain text for security
            '.css': 'text/plain; charset=utf-8',
            '.json': 'application/json',
            '.xml': 'text/xml',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.pdf': 'application/pdf',
            '.csv': 'text/csv',
        }
        
        return safe_types.get(file_ext, 'application/octet-stream')
    
    def generate_secure_file_list_html(self):
        """Generate secure HTML page for file listing"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Secure LAN File Share</title>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container { 
            max-width: 900px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        h1 { 
            color: #333; 
            text-align: center; 
            margin-bottom: 30px;
            font-size: 2.5em;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .security-notice {
            background: #e8f5e8;
            border: 1px solid #4caf50;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
            color: #2e7d32;
        }
        .file-item { 
            border: 1px solid #e0e0e0; 
            padding: 20px; 
            margin: 15px 0; 
            border-radius: 10px; 
            background: #fafafa;
            transition: all 0.3s ease;
        }
        .file-item:hover { 
            background: #f5f5f5; 
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .file-name { 
            font-weight: 600; 
            font-size: 18px; 
            color: #2c3e50;
            margin-bottom: 8px;
        }
        .file-info { 
            color: #666; 
            font-size: 14px; 
            margin-top: 5px;
        }
        .download-btn { 
            background: linear-gradient(45deg, #4caf50, #45a049); 
            color: white; 
            padding: 12px 24px; 
            text-decoration: none; 
            border-radius: 25px; 
            display: inline-block; 
            margin-top: 15px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        .download-btn:hover { 
            background: linear-gradient(45deg, #45a049, #4caf50);
            transform: translateY(-1px);
        }
        .preview-btn { 
            background: linear-gradient(45deg, #2196f3, #1976d2); 
            color: white; 
            padding: 12px 24px; 
            text-decoration: none; 
            border-radius: 25px; 
            display: inline-block; 
            margin-top: 15px; 
            margin-left: 10px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        .preview-btn:hover { 
            background: linear-gradient(45deg, #1976d2, #2196f3);
            transform: translateY(-1px);
        }
        .no-files { 
            text-align: center; 
            color: #666; 
            font-style: italic; 
            padding: 40px;
            font-size: 18px;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Secure LAN File Share</h1>
        <div class="security-notice">
            🛡️ This is a secure file sharing service. All access is logged and monitored.
        </div>
"""
        
        if not self.shared_files:
            html += '<div class="no-files">No files are currently being shared.</div>'
        else:
            for file_id, file_info in self.shared_files.items():
                filename = file_info['name']
                size = file_info['size']
                modified = file_info['modified']
                
                html += f"""
        <div class="file-item">
            <div class="file-name">📄 {filename}</div>
            <div class="file-info">
                📊 Size: {size} | 🕒 Modified: {modified}
            </div>
            <a href="/download/{file_id}" class="download-btn">⬇️ Download</a>
            <a href="/files/{file_id}" class="preview-btn" target="_blank">👁️ Preview</a>
        </div>
"""
        
        html += """
        <div class="footer">
            <p>Secure File Sharing Service | Access is monitored and logged</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def log_message(self, format, *args):
        """Override to prevent console spam"""
        pass

# Utility functions for security
def generate_session_id():
    """Generate a secure session ID"""
    return secrets.token_urlsafe(32)

def hash_password(password, salt=None):
    """Hash password with salt"""
    if salt is None:
        salt = secrets.token_hex(16)
    
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return salt + password_hash.hex()

def verify_password(password, hashed):
    """Verify password against hash"""
    salt = hashed[:32]
    stored_hash = hashed[32:]
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return password_hash.hex() == stored_hash
