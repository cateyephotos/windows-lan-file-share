#!/usr/bin/env python3
"""
Windows LAN File Sharing Utility
Share and download files over WiFi-LAN with other Windows machines
"""

import os
import sys
import socket
import threading
import json
import subprocess
import re
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import webbrowser
from datetime import datetime
import uuid
from discovery import NetworkDiscovery, create_discovery_integration
from security import AccessControl, SecureFileShareHandler
from client import FileShareClient, RemoteServerBrowser, create_client_integration
from config import get_chunk_size, validate_file_size, format_file_size, CONFIG, load_config_from_file
from fast_transfer import OptimizedHTTPServer, should_use_multithread, calculate_optimal_threads, MultiThreadedDownloader, SpeedMonitor
from settings_ui import open_settings
from file_verification import FileVerifier, verify_download

class FileShareHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for file sharing"""

    connection_callback = None  # Class variable for connection notifications
    _template_cache = None  # Cache for static file template

    # MIME type map for file preview serving
    CONTENT_TYPE_MAP = {
        # Text / Code
        '.txt': 'text/plain', '.py': 'text/plain', '.js': 'text/plain',
        '.html': 'text/plain', '.css': 'text/plain', '.json': 'text/plain',
        '.xml': 'text/plain', '.md': 'text/plain', '.yaml': 'text/plain',
        '.yml': 'text/plain', '.toml': 'text/plain', '.ini': 'text/plain',
        '.cfg': 'text/plain', '.conf': 'text/plain',
        '.c': 'text/plain', '.cpp': 'text/plain', '.h': 'text/plain',
        '.hpp': 'text/plain', '.java': 'text/plain', '.go': 'text/plain',
        '.rs': 'text/plain', '.rb': 'text/plain', '.php': 'text/plain',
        '.sh': 'text/plain', '.bat': 'text/plain', '.ps1': 'text/plain',
        '.ts': 'text/plain', '.tsx': 'text/plain', '.jsx': 'text/plain',
        '.vue': 'text/plain', '.svelte': 'text/plain',
        '.csv': 'text/plain', '.log': 'text/plain', '.sql': 'text/plain',
        '.r': 'text/plain', '.swift': 'text/plain', '.kt': 'text/plain',
        '.scala': 'text/plain', '.pl': 'text/plain', '.lua': 'text/plain',
        # Images
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.gif': 'image/gif',
        '.webp': 'image/webp', '.svg': 'image/svg+xml',
        '.bmp': 'image/bmp', '.ico': 'image/x-icon',
        # Video
        '.mp4': 'video/mp4', '.webm': 'video/webm',
        '.ogg': 'video/ogg', '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo', '.mkv': 'video/x-matroska',
        # Audio
        '.mp3': 'audio/mpeg', '.wav': 'audio/wav',
        '.flac': 'audio/flac', '.aac': 'audio/aac',
        '.m4a': 'audio/mp4', '.wma': 'audio/x-ms-wma',
        # Documents
        '.pdf': 'application/pdf',
    }

    def __init__(self, *args, shared_files=None, **kwargs):
        self.shared_files = shared_files or {}
        super().__init__(*args, **kwargs)

    @classmethod
    def _get_content_type(cls, file_path):
        """Get MIME content type for a file based on its extension"""
        ext = os.path.splitext(file_path)[1].lower()
        return cls.CONTENT_TYPE_MAP.get(ext, 'application/octet-stream')
    
    def log_message(self, format, *args):
        """Override to capture connection events"""
        # Call parent to maintain normal logging
        super().log_message(format, *args)
        
        # Notify about connections
        if self.connection_callback and args:
            client_ip = self.client_address[0]
            request_line = args[0] if len(args) > 0 else ""
            
            # Parse request to get action
            if 'GET /' in request_line and 'HTTP' in request_line:
                if '/download/' in request_line:
                    action = "downloading file"
                elif request_line.strip() == 'GET / HTTP/1.1' or request_line.strip() == 'GET / HTTP/1.0':
                    action = "browsing files"
                else:
                    action = "accessing server"
                
                self.connection_callback(client_ip, action, request_line)
    
    def do_GET(self):
        if self.path == '/':
            self.serve_file_list()
        elif self.path == '/api/files':
            self.serve_file_list_json()
        elif self.path.startswith('/download/'):
            self.serve_file_download()
        elif self.path.startswith('/files/'):
            self.serve_direct_file()
        else:
            super().do_GET()
    
    def do_HEAD(self):
        """Handle HEAD requests — return headers only, no body"""
        if self.path == '/':
            html_content = self.generate_file_list_html()
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Content-Length', str(len(html_content.encode('utf-8'))))
            self.end_headers()
        elif self.path.startswith('/download/'):
            file_id = self.path.split('/download/')[-1]
            if file_id in self.shared_files:
                file_path = self.shared_files[file_id]['path']
                if os.path.exists(file_path):
                    filename = os.path.basename(file_path)
                    file_size = os.path.getsize(file_path)
                    self.send_response(200)
                    self.send_header('Content-type', 'application/octet-stream')
                    self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                    self.send_header('Content-Length', str(file_size))
                    self.send_header('Accept-Ranges', 'bytes')
                    self.end_headers()
                else:
                    self.send_error(404, "File not found")
            else:
                self.send_error(404, "File not found")
        elif self.path.startswith('/files/'):
            file_id = self.path.split('/files/')[-1]
            if file_id in self.shared_files:
                file_path = self.shared_files[file_id]['path']
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    self.send_response(200)
                    self.send_header('Content-type', self._get_content_type(file_path))
                    self.send_header('Content-Length', str(file_size))
                    self.end_headers()
                else:
                    self.send_error(404, "File not found")
            else:
                self.send_error(404, "File not found")
        else:
            super().do_HEAD()
    
    def serve_file_list(self):
        """Serve the file list page"""
        html = self.generate_file_list_html()
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-Length', str(len(html.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_file_list_json(self):
        """Serve file list as JSON for API clients"""
        import json
        
        # Build file list
        files = []
        for file_id, file_info in self.shared_files.items():
            files.append({
                'id': file_id,
                'name': file_info.get('basename', file_info['name']),
                'size': file_info['size'],
                'size_bytes': file_info['size_bytes'],
                'modified': file_info['modified'],
                'folder': file_info.get('folder', ''),
                'extension': file_info.get('extension', '')
            })
        
        json_data = json.dumps(files, indent=2)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-Length', str(len(json_data.encode('utf-8'))))
        self.send_header('Access-Control-Allow-Origin', '*')  # Allow CORS
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))
    
    def serve_file_download(self):
        """Handle file download requests with chunked transfer and Range support for multi-threading"""
        file_id = self.path.split('/download/')[-1]
        if file_id in self.shared_files:
            file_path = self.shared_files[file_id]['path']
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                
                # Notify about file download
                if self.connection_callback:
                    client_ip = self.client_address[0]
                    self.connection_callback(client_ip, "download_start", f"Downloading: {filename}")
                
                # Check for Range header (for multi-threaded downloads)
                range_header = self.headers.get('Range')
                
                if range_header:
                    # Parse range header
                    try:
                        byte_range = range_header.replace('bytes=', '').split('-')
                        start = int(byte_range[0]) if byte_range[0] else 0
                        end = int(byte_range[1]) if byte_range[1] else file_size - 1
                        
                        # Validate range
                        if start >= file_size or end >= file_size or start > end:
                            self.send_error(416, "Requested Range Not Satisfiable")
                            return
                        
                        content_length = end - start + 1
                        
                        # Send partial content response
                        self.send_response(206)
                        self.send_header('Content-type', 'application/octet-stream')
                        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                        self.send_header('Content-Length', str(content_length))
                        self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                        self.send_header('Accept-Ranges', 'bytes')
                        self.end_headers()
                        
                        # Send requested byte range
                        with open(file_path, 'rb') as f:
                            f.seek(start)
                            remaining = content_length
                            chunk_size = get_chunk_size(content_length)
                            
                            while remaining > 0:
                                read_size = min(chunk_size, remaining)
                                chunk = f.read(read_size)
                                if not chunk:
                                    break
                                try:
                                    self.wfile.write(chunk)
                                    remaining -= len(chunk)
                                except (BrokenPipeError, ConnectionResetError):
                                    break
                    except (ValueError, IndexError):
                        self.send_error(400, "Invalid Range header")
                        return
                else:
                    # Normal full file download
                    self.send_response(200)
                    self.send_header('Content-type', 'application/octet-stream')
                    self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                    self.send_header('Content-Length', str(file_size))
                    self.send_header('Accept-Ranges', 'bytes')
                    self.end_headers()
                    
                    # Use chunked transfer for efficient memory usage
                    chunk_size = get_chunk_size(file_size)
                    with open(file_path, 'rb') as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            try:
                                self.wfile.write(chunk)
                            except (BrokenPipeError, ConnectionResetError):
                                # Client disconnected
                                break
            else:
                self.send_error(404, "File not found")
        else:
            self.send_error(404, "File not found")
    
    def serve_direct_file(self):
        """Serve files directly for preview"""
        file_id = self.path.split('/files/')[-1]
        if file_id in self.shared_files:
            file_path = self.shared_files[file_id]['path']
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        self.send_response(200)
                        self.send_header('Content-type', self._get_content_type(file_path))
                        self.end_headers()
                        self.wfile.write(content)
                except Exception as e:
                    self.send_error(500, f"Error serving file: {str(e)}")
            else:
                self.send_error(404, "File not found")
        else:
            self.send_error(404, "File not found")
    
    def generate_file_list_html(self):
        """Generate enhanced HTML page with filtering and folder navigation"""

        # Build folder structure
        folders = set()
        for file_info in self.shared_files.values():
            if file_info.get('folder'):
                folders.add(file_info['folder'])
                # Add parent folders
                parts = file_info['folder'].split('/')
                for i in range(1, len(parts)):
                    folders.add('/'.join(parts[:i]))

        # Convert files to JSON for JavaScript
        files_json = json.dumps([{
            'id': f['id'],
            'name': f.get('basename', f['name']),
            'fullPath': f['name'],
            'folder': f.get('folder', ''),
            'extension': f.get('extension', ''),
            'size': f['size'],
            'sizeBytes': f['size_bytes'],
            'modified': f['modified']
        } for f in self.shared_files.values()])

        folders_json = json.dumps(sorted(list(folders)))

        # Load and cache static template files
        if FileShareHandler._template_cache is None:
            static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
            try:
                with open(os.path.join(static_dir, 'index.html'), 'r', encoding='utf-8') as f:
                    html_template = f.read()
                with open(os.path.join(static_dir, 'style.css'), 'r', encoding='utf-8') as f:
                    css_content = f.read()
                with open(os.path.join(static_dir, 'app.js'), 'r', encoding='utf-8') as f:
                    js_content = f.read()
                # Inline CSS and JS into the HTML template
                html_template = html_template.replace('/* __STYLE_CSS__ */', css_content)
                html_template = html_template.replace('/* __APP_JS__ */', js_content)
                FileShareHandler._template_cache = html_template
            except (FileNotFoundError, OSError, IOError) as e:
                # Return a user-friendly error page if static files are missing or unreadable
                import html as html_mod
                return f"""<!DOCTYPE html>
