#!/usr/bin/env python3
"""
Network Discovery Module for Windows LAN File Share
Discovers other instances of the file share utility on the local network
"""

import socket
import threading
import json
import time
from datetime import datetime
import subprocess
import re

class NetworkDiscovery:
    """Handles discovery of other file share instances on the LAN"""
    
    def __init__(self, port=8000, discovery_port=8001):
        self.port = port
        self.discovery_port = discovery_port
        self.broadcast_socket = None
        self.listen_socket = None
        self.discovered_servers = {}
        self.is_running = False
        self.callbacks = []
    
    def add_callback(self, callback):
        """Add a callback to be notified when servers are discovered"""
        self.callbacks.append(callback)
        # If servers were already discovered before this callback was added, notify immediately
        if self.discovered_servers:
            try:
                callback(self.discovered_servers)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def notify_callbacks(self):
        """Notify all callbacks about discovered servers"""
        for callback in self.callbacks:
            try:
                callback(self.discovered_servers)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def start_discovery(self):
        """Start network discovery service"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start broadcasting thread
        broadcast_thread = threading.Thread(target=self._broadcast_presence, daemon=True)
        broadcast_thread.start()
        
        # Start listening thread
        listen_thread = threading.Thread(target=self._listen_for_broadcasts, daemon=True)
        listen_thread.start()
        
        # Start scanning thread
        scan_thread = threading.Thread(target=self._scan_network, daemon=True)
        scan_thread.start()
    
    def stop_discovery(self):
        """Stop network discovery service"""
        self.is_running = False
        
        if self.broadcast_socket:
            self.broadcast_socket.close()
        if self.listen_socket:
            self.listen_socket.close()
    
    def _broadcast_presence(self):
        """Broadcast our presence on the network"""
        try:
            self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.broadcast_socket.settimeout(1)
            
            message = json.dumps({
                'type': 'announcement',
                'port': self.port,
                'timestamp': time.time()
            }).encode('utf-8')
            
            while self.is_running:
                try:
                    self.broadcast_socket.sendto(message, ('<broadcast>', self.discovery_port))
                    time.sleep(30)  # Broadcast every 30 seconds
                except Exception as e:
                    if self.is_running:
                        print(f"Broadcast error: {e}")
                    time.sleep(5)
                    
        except Exception as e:
            print(f"Failed to start broadcasting: {e}")
    
    def _listen_for_broadcasts(self):
        """Listen for broadcasts from other instances"""
        try:
            self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listen_socket.bind(('', self.discovery_port))
            self.listen_socket.settimeout(1)
            
            while self.is_running:
                try:
                    data, addr = self.listen_socket.recvfrom(1024)
                    self._process_broadcast(data, addr[0])
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.is_running:
                        print(f"Listen error: {e}")
                    
        except Exception as e:
            print(f"Failed to start listening: {e}")
    
    def _process_broadcast(self, data, sender_ip):
        """Process received broadcast message"""
        try:
            message = json.loads(data.decode('utf-8'))
            
            if message.get('type') == 'announcement':
                server_port = message.get('port')
                if server_port and server_port != self.port:
                    # Add or update discovered server
                    server_key = f"{sender_ip}:{server_port}"
                    self.discovered_servers[server_key] = {
                        'ip': sender_ip,
                        'port': server_port,
                        'url': f"http://{sender_ip}:{server_port}",
                        'last_seen': time.time(),
                        'timestamp': message.get('timestamp', 0)
                    }
                    self.notify_callbacks()
                    
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"Error processing broadcast: {e}")
    
    def trigger_manual_scan(self):
        """Trigger an immediate network scan (non-blocking)"""
        if not self.is_running:
            return
        
        scan_thread = threading.Thread(target=self._perform_quick_scan, daemon=True)
        scan_thread.start()
    
    def _perform_quick_scan(self):
        """Perform a quick scan using ARP table and targeted checks"""
        try:
            print("[Discovery] Starting network scan...")
            
            # First, try to get hosts from ARP table
            active_hosts = NetworkScanner.get_active_hosts()
            
            if active_hosts:
                print(f"[Discovery] Scanning {len(active_hosts)} hosts from ARP table...")
                checked_count = 0
                for i, ip in enumerate(active_hosts):
                    if not self.is_running:
                        break
                    self._check_server(ip, self.port)
                    checked_count += 1
                print(f"[Discovery] Scan complete - checked {checked_count} hosts")
            else:
                # Fallback to subnet scan if ARP table is empty
                print("[Discovery] ARP table empty, performing subnet scan...")
                self._scan_subnet()
            
        except Exception as e:
            print(f"[Discovery] Scan error: {e}")
    
    def _scan_subnet(self):
        """Scan the local subnet for servers"""
        local_ip = self._get_local_ip()
        if local_ip and local_ip != "127.0.0.1":
            network_parts = local_ip.split('.')
            network_base = f"{network_parts[0]}.{network_parts[1]}.{network_parts[2]}"
            
            for i in range(1, 255):
                if not self.is_running:
                    break
                    
                target_ip = f"{network_base}.{i}"
                if target_ip != local_ip:
                    self._check_server(target_ip, self.port)
                    
                # Small delay to avoid overwhelming the network
                time.sleep(0.1)
    
    def _scan_network(self):
        """Scan the local network for file share servers"""
        while self.is_running:
            try:
                # Perform quick scan using ARP table
                self._perform_quick_scan()
                
                # Wait before next scan
                time.sleep(300)  # Scan every 5 minutes
                
            except Exception as e:
                print(f"Network scan error: {e}")
                time.sleep(60)
    
    def _check_server(self, ip, port):
        """Check if a file share server is running at the given IP and port"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result == 0:
                server_key = f"{ip}:{port}"
                print(f"[Discovery] Found server at {ip}:{port}")
                self.discovered_servers[server_key] = {
                    'ip': ip,
                    'port': port,
                    'url': f"http://{ip}:{port}",
                    'last_seen': time.time(),
                    'timestamp': 0
                }
                self.notify_callbacks()
                
        except Exception as e:
            # Silently ignore connection errors during scan
            pass
    
    def _get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"
    
    def get_network_range(self):
        """Get the local network range"""
        try:
            local_ip = self._get_local_ip()
            if local_ip and local_ip != "127.0.0.1":
                parts = local_ip.split('.')
                return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        except Exception:
            pass
        return None
    
    def cleanup_old_servers(self):
        """Remove servers that haven't been seen recently"""
        current_time = time.time()
        timeout = 300  # 5 minutes
        
        old_servers = []
        for server_key, server_info in self.discovered_servers.items():
            if current_time - server_info['last_seen'] > timeout:
                old_servers.append(server_key)
        
        for server_key in old_servers:
            del self.discovered_servers[server_key]
        
        if old_servers:
            self.notify_callbacks()

class NetworkScanner:
    """Advanced network scanning utilities"""
    
    @staticmethod
    def get_active_hosts():
        """Get list of active hosts on the local network"""
        try:
            # Try to get ARP table
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                hosts = []
                for line in result.stdout.split('\n'):
                    # Parse ARP table entries
                    match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                    if match:
                        ip = match.group(1)
                        if not ip.startswith('127.') and not ip.startswith('169.254.'):
                            hosts.append(ip)
                return list(set(hosts))  # Remove duplicates
        except Exception:
            pass
        
        return []
    
    @staticmethod
    def ping_host(ip):
        """Ping a host to check if it's reachable"""
        try:
            result = subprocess.run(['ping', '-n', '1', '-w', '1000', ip], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def scan_port(ip, port, timeout=2):
        """Check if a specific port is open on a host"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False

# Integration function for main application
def create_discovery_integration(main_app):
    """Create discovery integration for the main application"""
    
    discovery = NetworkDiscovery()
    
    def on_servers_discovered(servers):
        """Handle discovered servers update"""
        # Update GUI with discovered servers
        if hasattr(main_app, 'update_discovered_servers'):
            main_app.update_discovered_servers(servers)
    
    discovery.add_callback(on_servers_discovered)
    
    return discovery
