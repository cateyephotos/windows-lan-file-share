#!/usr/bin/env python3
"""
Fast Transfer Module for Windows LAN File Share
Implements multi-threaded downloads and network optimizations for maximum speed
"""

import os
import threading
import queue
import time
import socket
from urllib.parse import urljoin
import urllib.request
import urllib.error
from config import CONFIG
from file_verification import FileVerifier, ResumeManager, ChunkVerifier

class MultiThreadedDownloader:
    """
    Multi-threaded file downloader with parallel chunk downloads
    Significantly speeds up large file transfers
    """
    
    def __init__(self, url, save_path, file_size, num_threads=None, token=None, expected_checksum=None, enable_resume=True):
        self.url = url
        self.save_path = save_path
        self.file_size = file_size
        self.num_threads = num_threads or CONFIG.get('max_download_threads', 4)
        self.token = token
        self.expected_checksum = expected_checksum
        self.enable_resume = enable_resume
        
        self.chunks_queue = queue.Queue()
        self.downloaded_bytes = 0
        self.lock = threading.Lock()
        self.errors = []
        self.start_time = None
        self.is_cancelled = False
        self.resume_manager = ResumeManager() if enable_resume else None
        self.download_id = self._generate_download_id()
        
    def download(self, progress_callback=None):
        """
        Download file using multiple threads
        
        Args:
            progress_callback: Function to call with progress updates (bytes_downloaded, total_bytes, speed_mbps)
            
        Returns:
            True if successful, False otherwise
        """
        self.start_time = time.time()
        
        # Calculate chunk size per thread
        chunk_size = CONFIG.get('thread_chunk_size', 2 * 1024 * 1024)
        
        # Create chunks
        chunks = []
        offset = 0
        chunk_id = 0
        
        while offset < self.file_size:
            end = min(offset + chunk_size - 1, self.file_size - 1)
            chunks.append({
                'id': chunk_id,
                'start': offset,
                'end': end,
                'size': end - offset + 1
            })
            offset = end + 1
            chunk_id += 1
        
        # Add chunks to queue
        for chunk in chunks:
            self.chunks_queue.put(chunk)
        
        # Create temporary file
        temp_files = []
        
        # Start download threads
        threads = []
        for i in range(min(self.num_threads, len(chunks))):
            thread = threading.Thread(
                target=self._download_worker,
                args=(temp_files, progress_callback),
                daemon=True
            )
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check for errors
        if self.errors:
            return False, f"Download failed: {self.errors[0]}"
        
        if self.is_cancelled:
            return False, "Download cancelled"
        
        # Merge chunks into final file with verification
        try:
            # Prepare chunk files in order
            sorted_chunks = sorted(temp_files, key=lambda x: x['id'])
            chunk_paths = [c['path'] for c in sorted_chunks]
            
            # Merge and verify
            success, error_msg = ChunkVerifier.merge_and_verify_chunks(
                chunk_paths,
                self.save_path,
                self.file_size,
                self.expected_checksum
            )
            
            if not success:
                return False, error_msg
            
            # Delete temp files after successful merge
            for temp_file in sorted_chunks:
                try:
                    os.remove(temp_file['path'])
                except:
                    pass
            
            # Delete resume info after successful download
            if self.resume_manager:
                self.resume_manager.delete_resume_info(self.download_id)
            
            # Final verification
            if self.expected_checksum:
                is_valid, actual_checksum = FileVerifier.verify_file(
                    self.save_path,
                    self.expected_checksum,
                    'sha256'
                )
                if not is_valid:
                    return False, "Final checksum verification failed"
            
            return True, "Download complete and verified"
            
        except Exception as e:
            return False, f"Error merging chunks: {str(e)}"
    
    def _download_worker(self, temp_files, progress_callback):
        """Worker thread for downloading chunks"""
        while not self.chunks_queue.empty() and not self.is_cancelled:
            try:
                chunk = self.chunks_queue.get_nowait()
            except queue.Empty:
                break
            
            try:
                # Download chunk
                temp_path = f"{self.save_path}.part{chunk['id']}"
                
                headers = {
                    'Range': f"bytes={chunk['start']}-{chunk['end']}"
                }
                if self.token:
                    headers['Authorization'] = f'Bearer {self.token}'
                
                req = urllib.request.Request(self.url, headers=headers)
                
                with urllib.request.urlopen(req, timeout=CONFIG.get('connection_timeout', 30)) as response:
                    with open(temp_path, 'wb') as f:
                        downloaded = 0
                        buffer_size = 65536  # 64 KB buffer
                        
                        while downloaded < chunk['size']:
                            data = response.read(min(buffer_size, chunk['size'] - downloaded))
                            if not data:
                                break
                            
                            f.write(data)
                            downloaded += len(data)
                            
                            # Update progress
                            with self.lock:
                                self.downloaded_bytes += len(data)
                                
                                if progress_callback:
                                    elapsed = time.time() - self.start_time
                                    speed_mbps = (self.downloaded_bytes / elapsed / 1024 / 1024) if elapsed > 0 else 0
                                    progress_callback(self.downloaded_bytes, self.file_size, speed_mbps)
                
                # Add to temp files list
                with self.lock:
                    temp_files.append({'id': chunk['id'], 'path': temp_path})
                
            except Exception as e:
                with self.lock:
                    self.errors.append(str(e))
                break
    
    def _generate_download_id(self):
        """Generate unique download ID for resume tracking"""
        import hashlib
        unique_string = f"{self.url}_{self.save_path}_{self.file_size}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def _save_resume_info(self):
        """Save resume information for interrupted downloads"""
        if not self.resume_manager:
            return
        
        resume_info = {
            'url': self.url,
            'save_path': self.save_path,
            'total_size': self.file_size,
            'downloaded': self.downloaded_bytes,
            'checksum': self.expected_checksum,
            'timestamp': time.time()
        }
        
        self.resume_manager.save_resume_info(self.download_id, resume_info)
    
    def can_resume(self):
        """Check if download can be resumed"""
        if not self.resume_manager:
            return False, 0
        
        return self.resume_manager.can_resume(
            self.download_id,
            self.save_path + '.partial',
            self.file_size
        )
    
    def cancel(self):
        """Cancel the download"""
        self.is_cancelled = True
        self._save_resume_info()