<html><head><title>Configuration Error</title></head>
<body style="font-family: sans-serif; padding: 40px; text-align: center;">
<h1>Configuration Error</h1>
<p>Required static files are missing from the <code>static/</code> directory.</p>
<p>Please ensure these files exist: static/index.html, static/style.css, static/app.js</p>
<p style="color: #666; font-size: 12px;">Error: {html_mod.escape(str(e))}</p>
</body></html>"""

        # Sanitize JSON for safe embedding inside <script> tags.
        # A filename containing "</script>" would break out of the script block,
        # enabling XSS. Escaping "</" to "<\\/" is the standard mitigation.
        files_json = files_json.replace('</', '<\\/')
        folders_json = folders_json.replace('</', '<\\/')

        # Substitute data placeholders using regex single-pass replacement to prevent
        # injection attacks where filenames contain placeholder strings like __FOLDERS_JSON__
        html = FileShareHandler._template_cache
        substitutions = {
            '__FILES_JSON__': files_json,
            '__FOLDERS_JSON__': folders_json
        }
        # Build regex pattern that matches any placeholder
        pattern = re.compile('|'.join(re.escape(k) for k in substitutions.keys()))
        # Single-pass replacement using a function - each placeholder is replaced only once
        # and already-substituted content cannot affect subsequent matches
        html = pattern.sub(lambda m: substitutions[m.group(0)], html)

        return html
    
    def log_message(self, format, *args):
        """Override to prevent console spam"""
        pass

class LANFileShareApp:
    """Main application class"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Windows LAN File Share")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        self.server = None
        self.server_thread = None
        self.shared_files = {}
        self.is_server_running = False
        self.port = 8000
        self.port_range = range(8000, 8010)  # Try ports 8000-8009 if needed
        self.discovery = None
        self.access_control = AccessControl()
        self.use_security = False
        self.client = None
        self.browser = None
        self.current_remote_server = None
        # Load download directory from config or use default
        self.download_save_dir = self.load_download_directory()
        self.connected_clients = {}  # Track connected clients
        self.connection_history = []  # Store connection history
        self.config_file = os.path.join(os.path.expanduser("~"), ".lanfileshare_shared.json")
        
        self.setup_gui()
        self.get_local_ip()
        self.setup_discovery()
        self.setup_client()
        
        # Load previously shared files/folders
        self.load_shared_config()
    
    def setup_gui(self):
        """Setup the GUI interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Windows LAN File Share", font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Server Status Frame
        status_frame = ttk.LabelFrame(main_frame, text="Server Status", padding="10")
        status_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.status_label = ttk.Label(status_frame, text="Server: Stopped", foreground="red")
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.ip_label = ttk.Label(status_frame, text="IP: Not available")
        self.ip_label.grid(row=1, column=0, sticky=tk.W)
        
        self.port_label = ttk.Label(status_frame, text=f"Port: {self.port}")
        self.port_label.grid(row=2, column=0, sticky=tk.W)
        
        self.connections_label = ttk.Label(status_frame, text="Active Connections: 0", foreground="blue")
        self.connections_label.grid(row=3, column=0, sticky=tk.W)
        
        # Server Control Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=(0, 20))
        
        self.start_button = ttk.Button(button_frame, text="Start Server", command=self.start_server)
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="Stop Server", command=self.stop_server, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=(0, 10))
        
        self.open_browser_button = ttk.Button(button_frame, text="Open in Browser", command=self.open_in_browser, state=tk.DISABLED)
        self.open_browser_button.grid(row=0, column=2, padx=(0, 10))
        
        ttk.Button(button_frame, text="⚙️ Settings", command=self.open_settings).grid(row=0, column=3, padx=(0, 10))
        
        self.security_var = tk.BooleanVar()
        self.security_check = ttk.Checkbutton(button_frame, text="Enable Security", variable=self.security_var, command=self.toggle_security)
        self.security_check.grid(row=0, column=4)
        
        # File Management Frame
        file_frame = ttk.LabelFrame(main_frame, text="File Management", padding="10")
        file_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        
        # File selection
        ttk.Button(file_frame, text="Add Files", command=self.add_files).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(file_frame, text="Add Folder", command=self.add_folder).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(file_frame, text="Remove Selected", command=self.remove_selected).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(file_frame, text="Clear All", command=self.clear_all).grid(row=0, column=3)
        
        # File list
        columns = ('Name', 'Size', 'Modified')
        self.file_tree = ttk.Treeview(file_frame, columns=columns, show='tree headings', height=10)
        
        for col in columns:
            self.file_tree.heading(col, text=col)
            self.file_tree.column(col, width=200)
        
        self.file_tree.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        # Scrollbar for file list
        scrollbar = ttk.Scrollbar(file_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        scrollbar.grid(row=1, column=3, sticky=(tk.N, tk.S), pady=(10, 0))
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        
        # Log Frame
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="10")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Network Discovery Frame
        discovery_frame = ttk.LabelFrame(main_frame, text="Discovered Servers", padding="10")
        discovery_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        # Discovered servers list
        columns = ('IP', 'Port', 'URL', 'Last Seen')
        self.discovery_tree = ttk.Treeview(discovery_frame, columns=columns, show='tree headings', height=6)
        
        for col in columns:
            self.discovery_tree.heading(col, text=col)
            if col == 'URL':
                self.discovery_tree.column(col, width=300)
            else:
                self.discovery_tree.column(col, width=100)
        
        self.discovery_tree.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Discovery buttons
        ttk.Button(discovery_frame, text="Refresh", command=self.refresh_discovery).grid(row=1, column=0, pady=(5, 0), padx=(0, 5))
        ttk.Button(discovery_frame, text="Open in Browser", command=self.connect_to_server).grid(row=1, column=1, pady=(5, 0), padx=(0, 5))
        ttk.Button(discovery_frame, text="Browse & Download", command=self.browse_remote_server).grid(row=1, column=2, pady=(5, 0))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(4, weight=1)
        main_frame.rowconfigure(5, weight=1)
        file_frame.columnconfigure(0, weight=1)
        file_frame.rowconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        discovery_frame.columnconfigure(0, weight=1)
        discovery_frame.rowconfigure(0, weight=1)
    
    def toggle_security(self):
        """Toggle security mode"""
        self.use_security = self.security_var.get()
        if self.use_security:
            self.log("Security mode enabled - access control and logging active")
            # Generate access token for immediate use
            token = self.access_control.generate_access_token()
            self.log(f"Access token generated: {token}")
            messagebox.showinfo("Security Enabled", f"Security mode enabled.\n\nAccess token: {token}\n\nThis token can be used to access the server.")
        else:
            self.log("Security mode disabled")
    
    def setup_discovery(self):
        """Setup network discovery"""
        try:
            self.discovery = create_discovery_integration(self)
            self.discovery.start_discovery()
            self.log("Network discovery started")
        except Exception as e:
            self.log(f"Failed to start network discovery: {e}")
    
    def update_discovered_servers(self, servers):
        """Update the discovered servers list"""
        # Clear existing items
        for item in self.discovery_tree.get_children():
            self.discovery_tree.delete(item)
        
        # Add discovered servers
        for server_key, server_info in servers.items():
            last_seen = datetime.fromtimestamp(server_info['last_seen']).strftime('%H:%M:%S')
            self.discovery_tree.insert('', 'end', iid=server_key, values=(
                server_info['ip'],
                server_info['port'],
                server_info['url'],
                last_seen
            ))
    
    def refresh_discovery(self):
        """Refresh network discovery"""
        if self.discovery:
            self.discovery.cleanup_old_servers()
            self.discovery.trigger_manual_scan()
            self.log("Scanning network for servers...")
    
    def connect_to_server(self):
        """Connect to selected discovered server"""
        selected = self.discovery_tree.selection()
        if selected:
            server_key = selected[0]
            if self.discovery and server_key in self.discovery.discovered_servers:
                server_info = self.discovery.discovered_servers[server_key]
                url = server_info['url']
                webbrowser.open(url)
                self.log(f"Opening {url} in browser")
        else:
            messagebox.showinfo("No Selection", "Please select a server to connect to.")
    
    def browse_remote_server(self):
        """Browse and download files from a remote server"""
        selected = self.discovery_tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select a server to browse.")
            return
        
        server_key = selected[0]
        if self.discovery and server_key in self.discovery.discovered_servers:
            server_info = self.discovery.discovered_servers[server_key]
            url = server_info['url']
            self.current_remote_server = url
            self.show_remote_browser_window(url)
        else:
            messagebox.showinfo("No Selection", "Please select a server to browse.")
    
    def show_remote_browser_window(self, server_url):
        """Show window for browsing remote server files"""
        # Create new window
        browser_window = tk.Toplevel(self.root)
        browser_window.title(f"Browse Remote Server - {server_url}")
        browser_window.geometry("700x500")
        
        # Main frame
        main_frame = ttk.Frame(browser_window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Server info
        ttk.Label(main_frame, text=f"Server: {server_url}", font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Refresh button
        ttk.Button(main_frame, text="Refresh File List", command=lambda: self.refresh_remote_files(server_url, file_tree)).grid(row=1, column=0, pady=(0, 10))
        
        # Download location
        ttk.Label(main_frame, text="Download to:").grid(row=1, column=1, padx=(20, 5))
        download_dir_var = tk.StringVar(value=self.download_save_dir)
        download_entry = ttk.Entry(main_frame, textvariable=download_dir_var, width=25)
        download_entry.grid(row=1, column=2)
        ttk.Button(main_frame, text="Browse...", 
                  command=lambda: self.browse_download_directory(download_dir_var)).grid(row=1, column=3, padx=(5, 0))
        
        # File list
        columns = ('Name', 'Size', 'Modified')
        file_tree = ttk.Treeview(main_frame, columns=columns, show='tree headings', height=15)
        
        for col in columns:
            file_tree.heading(col, text=col)
            if col == 'Name':
                file_tree.column(col, width=300)
            else:
                file_tree.column(col, width=150)
        
        file_tree.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=file_tree.yview)
        scrollbar.grid(row=2, column=3, sticky=(tk.N, tk.S), pady=(0, 10))
        file_tree.configure(yscrollcommand=scrollbar.set)
        
        # Download buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3)
        
        ttk.Button(button_frame, text="Download Selected", 
                  command=lambda: self.download_selected_files(server_url, file_tree, download_dir_var.get())).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text="Download All", 
                  command=lambda: self.download_all_files(server_url, file_tree, download_dir_var.get())).grid(row=0, column=1)
        
        # Status label
        status_label = ttk.Label(main_frame, text="Loading files...", foreground="blue")
        status_label.grid(row=4, column=0, columnspan=3, pady=(10, 0))
        
        # Configure grid weights
        browser_window.columnconfigure(0, weight=1)
        browser_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Load files
        self.load_remote_files(server_url, file_tree, status_label)
    
    def load_remote_files(self, server_url, file_tree, status_label):
        """Load files from remote server"""
        def load_thread():
            try:
                status_label.config(text="Loading files...", foreground="blue")
                files = self.browser.browse_server(server_url)
                
                # Update tree view
                self.root.after(0, lambda: self.populate_remote_file_tree(file_tree, files, status_label))
                
            except Exception as e:
                error_msg = f"Error loading files: {str(e)}"
                self.root.after(0, lambda: status_label.config(text=error_msg, foreground="red"))
                self.log(error_msg)
        
        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()
    
    def populate_remote_file_tree(self, file_tree, files, status_label):
        """Populate tree view with remote files"""
        # Clear existing items
        for item in file_tree.get_children():
            file_tree.delete(item)
        
        # Add files
        for file_info in files:
            file_tree.insert('', 'end', iid=file_info['id'], values=(
                file_info['name'],
                file_info['size'],
                file_info['modified']
            ))
        
        status_label.config(text=f"Loaded {len(files)} file(s)", foreground="green")
    
    def refresh_remote_files(self, server_url, file_tree):
        """Refresh remote file list"""
        status_label = ttk.Label(text="Refreshing...")
        self.load_remote_files(server_url, file_tree, status_label)
    
    def download_selected_files(self, server_url, file_tree, save_dir):
        """Download selected files from remote server"""
        selected = file_tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select files to download.")
            return
        
        file_list = []
        for item_id in selected:
            values = file_tree.item(item_id)['values']
            file_list.append({
                'id': item_id,
                'name': values[0],
                'size': values[1],
                'modified': values[2]
            })
        
        self.start_downloads(server_url, file_list, save_dir)
    
    def download_all_files(self, server_url, file_tree, save_dir):
        """Download all files from remote server"""
        file_list = []
        for item_id in file_tree.get_children():
            values = file_tree.item(item_id)['values']
            file_list.append({
                'id': item_id,
                'name': values[0],
                'size': values[1],
                'modified': values[2]
            })
        
        if not file_list:
            messagebox.showinfo("No Files", "No files available to download.")
            return
        
        response = messagebox.askyesno("Download All", 
                                      f"Download all {len(file_list)} file(s)?")
        if response:
            self.start_downloads(server_url, file_list, save_dir)
    
    def start_downloads(self, server_url, file_list, save_dir):
        """Start downloading files"""
        self.log(f"Starting download of {len(file_list)} file(s) from {server_url}")
        
        for file_info in file_list:
            self.client.download_file(server_url, file_info['id'], file_info['name'], save_dir)
        
        messagebox.showinfo("Download Started", 
                          f"Downloading {len(file_list)} file(s) to:\n{save_dir}\n\nCheck activity log for progress.")
    
    def update_download_status(self, download_id, status, progress, message):
        """Update download status in the log"""
        if status == 'started':
            self.log(message)
        elif status == 'progress':
            # Only log every 25% to avoid spam
            if progress % 25 == 0:
                self.log(message)
        elif status == 'completed':
            self.log(f"✓ {message}")
        elif status == 'failed':
            self.log(f"✗ {message}")
    
    def setup_client(self):
        """Setup download client"""
        try:
            self.client, self.browser = create_client_integration(self)
            self.log("Download client initialized")
        except Exception as e:
            self.log(f"Failed to initialize download client: {e}")
    
    def get_local_ip(self):
        """Get local IP address"""
        try:
            # Create a socket to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            self.local_ip = local_ip
            self.ip_label.config(text=f"IP: {local_ip}")
            self.log(f"Local IP detected: {local_ip}")
        except Exception as e:
            self.local_ip = "127.0.0.1"
            self.ip_label.config(text=f"IP: {self.local_ip}")
            self.log(f"Could not detect local IP, using localhost: {str(e)}")
    
    def is_port_available(self, port):
        """Check if a port is available for binding"""
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_socket.bind(('0.0.0.0', port))
            test_socket.close()
            return True
        except OSError:
            return False
    
    def find_available_port(self):
        """Find an available port from the port range"""
        for port in self.port_range:
            if self.is_port_available(port):
                return port
        return None
    
    def start_server(self):
        """Start the file sharing server"""
        if not self.shared_files:
            messagebox.showwarning("No Files", "Please add files to share before starting the server.")
            return
        
        try:
            # Check if default port is available, otherwise find alternative
            if not self.is_port_available(self.port):
                self.log(f"Port {self.port} is already in use, searching for alternative...")
                available_port = self.find_available_port()
                
                if available_port is None:
                    error_msg = f"No available ports found in range {self.port_range.start}-{self.port_range.stop-1}.\n\n" \
                               f"Please close other applications using these ports or:\n" \
                               f"1. Check Windows Firewall settings\n" \
                               f"2. Run as Administrator\n" \
                               f"3. Restart your computer"
                    messagebox.showerror("Port Unavailable", error_msg)
                    self.log("Failed to start server: No available ports")
                    return
                
                self.port = available_port
                self.port_label.config(text=f"Port: {self.port}")
                self.log(f"Using alternative port: {self.port}")
            
            # Create handler with shared files and security
            if self.use_security:
                handler = lambda *args, **kwargs: SecureFileShareHandler(
                    *args, 
                    shared_files=self.shared_files, 
                    access_control=self.access_control, 
                    **kwargs
                )
                self.access_control.require_token = True
            else:
                handler = lambda *args, **kwargs: FileShareHandler(*args, shared_files=self.shared_files, **kwargs)
            
            # Set up connection notification callback
            FileShareHandler.connection_callback = self.on_client_connection
            
            # Start optimized server with network optimizations
            self.server = OptimizedHTTPServer.create_optimized_server(('0.0.0.0', self.port), handler)
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            self.is_server_running = True
            self.update_server_status(True)
            
            if self.use_security:
                self.log(f"Secure server started on http://{self.local_ip}:{self.port}")
                token = self.access_control.generate_token()
                self.log(f"Access token: {token}")
                messagebox.showinfo("Server Started", f"Server started with security enabled.\n\nAccess Token: {token}\n\nShare this token with authorized users.")
            else:
                self.log(f"Server started on http://{self.local_ip}:{self.port}")
            
        except PermissionError as e:
            error_msg = f"Permission denied to bind to port {self.port}.\n\n" \
                       f"Solutions:\n" \
                       f"1. Run the application as Administrator\n" \
                       f"2. Check Windows Firewall settings\n" \
                       f"3. Ensure no other application is using port {self.port}"
            messagebox.showerror("Permission Error", error_msg)
            self.log(f"Server start failed: Permission denied on port {self.port}")
        except OSError as e:
            if "10013" in str(e) or "access" in str(e).lower():
                error_msg = f"Cannot access port {self.port}.\n\n" \
                           f"This usually means:\n" \
                           f"• Another application is using this port\n" \
                           f"• Windows Firewall is blocking the port\n" \
                           f"• Insufficient permissions\n\n" \
                           f"Solutions:\n" \
                           f"1. Close other applications (Skype, IIS, etc.)\n" \
                           f"2. Run as Administrator\n" \
                           f"3. Allow Python through Windows Firewall"
                messagebox.showerror("Port Access Error", error_msg)
                self.log(f"Server start failed: Port {self.port} access denied (WinError 10013)")
            else:
                messagebox.showerror("Server Error", f"Failed to start server: {str(e)}")
                self.log(f"Server start failed: {str(e)}")
        except Exception as e:
            messagebox.showerror("Server Error", f"Failed to start server: {str(e)}")
            self.log(f"Server start failed: {str(e)}")
    
    def stop_server(self):
        """Stop the file sharing server"""
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
                self.server_thread.join(timeout=5)
                self.is_server_running = False
                self.update_server_status(False)
                # Reset to default port for next start
                self.port = 8000
                self.port_label.config(text=f"Port: {self.port}")
                self.log("Server stopped")
            except Exception as e:
                self.log(f"Error stopping server: {str(e)}")
    
    def update_server_status(self, running):
        """Update GUI based on server status"""
        if running:
            self.status_label.config(text="Server: Running", foreground="green")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.open_browser_button.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="Server: Stopped", foreground="red")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.open_browser_button.config(state=tk.DISABLED)
    
    def open_in_browser(self):
        """Open the file share page in browser"""
        if self.is_server_running:
            url = f"http://{self.local_ip}:{self.port}"
            webbrowser.open(url)
            self.log(f"Opened {url} in browser")
    
    def add_files(self):
        """Add files to share"""
        files = filedialog.askopenfilenames(
            title="Select files to share",
            filetypes=[("All files", "*.*")]
        )
        
        added_count = 0
        for file_path in files:
            if self._add_single_file(file_path):
                added_count += 1
        
        if added_count > 0:
            self.log(f"Added {added_count} file(s) to share")
            self.save_shared_config()
    
    def add_folder(self):
        """Add folder and all its contents to share"""
        folder_path = filedialog.askdirectory(
            title="Select folder to share"
        )
        
        if not folder_path:
            return
        
        self.log(f"Scanning folder: {folder_path}")
        added_count = 0
        
        # Recursively scan folder
        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                if self._add_single_file(file_path, show_log=False, base_folder=folder_path):
                    added_count += 1
        
        if added_count > 0:
            self.log(f"Added {added_count} file(s) from folder: {os.path.basename(folder_path)}")
            self.save_shared_config()
        else:
            self.log(f"No new files found in folder: {os.path.basename(folder_path)}")
    
    def _add_single_file(self, file_path, show_log=True, base_folder=None):
        """Add a single file to the shared files list with size validation"""
        try:
            # Check if file already exists
            if file_path in [f['path'] for f in self.shared_files.values()]:
                return False
            
            # Skip if not a file
            if not os.path.isfile(file_path):
                return False
            
            file_stat = os.stat(file_path)
            file_size_bytes = file_stat.st_size
            
            # Validate file size
            is_valid, message = validate_file_size(file_size_bytes)
            if not is_valid:
                if show_log:
                    self.log(f"⚠️ Skipped {os.path.basename(file_path)}: {message}")
                return False
            
            # Warn about large files
            if message and show_log:
                self.log(f"⚠️ {os.path.basename(file_path)}: {message}")
            
            file_id = str(uuid.uuid4())
            
            # Get relative path for folder structure
            if base_folder and file_path.startswith(base_folder):
                relative_path = os.path.relpath(file_path, base_folder)
                display_name = relative_path.replace('\\', '/')
                folder_path = os.path.dirname(relative_path).replace('\\', '/') if os.path.dirname(relative_path) != '.' else ''
            else:
                display_name = os.path.basename(file_path)
                folder_path = ''
            
            # Get file extension
            _, ext = os.path.splitext(file_path)
            
            file_info = {
                'id': file_id,
                'name': display_name,
                'basename': os.path.basename(file_path),
                'path': file_path,
                'folder': folder_path,
                'extension': ext.lower(),
                'size': format_file_size(file_size_bytes),
                'size_bytes': file_size_bytes,
                'modified': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'full_path': file_path
            }
            self.shared_files[file_id] = file_info
            
            # Add to tree view
            self.file_tree.insert('', 'end', iid=file_id, values=(
                file_info['name'],
                file_info['size'],
                file_info['modified']
            ))
            
            if show_log:
                self.log(f"Added file: {file_info['name']} ({file_info['size']})")
            
            return True
            
        except Exception as e:
            if show_log:
                self.log(f"Error adding file {file_path}: {str(e)}")
            return False
    
    def remove_selected(self):
        """Remove selected files from sharing"""
        selected = self.file_tree.selection()
        if selected:
            for file_id in selected:
                if file_id in self.shared_files:
                    file_name = self.shared_files[file_id]['name']
                    del self.shared_files[file_id]
                    self.file_tree.delete(file_id)
                    self.log(f"Removed file: {file_name}")
            self.save_shared_config()
    
    def clear_all(self):
        """Clear all shared files"""
        if self.shared_files:
            self.shared_files.clear()
            for item in self.file_tree.get_children():
                self.file_tree.delete(item)
            self.log("Cleared all shared files")
            self.save_shared_config()
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        return format_file_size(size_bytes)
    
    def load_download_directory(self):
        """Load download directory from config file"""
        config_file = os.path.join(os.path.expanduser("~"), ".lanfileshare_config.json")
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    download_dir = config.get('download_directory')
                    if download_dir and os.path.exists(os.path.dirname(download_dir)):
                        return download_dir
        except Exception as e:
            self.log(f"Error loading download directory config: {e}")
        
        # Default location
        return os.path.join(os.path.expanduser("~"), "Downloads", "LANFileShare")
    
    def save_shared_config(self):
        """Save currently shared files/folders to config"""
        try:
            config = {
                'shared_items': [],
                'last_updated': datetime.now().isoformat()
            }
            
            # Track which base folders we've already saved
            saved_folders = set()
            
            for file_id, file_info in self.shared_files.items():
                file_path = file_info['path']
                
                # Check if this file is part of a folder that was added
                # by looking at the folder field
                if file_info.get('folder'):
                    # This file is part of a shared folder
                    # Extract the base folder path
                    full_path = file_info['full_path']
                    # Get the base folder by removing the relative part
                    relative_path = file_info['name']
                    if '/' in relative_path or '\\' in relative_path:
                        # Calculate base folder
                        base_folder = os.path.dirname(full_path)
                        # Walk up to find the root shared folder
                        folder_parts = file_info['folder'].split('/')
                        for _ in range(len(folder_parts)):
                            base_folder = os.path.dirname(base_folder)
                        
                        if base_folder not in saved_folders:
                            saved_folders.add(base_folder)
                            config['shared_items'].append({
                                'type': 'folder',
                                'path': base_folder
                            })
                else:
                    # Individual file
                    config['shared_items'].append({
                        'type': 'file',
                        'path': file_path
                    })
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.log(f"Saved configuration: {len(config['shared_items'])} item(s)")
            
        except Exception as e:
            self.log(f"Error saving shared config: {e}")
    
    def load_shared_config(self):
        """Load previously shared files/folders from config"""
        try:
            if not os.path.exists(self.config_file):
                return
            
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            shared_items = config.get('shared_items', [])
            if not shared_items:
                return
            
            self.log(f"Loading {len(shared_items)} previously shared item(s)...")
            
            missing_items = []
            loaded_count = 0
            
            for item in shared_items:
                item_type = item.get('type')
                item_path = item.get('path')
                
                if not os.path.exists(item_path):
                    missing_items.append(item)
                    continue
                
                if item_type == 'file':
                    if self._add_single_file(item_path, show_log=False):
                        loaded_count += 1
                elif item_type == 'folder':
                    # Add folder contents
                    for root, dirs, files in os.walk(item_path):
                        for filename in files:
                            file_path = os.path.join(root, filename)
                            if self._add_single_file(file_path, show_log=False, base_folder=item_path):
                                loaded_count += 1
            
            if loaded_count > 0:
                self.log(f"Loaded {loaded_count} file(s) from saved configuration")
            
            # Handle missing items
            if missing_items:
                self.handle_missing_items(missing_items)
                
        except Exception as e:
            self.log(f"Error loading shared config: {e}")
    
    def handle_missing_items(self, missing_items):
        """Handle missing files/folders from saved configuration"""
        missing_count = len(missing_items)
        
        message = f"Found {missing_count} missing item(s) from previous session:\n\n"
        for item in missing_items[:5]:  # Show first 5
            message += f"  • {item['type'].title()}: {item['path']}\n"
        
        if missing_count > 5:
            message += f"  ... and {missing_count - 5} more\n"
        
        message += "\nWould you like to re-select these items?"
        
        response = messagebox.askyesno("Missing Shared Items", message)
        
        if response:
            self.reselect_missing_items(missing_items)
    
    def reselect_missing_items(self, missing_items):
        """Allow user to re-select missing items"""
        for item in missing_items:
            item_type = item['type']
            old_path = item['path']
            
            message = f"Original {item_type} not found:\n{old_path}\n\nSelect new location:"
            messagebox.showinfo("Re-select Item", message)
            
            if item_type == 'file':
                files = filedialog.askopenfilenames(
                    title=f"Select replacement for: {os.path.basename(old_path)}",
                    filetypes=[("All files", "*.*")]
                )
                for file_path in files:
                    self._add_single_file(file_path)
            
            elif item_type == 'folder':
                folder_path = filedialog.askdirectory(
                    title=f"Select replacement for: {os.path.basename(old_path)}"
                )
                if folder_path:
                    self.log(f"Scanning folder: {folder_path}")
                    added_count = 0
                    for root, dirs, files in os.walk(folder_path):
                        for filename in files:
                            file_path = os.path.join(root, filename)
                            if self._add_single_file(file_path, show_log=False, base_folder=folder_path):
                                added_count += 1
                    if added_count > 0:
                        self.log(f"Added {added_count} file(s) from folder: {os.path.basename(folder_path)}")
        
        # Save updated config
        self.save_shared_config()
    
    def save_download_directory(self, directory):
        """Save download directory to config file"""
        config_file = os.path.join(os.path.expanduser("~"), ".lanfileshare_config.json")
        try:
            config = {}
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
            
            config['download_directory'] = directory
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.download_save_dir = directory
            self.log(f"Download directory saved: {directory}")
        except Exception as e:
            self.log(f"Error saving download directory config: {e}")
    
    def browse_download_directory(self, dir_var):
        """Browse for download directory"""
        directory = filedialog.askdirectory(
            title="Select Download Directory",
            initialdir=dir_var.get()
        )
        
        if directory:
            dir_var.set(directory)
            self.save_download_directory(directory)
    
    def open_settings(self):
        """Open settings window"""
        open_settings(self.root)
        self.log("Settings window opened")
    
    def on_client_connection(self, client_ip, action, details):
        """Handle client connection notifications"""
        try:
            # Update connection tracking
            if client_ip not in self.connected_clients:
                self.connected_clients[client_ip] = {
                    'first_seen': datetime.now(),
                    'last_seen': datetime.now(),
                    'actions': []
                }
            else:
                self.connected_clients[client_ip]['last_seen'] = datetime.now()
            
            # Add action to history
            self.connected_clients[client_ip]['actions'].append({
                'action': action,
                'details': details,
                'timestamp': datetime.now()
            })
            
            # Add to connection history
            self.connection_history.append({
                'ip': client_ip,
                'action': action,
                'details': details,
                'timestamp': datetime.now()
            })
            
            # Update UI
            self.update_connection_display()
            
            # Log the connection
            if action == "browsing files":
                self.log(f"🔵 Client connected: {client_ip} is browsing files")
            elif action == "downloading file":
                self.log(f"⬇️ Client {client_ip} is {action}")
            elif action == "download_start":
                self.log(f"📥 {client_ip}: {details}")
            else:
                self.log(f"🔗 Client {client_ip}: {action}")
        
        except Exception as e:
            self.log(f"Error handling connection notification: {e}")
    
    def update_connection_display(self):
        """Update the connection count display"""
        try:
            # Count active connections (seen in last 5 minutes)
            now = datetime.now()
            active_count = sum(1 for client in self.connected_clients.values() 
                             if (now - client['last_seen']).total_seconds() < 300)
            
            self.connections_label.config(text=f"Active Connections: {active_count}")
            
            # Update color based on activity
            if active_count > 0:
                self.connections_label.config(foreground="green")
            else:
                self.connections_label.config(foreground="blue")
        except Exception as e:
            pass
    
    def log(self, message):
        """Add message to activity log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def run(self):
        """Start the application"""
        # Load configuration from file if it exists
        load_config_from_file()
        self.log("Windows LAN File Share started")
        self.log("Add files and click 'Start Server' to begin sharing")
        try:
            self.root.mainloop()
        finally:
            if self.discovery:
                self.discovery.stop_discovery()

def main():
    """Main entry point"""
    try:
        app = LANFileShareApp()
        app.run()
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
    except Exception as e:
        print(f"Error: {str(e)}")
        messagebox.showerror("Error", f"Application error: {str(e)}")

if __name__ == "__main__":
    main()
