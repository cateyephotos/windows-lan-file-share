#!/usr/bin/env python3
"""
Configuration Module for Windows LAN File Share
Centralized configuration for file size limits and transfer settings
"""

# File Size Limits
MAX_FILE_SIZE_MB = 10240  # 10 GB default maximum file size
WARN_FILE_SIZE_MB = 1024  # 1 GB - warn user about large files
MAX_TOTAL_SHARE_SIZE_GB = 50  # Maximum total size of all shared files

# Transfer Settings
CHUNK_SIZE_SMALL = 8192      # 8 KB for files < 10 MB
CHUNK_SIZE_MEDIUM = 65536    # 64 KB for files 10-100 MB
CHUNK_SIZE_LARGE = 524288    # 512 KB for files > 100 MB
CHUNK_SIZE_XLARGE = 1048576  # 1 MB for files > 1 GB

# Network Settings
DOWNLOAD_TIMEOUT = 300  # 5 minutes timeout for downloads
UPLOAD_TIMEOUT = 300    # 5 minutes timeout for uploads
CONNECTION_TIMEOUT = 30  # 30 seconds for initial connection

# Performance Settings
ENABLE_COMPRESSION = False  # Enable gzip compression for transfers
ENABLE_RESUME = False       # Enable resume capability (future feature)
MAX_CONCURRENT_DOWNLOADS = 5  # Maximum simultaneous downloads

# Multi-threaded Download Settings
ENABLE_MULTITHREADED_DOWNLOAD = True  # Enable parallel chunk downloads
MIN_FILE_SIZE_FOR_MULTITHREAD = 10 * 1024 * 1024  # 10 MB minimum
MAX_DOWNLOAD_THREADS = 4  # Number of parallel download threads
THREAD_CHUNK_SIZE = 2 * 1024 * 1024  # 2 MB per thread chunk

# Network Optimization
TCP_BUFFER_SIZE = 262144  # 256 KB TCP buffer (default is usually 64KB)
SOCKET_TIMEOUT = 30  # Socket timeout in seconds
ENABLE_TCP_NODELAY = True  # Disable Nagle's algorithm for faster small packets
ENABLE_KEEPALIVE = True  # Enable TCP keepalive

# UI Settings
SHOW_FILE_SIZE_WARNING = True  # Show warning for large files
AUTO_REFRESH_INTERVAL = 30     # Seconds between auto-refresh of discovery

def get_chunk_size(file_size_bytes):
    """
    Get optimal chunk size based on file size
    
    Args:
        file_size_bytes: Size of file in bytes
        
    Returns:
        Optimal chunk size in bytes
    """
    mb = 1024 * 1024
    
    if file_size_bytes < 10 * mb:
        return CHUNK_SIZE_SMALL
    elif file_size_bytes < 100 * mb:
        return CHUNK_SIZE_MEDIUM
    elif file_size_bytes < 1024 * mb:
        return CHUNK_SIZE_LARGE
    else:
        return CHUNK_SIZE_XLARGE

def format_file_size(size_bytes):
    """
    Format file size in human readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def validate_file_size(file_size_bytes):
    """
    Validate if file size is within limits
    
    Args:
        file_size_bytes: Size of file in bytes
        
    Returns:
        Tuple of (is_valid, message)
    """
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    warn_bytes = WARN_FILE_SIZE_MB * 1024 * 1024
    
    if file_size_bytes > max_bytes:
        return False, f"File exceeds maximum size limit of {MAX_FILE_SIZE_MB} MB"
    elif file_size_bytes > warn_bytes:
        return True, f"Large file ({format_file_size(file_size_bytes)}) - transfer may take time"
    else:
        return True, None

# Configuration dictionary for easy access
CONFIG = {
    'max_file_size_mb': MAX_FILE_SIZE_MB,
    'warn_file_size_mb': WARN_FILE_SIZE_MB,
    'max_total_share_size_gb': MAX_TOTAL_SHARE_SIZE_GB,
    'chunk_size_small': CHUNK_SIZE_SMALL,
    'chunk_size_medium': CHUNK_SIZE_MEDIUM,
    'chunk_size_large': CHUNK_SIZE_LARGE,
    'chunk_size_xlarge': CHUNK_SIZE_XLARGE,
    'download_timeout': DOWNLOAD_TIMEOUT,
    'upload_timeout': UPLOAD_TIMEOUT,
    'connection_timeout': CONNECTION_TIMEOUT,
    'enable_compression': ENABLE_COMPRESSION,
    'enable_resume': ENABLE_RESUME,
    'max_concurrent_downloads': MAX_CONCURRENT_DOWNLOADS,
    'show_file_size_warning': SHOW_FILE_SIZE_WARNING,
    'auto_refresh_interval': AUTO_REFRESH_INTERVAL,
}

def load_config_from_file(config_file='config.json'):
    """
    Load configuration from JSON file if it exists
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Updated CONFIG dictionary
    """
    import json
    import os
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                CONFIG.update(user_config)
                print(f"Loaded configuration from {config_file}")
        except Exception as e:
            print(f"Error loading config file: {e}")
    
    return CONFIG

def save_config_to_file(config_file='config.json'):
    """
    Save current configuration to JSON file
    
    Args:
        config_file: Path to configuration file
    """
    import json
    
    try:
        with open(config_file, 'w') as f:
            json.dump(CONFIG, f, indent=2)
        print(f"Configuration saved to {config_file}")
    except Exception as e:
        print(f"Error saving config file: {e}")