class OptimizedHTTPServer:
    """
    HTTP Server with network optimizations for maximum transfer speed
    """
    
    @staticmethod
    def optimize_socket(sock):
        """
        Apply network optimizations to socket
        
        Args:
            sock: Socket object to optimize
        """
        try:
            # Increase TCP buffer sizes
            buffer_size = CONFIG.get('tcp_buffer_size', 262144)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, buffer_size)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, buffer_size)
            
            # Disable Nagle's algorithm for lower latency
            if CONFIG.get('enable_tcp_nodelay', True):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            # Enable TCP keepalive
            if CONFIG.get('enable_keepalive', True):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                
                # Set keepalive parameters (Windows)
                if hasattr(socket, 'TCP_KEEPIDLE'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                if hasattr(socket, 'TCP_KEEPINTVL'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                if hasattr(socket, 'TCP_KEEPCNT'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)
            
        except Exception as e:
            print(f"Warning: Could not apply socket optimizations: {e}")
    
    @staticmethod
    def create_optimized_server(server_address, handler_class):
        """
        Create HTTP server with optimized socket settings
        
        Args:
            server_address: Tuple of (host, port)
            handler_class: Request handler class
            
        Returns:
            Optimized HTTPServer instance
        """
        from http.server import HTTPServer
        
        outer = OptimizedHTTPServer
        
        class _OptimizedHTTPServer(HTTPServer):
            def server_bind(self):
                """Override to apply socket optimizations"""
                outer.optimize_socket(self.socket)
                super().server_bind()
        
        return _OptimizedHTTPServer(server_address, handler_class)

class SpeedMonitor:
    """Monitor and report transfer speeds"""
    
    def __init__(self, window_size=10):
        self.window_size = window_size
        self.samples = []
        self.lock = threading.Lock()
    
    def add_sample(self, bytes_transferred, elapsed_time):
        """
        Add a speed sample
        
        Args:
            bytes_transferred: Bytes transferred in this sample
            elapsed_time: Time elapsed for this sample
        """
        with self.lock:
            speed_mbps = (bytes_transferred / elapsed_time / 1024 / 1024) if elapsed_time > 0 else 0
            self.samples.append(speed_mbps)
            
            # Keep only recent samples
            if len(self.samples) > self.window_size:
                self.samples.pop(0)
    
    def get_average_speed(self):
        """Get average speed in Mbps"""
        with self.lock:
            if not self.samples:
                return 0
            return sum(self.samples) / len(self.samples)
    
    def get_current_speed(self):
        """Get most recent speed in Mbps"""
        with self.lock:
            if not self.samples:
                return 0
            return self.samples[-1]
    
    def format_speed(self, speed_mbps):
        """Format speed for display"""
        if speed_mbps < 1:
            return f"{speed_mbps * 1024:.1f} KB/s"
        else:
            return f"{speed_mbps:.1f} MB/s"

def should_use_multithread(file_size):
    """
    Determine if multi-threaded download should be used
    
    Args:
        file_size: Size of file in bytes
        
    Returns:
        Boolean indicating if multi-threading should be used
    """
    if not CONFIG.get('enable_multithreaded_download', True):
        return False
    
    min_size = CONFIG.get('min_file_size_for_multithread', 10 * 1024 * 1024)
    return file_size >= min_size

def calculate_optimal_threads(file_size):
    """
    Calculate optimal number of threads based on file size
    
    Args:
        file_size: Size of file in bytes
        
    Returns:
        Optimal number of threads
    """
    max_threads = CONFIG.get('max_download_threads', 4)
    chunk_size = CONFIG.get('thread_chunk_size', 2 * 1024 * 1024)
    
    # Calculate how many chunks the file can be divided into
    num_chunks = file_size // chunk_size
    
    # Use fewer threads for smaller files
    if file_size < 50 * 1024 * 1024:  # < 50 MB
        return min(2, max_threads)
    elif file_size < 500 * 1024 * 1024:  # < 500 MB
        return min(4, max_threads)
    else:
        return max_threads

def estimate_transfer_time(file_size, speed_mbps):
    """
    Estimate transfer time
    
    Args:
        file_size: Size in bytes
        speed_mbps: Speed in MB/s
        
    Returns:
        Estimated time in seconds
    """
    if speed_mbps <= 0:
        return 0
    
    file_size_mb = file_size / (1024 * 1024)
    return file_size_mb / speed_mbps

def format_time(seconds):
    """Format time for display"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"
