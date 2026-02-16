#!/usr/bin/env python3
"""
Client Module for Windows LAN File Share
Enables downloading files from other servers on the network
"""

import os
import json
import urllib.request
import urllib.error
from urllib.parse import urljoin
import threading
from datetime import datetime
from config import get_chunk_size, CONFIG
from fast_transfer import MultiThreadedDownloader, should_use_multithread, calculate_optimal_threads, SpeedMonitor

class FileShareClient:
    """Client for connecting to and downloading from other file share servers"""
    
    def __init__(self):
        self.download_callbacks = []
        self.active_downloads = {}
    
    def add_download_callback(self, callback):
        """Add callback for download progress updates"""
        self.download_callbacks.append(callback)
    
    def notify_callbacks(self, download_id, status, progress=0, message=""):
        """Notify all callbacks about download progress"""
        for callback in self.download_callbacks:
            try:
                callback(download_id, status, progress, message)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def fetch_file_list(self, server_url, token=None):
        """Fetch list of files from a remote server"""
        try:
            # Parse the HTML response to extract file information
            headers = {}
            if token:
                headers['Authorization'] = f'Bearer {token}'
            
            req = urllib.request.Request(server_url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                html_content = response.read().decode('utf-8')
                
                # Parse file list from HTML
                files = self._parse_file_list_from_html(html_content)
                return files
                
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise Exception("Authentication required - token needed")
            elif e.code == 403:
                raise Exception("Access denied")
            else:
                raise Exception(f"HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Connection error: {str(e.reason)}")
        except Exception as e:
            raise Exception(f"Failed to fetch file list: {str(e)}")
    
    def _parse_file_list_from_html(self, html_content):
        """Parse file information from HTML response"""
        files = []
        
        # Simple HTML parsing to extract file information
        # Look for download links in the format /download/{file_id}
        import re
        
        # Find all download links
        download_pattern = r'/download/([a-f0-9\-]+)'
        download_matches = re.findall(download_pattern, html_content)
        
        # Find file names (look for patterns between specific HTML tags)
        name_pattern = r'<div class="file-name">(?:📄 )?([^<]+)</div>'
        name_matches = re.findall(name_pattern, html_content)
        
        # Find file sizes
        size_pattern = r'📊 Size: ([^|]+)\|'
        size_matches = re.findall(size_pattern, html_content)
        
        # Find modified dates
        modified_pattern = r'🕒 Modified: ([^<]+)'
        modified_matches = re.findall(modified_pattern, html_content)
        
        # Combine the information
        for i, file_id in enumerate(download_matches):
            file_info = {
                'id': file_id,
                'name': name_matches[i].strip() if i < len(name_matches) else f"file_{i}",
                'size': size_matches[i].strip() if i < len(size_matches) else "Unknown",
                'modified': modified_matches[i].strip() if i < len(modified_matches) else "Unknown"
            }
            files.append(file_info)
        
        return files
    
    def download_file(self, server_url, file_id, file_name, save_directory, token=None, file_size=None):
        """Download a file from a remote server (uses multi-threading for large files)"""
        download_id = f"{server_url}_{file_id}"
        
        # Start download in a separate thread
        thread = threading.Thread(
            target=self._download_file_thread,
            args=(server_url, file_id, file_name, save_directory, token, download_id, file_size),
            daemon=True
        )
        thread.start()
        
        return download_id
    
    def _download_file_thread(self, server_url, file_id, file_name, save_directory, token, download_id, file_size=None):
        """Download file in a separate thread with multi-threading support for large files"""
        try:
            self.active_downloads[download_id] = {
                'status': 'downloading',
                'progress': 0,
                'file_name': file_name
            }
            
            self.notify_callbacks(download_id, 'started', 0, f"Starting download: {file_name}")
            
            # Construct download URL
            download_url = urljoin(server_url, f'/download/{file_id}')
            
            # Create save path
            os.makedirs(save_directory, exist_ok=True)
            save_path = os.path.join(save_directory, file_name)
            
            # Handle duplicate filenames
            counter = 1
            base_name, extension = os.path.splitext(file_name)
            while os.path.exists(save_path):
                save_path = os.path.join(save_directory, f"{base_name}_{counter}{extension}")
                counter += 1
            
            # Get file size if not provided
            if file_size is None:
                headers = {}
                if token:
                    headers['Authorization'] = f'Bearer {token}'
                req = urllib.request.Request(download_url, headers=headers, method='HEAD')
                try:
                    with urllib.request.urlopen(req, timeout=10) as response:
                        file_size = int(response.headers.get('Content-Length', 0))
                except:
                    file_size = 0
            
            # Determine if multi-threaded download should be used
            use_multithread = should_use_multithread(file_size) if file_size > 0 else False
            
            if use_multithread:
                # Use multi-threaded download for large files
                num_threads = calculate_optimal_threads(file_size)
                self.notify_callbacks(download_id, 'progress', 0, 
                                    f"Starting multi-threaded download ({num_threads} threads)...")
                
                speed_monitor = SpeedMonitor()
                
                def progress_callback(downloaded, total, speed_mbps):
                    progress = int((downloaded / total) * 100) if total > 0 else 0
                    self.active_downloads[download_id]['progress'] = progress
                    speed_monitor.add_sample(downloaded, 1)
                    avg_speed = speed_monitor.get_average_speed()
                    self.notify_callbacks(download_id, 'progress', progress, 
                                        f"Downloading: {progress}% @ {speed_monitor.format_speed(avg_speed)}")
                
                downloader = MultiThreadedDownloader(download_url, save_path, file_size, num_threads, token)
                success, message = downloader.download(progress_callback)
                
                if not success:
                    raise Exception(message)
            else:
                # Use single-threaded download for smaller files
                headers = {}
                if token:
                    headers['Authorization'] = f'Bearer {token}'
                
                req = urllib.request.Request(download_url, headers=headers)
                timeout = CONFIG.get('download_timeout', 300)
                
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded = 0
                    
                    chunk_size = get_chunk_size(total_size) if total_size > 0 else CONFIG.get('chunk_size_medium', 65536)
                    
                    with open(save_path, 'wb') as f:
                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0:
                                progress = int((downloaded / total_size) * 100)
                                self.active_downloads[download_id]['progress'] = progress
                                self.notify_callbacks(download_id, 'progress', progress, 
                                                    f"Downloading: {progress}%")
            
            # Download complete
            self.active_downloads[download_id]['status'] = 'completed'
            self.active_downloads[download_id]['progress'] = 100
            self.active_downloads[download_id]['save_path'] = save_path
            
            self.notify_callbacks(download_id, 'completed', 100, 
                                f"Download complete: {file_name}\nSaved to: {save_path}")
            
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP Error {e.code}: {e.reason}"
            self.active_downloads[download_id]['status'] = 'failed'
            self.active_downloads[download_id]['error'] = error_msg
            self.notify_callbacks(download_id, 'failed', 0, error_msg)
            
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            self.active_downloads[download_id]['status'] = 'failed'
            self.active_downloads[download_id]['error'] = error_msg
            self.notify_callbacks(download_id, 'failed', 0, error_msg)
    
    def download_multiple_files(self, server_url, file_list, save_directory, token=None):
        """Download multiple files from a server"""
        download_ids = []
        
        for file_info in file_list:
            file_id = file_info['id']
            file_name = file_info['name']
            
            download_id = self.download_file(server_url, file_id, file_name, save_directory, token)
            download_ids.append(download_id)
        
        return download_ids
    
    def get_download_status(self, download_id):
        """Get status of a download"""
        return self.active_downloads.get(download_id, None)
    
    def cancel_download(self, download_id):
        """Cancel an active download"""
        if download_id in self.active_downloads:
            self.active_downloads[download_id]['status'] = 'cancelled'
            self.notify_callbacks(download_id, 'cancelled', 0, "Download cancelled")
    
    def clear_completed_downloads(self):
        """Clear completed downloads from the list"""
        completed = [did for did, info in self.active_downloads.items() 
                    if info['status'] in ['completed', 'failed', 'cancelled']]
        
        for download_id in completed:
            del self.active_downloads[download_id]
        
        return len(completed)

class RemoteServerBrowser:
    """Browse and interact with remote file share servers"""
    
    def __init__(self, client):
        self.client = client
        self.cached_file_lists = {}
        self.cache_timeout = 60  # seconds
    
    def browse_server(self, server_url, token=None, force_refresh=False):
        """Browse files on a remote server"""
        cache_key = server_url
        
        # Check cache
        if not force_refresh and cache_key in self.cached_file_lists:
            cached_data = self.cached_file_lists[cache_key]
            age = (datetime.now() - cached_data['timestamp']).total_seconds()
            
            if age < self.cache_timeout:
                return cached_data['files']
        
        # Fetch fresh data
        try:
            files = self.client.fetch_file_list(server_url, token)
            
            # Update cache
            self.cached_file_lists[cache_key] = {
                'files': files,
                'timestamp': datetime.now()
            }
            
            return files
            
        except Exception as e:
            # If cache exists, return cached data even if expired
            if cache_key in self.cached_file_lists:
                return self.cached_file_lists[cache_key]['files']
            else:
                raise e
    
    def search_files(self, server_url, search_term, token=None):
        """Search for files on a remote server"""
        try:
            files = self.browse_server(server_url, token)
            
            # Filter files by search term
            search_term_lower = search_term.lower()
            matching_files = [
                f for f in files 
                if search_term_lower in f['name'].lower()
            ]
            
            return matching_files
            
        except Exception as e:
            raise Exception(f"Search failed: {str(e)}")
    
    def clear_cache(self):
        """Clear the file list cache"""
        self.cached_file_lists.clear()

def create_client_integration(main_app):
    """Create client integration for the main application"""
    
    client = FileShareClient()
    browser = RemoteServerBrowser(client)
    
    def on_download_progress(download_id, status, progress, message):
        """Handle download progress updates"""
        if hasattr(main_app, 'update_download_status'):
            main_app.update_download_status(download_id, status, progress, message)
    
    client.add_download_callback(on_download_progress)
    
    return client, browser
