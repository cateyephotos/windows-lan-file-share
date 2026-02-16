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

class FileShareHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for file sharing"""
    
    def __init__(self, *args, shared_files=None, **kwargs):
        self.shared_files = shared_files or {}
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == '/':
            self.serve_file_list()
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
                    if file_path.lower().endswith(('.txt', '.py', '.js', '.html', '.css', '.json', '.xml')):
                        self.send_header('Content-type', 'text/plain')
                    elif file_path.lower().endswith(('.jpg', '.jpeg')):
                        self.send_header('Content-type', 'image/jpeg')
                    elif file_path.lower().endswith('.png'):
                        self.send_header('Content-type', 'image/png')
                    elif file_path.lower().endswith('.gif'):
                        self.send_header('Content-type', 'image/gif')
                    else:
                        self.send_header('Content-type', 'application/octet-stream')
                    self.send_header('Content-Length', str(file_size))
                    self.end_headers()
                else:
                    self.send_error(404, "File not found")
            else:
                self.send_error(404, "File not found")
        else:
            super().do_HEAD()
    
    def serve_file_list(self):
        """Serve the file listing page"""
        html_content = self.generate_file_list_html()
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def serve_file_download(self):
        """Handle file download requests with chunked transfer and Range support for multi-threading"""
        file_id = self.path.split('/download/')[-1]
        if file_id in self.shared_files:
            file_path = self.shared_files[file_id]['path']
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                
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
                        
                        # Determine content type
                        if file_path.lower().endswith(('.txt', '.py', '.js', '.html', '.css', '.json', '.xml')):
                            self.send_header('Content-type', 'text/plain')
                        elif file_path.lower().endswith(('.jpg', '.jpeg')):
                            self.send_header('Content-type', 'image/jpeg')
                        elif file_path.lower().endswith('.png'):
                            self.send_header('Content-type', 'image/png')
                        elif file_path.lower().endswith('.gif'):
                            self.send_header('Content-type', 'image/gif')
                        else:
                            self.send_header('Content-type', 'application/octet-stream')
                        
                        self.end_headers()
                        self.wfile.write(content)
                except Exception as e:
                    self.send_error(500, f"Error serving file: {str(e)}")
            else:
                self.send_error(404, "File not found")
        else:
            self.send_error(404, "File not found")
    
    def generate_file_list_html(self):
        """Generate HTML page for file listing"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>LAN File Share</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; margin-bottom: 30px; }
        .file-item { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; background: #fafafa; }
        .file-item:hover { background: #f0f0f0; }
        .file-name { font-weight: bold; font-size: 16px; color: #2c3e50; }
        .file-info { color: #666; font-size: 14px; margin-top: 5px; }
        .download-btn { background: #3498db; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 10px; }
        .download-btn:hover { background: #2980b9; }
        .preview-btn { background: #27ae60; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 10px; margin-left: 10px; }
        .preview-btn:hover { background: #229954; }
        .no-files { text-align: center; color: #666; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📁 LAN File Share</h1>
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
            <div class="file-name">{filename}</div>
            <div class="file-info">
                Size: {size} | Modified: {modified}
            </div>
            <a href="/download/{file_id}" class="download-btn">⬇️ Download</a>
            <a href="/files/{file_id}" class="preview-btn" target="_blank">👁️ Preview</a>
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
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
        self.discovery = None
        self.access_control = AccessControl()
        self.use_security = False
        self.client = None
        self.browser = None
        self.current_remote_server = None
        self.download_save_dir = os.path.join(os.path.expanduser("~"), "Downloads", "LANFileShare")
        
        self.setup_gui()
        self.get_local_ip()
        self.setup_discovery()
        self.setup_client()
    
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
            self.log("Refreshing network discovery...")
    
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
        ttk.Entry(main_frame, textvariable=download_dir_var, width=30).grid(row=1, column=2)
        
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
    
    def start_server(self):
        """Start the file sharing server"""
        if not self.shared_files:
            messagebox.showwarning("No Files", "Please add files to share before starting the server.")
            return
        
        try:
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
            
            # Start optimized server with network optimizations
            self.server = OptimizedHTTPServer.create_optimized_server(('0.0.0.0', self.port), handler)
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            self.is_server_running = True
            self.update_server_status(True)
            
            if self.use_security:
                self.log(f"Secure server started on http://{self.local_ip}:{self.port}")
                self.log("Access token authentication required")
            else:
                self.log(f"Server started on http://{self.local_ip}:{self.port}")
            
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
                if self._add_single_file(file_path, show_log=False):
                    added_count += 1
        
        if added_count > 0:
            self.log(f"Added {added_count} file(s) from folder: {os.path.basename(folder_path)}")
        else:
            self.log(f"No new files found in folder: {os.path.basename(folder_path)}")
    
    def _add_single_file(self, file_path, show_log=True):
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
            
            # Get relative display name (show folder structure)
            display_name = os.path.basename(file_path)
            
            file_info = {
                'id': file_id,
                'name': display_name,
                'path': file_path,
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
        for file_id in selected:
            if file_id in self.shared_files:
                file_name = self.shared_files[file_id]['name']
                del self.shared_files[file_id]
                self.file_tree.delete(file_id)
                self.log(f"Removed file: {file_name}")
    
    def clear_all(self):
        """Clear all shared files"""
        self.shared_files.clear()
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        self.log("Cleared all shared files")
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        return format_file_size(size_bytes)
    
    def open_settings(self):
        """Open settings window"""
        open_settings(self.root)
        self.log("Settings window opened")
    
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
