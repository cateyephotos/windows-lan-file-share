#!/usr/bin/env python3
"""
Settings UI Module for Windows LAN File Share
Provides a graphical interface for configuring application settings
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from config import CONFIG, save_config_to_file, load_config_from_file

class SettingsWindow:
    """Settings configuration window"""
    
    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("Settings - LAN File Share")
        self.window.geometry("600x700")
        self.window.resizable(False, False)
        
        # Make window modal
        self.window.transient(parent)
        self.window.grab_set()
        
        # Load current configuration
        load_config_from_file()
        
        # Store original values for cancel
        self.original_config = CONFIG.copy()
        
        # Create UI
        self.create_ui()
        
        # Center window
        self.center_window()
    
    def center_window(self):
        """Center the window on screen"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_ui(self):
        """Create the settings UI"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        file_frame = ttk.Frame(notebook)
        performance_frame = ttk.Frame(notebook)
        network_frame = ttk.Frame(notebook)
        advanced_frame = ttk.Frame(notebook)
        
        notebook.add(file_frame, text="File Settings")
        notebook.add(performance_frame, text="Performance")
        notebook.add(network_frame, text="Network")
        notebook.add(advanced_frame, text="Advanced")
        
        # Populate tabs
        self.create_file_settings(file_frame)
        self.create_performance_settings(performance_frame)
        self.create_network_settings(network_frame)
        self.create_advanced_settings(advanced_frame)
        
        # Create button frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(button_frame, text="Save", command=self.save_settings, width=15).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel, width=15).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_defaults, width=15).pack(side=tk.LEFT, padx=5)
    
    def create_file_settings(self, parent):
        """Create file size settings"""
        frame = ttk.LabelFrame(parent, text="File Size Limits", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Max file size
        ttk.Label(frame, text="Maximum File Size (MB):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.max_file_size = ttk.Entry(frame, width=20)
        self.max_file_size.insert(0, str(CONFIG.get('max_file_size_mb', 10240)))
        self.max_file_size.grid(row=0, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame, text="(Default: 10240 MB = 10 GB)", foreground="gray").grid(row=0, column=2, sticky=tk.W, pady=5)
        
        # Warning threshold
        ttk.Label(frame, text="Warning Threshold (MB):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.warn_file_size = ttk.Entry(frame, width=20)
        self.warn_file_size.insert(0, str(CONFIG.get('warn_file_size_mb', 1024)))
        self.warn_file_size.grid(row=1, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame, text="(Default: 1024 MB = 1 GB)", foreground="gray").grid(row=1, column=2, sticky=tk.W, pady=5)
        
        # Max total share size
        ttk.Label(frame, text="Max Total Share Size (GB):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.max_total_size = ttk.Entry(frame, width=20)
        self.max_total_size.insert(0, str(CONFIG.get('max_total_share_size_gb', 50)))
        self.max_total_size.grid(row=2, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame, text="(Default: 50 GB)", foreground="gray").grid(row=2, column=2, sticky=tk.W, pady=5)
        
        # Show warnings
        self.show_warnings = tk.BooleanVar(value=CONFIG.get('show_file_size_warning', True))
        ttk.Checkbutton(frame, text="Show file size warnings", variable=self.show_warnings).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # Info label
        info_frame = ttk.LabelFrame(parent, text="Information", padding="10")
        info_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        info_text = "File size limits control which files can be added to sharing.\n" \
                   "Larger limits allow bigger files but may impact performance."
        ttk.Label(info_frame, text=info_text, wraplength=550, justify=tk.LEFT).pack()
    
    def create_performance_settings(self, parent):
        """Create performance settings"""
        frame = ttk.LabelFrame(parent, text="Multi-Threaded Downloads", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Enable multi-threading
        self.enable_multithread = tk.BooleanVar(value=CONFIG.get('enable_multithreaded_download', True))
        ttk.Checkbutton(frame, text="Enable multi-threaded downloads", variable=self.enable_multithread,
                       command=self.toggle_multithread).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # Max threads
        ttk.Label(frame, text="Maximum Download Threads:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.max_threads = ttk.Spinbox(frame, from_=1, to=16, width=18)
        self.max_threads.set(CONFIG.get('max_download_threads', 4))
        self.max_threads.grid(row=1, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame, text="(Recommended: 4-8)", foreground="gray").grid(row=1, column=2, sticky=tk.W, pady=5)
        
        # Min file size for multi-threading
        ttk.Label(frame, text="Min File Size for Multi-thread (MB):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.min_multithread_size = ttk.Entry(frame, width=20)
        min_size_mb = CONFIG.get('min_file_size_for_multithread', 10485760) / (1024 * 1024)
        self.min_multithread_size.insert(0, str(int(min_size_mb)))
        self.min_multithread_size.grid(row=2, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame, text="(Default: 10 MB)", foreground="gray").grid(row=2, column=2, sticky=tk.W, pady=5)
        
        # Thread chunk size
        ttk.Label(frame, text="Thread Chunk Size (MB):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.thread_chunk_size = ttk.Entry(frame, width=20)
        chunk_size_mb = CONFIG.get('thread_chunk_size', 2097152) / (1024 * 1024)
        self.thread_chunk_size.insert(0, str(int(chunk_size_mb)))
        self.thread_chunk_size.grid(row=3, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame, text="(Default: 2 MB)", foreground="gray").grid(row=3, column=2, sticky=tk.W, pady=5)
        
        # Max concurrent downloads
        ttk.Label(frame, text="Max Concurrent Downloads:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.max_concurrent = ttk.Spinbox(frame, from_=1, to=20, width=18)
        self.max_concurrent.set(CONFIG.get('max_concurrent_downloads', 5))
        self.max_concurrent.grid(row=4, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame, text="(Default: 5)", foreground="gray").grid(row=4, column=2, sticky=tk.W, pady=5)
        
        # Info
        info_frame = ttk.LabelFrame(parent, text="Performance Tips", padding="10")
        info_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        info_text = "• More threads = faster downloads for large files\n" \
                   "• 4 threads recommended for WiFi, 8 for Gigabit Ethernet\n" \
                   "• Larger chunk sizes may improve speed on fast networks"
        ttk.Label(info_frame, text=info_text, wraplength=550, justify=tk.LEFT).pack()
    
    def create_network_settings(self, parent):
        """Create network settings"""
        frame = ttk.LabelFrame(parent, text="Network Optimization", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # TCP buffer size
        ttk.Label(frame, text="TCP Buffer Size (KB):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.tcp_buffer = ttk.Entry(frame, width=20)
        buffer_kb = CONFIG.get('tcp_buffer_size', 262144) / 1024
        self.tcp_buffer.insert(0, str(int(buffer_kb)))
        self.tcp_buffer.grid(row=0, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame, text="(Default: 256 KB)", foreground="gray").grid(row=0, column=2, sticky=tk.W, pady=5)
        
        # Download timeout
        ttk.Label(frame, text="Download Timeout (seconds):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.download_timeout = ttk.Entry(frame, width=20)
        self.download_timeout.insert(0, str(CONFIG.get('download_timeout', 300)))
        self.download_timeout.grid(row=1, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame, text="(Default: 300s = 5 min)", foreground="gray").grid(row=1, column=2, sticky=tk.W, pady=5)
        
        # Connection timeout
        ttk.Label(frame, text="Connection Timeout (seconds):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.connection_timeout = ttk.Entry(frame, width=20)
        self.connection_timeout.insert(0, str(CONFIG.get('connection_timeout', 30)))
        self.connection_timeout.grid(row=2, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame, text="(Default: 30s)", foreground="gray").grid(row=2, column=2, sticky=tk.W, pady=5)
        
        # TCP optimizations
        self.tcp_nodelay = tk.BooleanVar(value=CONFIG.get('enable_tcp_nodelay', True))
        ttk.Checkbutton(frame, text="Enable TCP_NODELAY (lower latency)", 
                       variable=self.tcp_nodelay).grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        self.tcp_keepalive = tk.BooleanVar(value=CONFIG.get('enable_keepalive', True))
        ttk.Checkbutton(frame, text="Enable TCP keepalive (stable connections)", 
                       variable=self.tcp_keepalive).grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # Info
        info_frame = ttk.LabelFrame(parent, text="Network Information", padding="10")
        info_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        info_text = "• Larger TCP buffer = better throughput on fast networks\n" \
                   "• Increase timeouts for slow/unstable connections\n" \
                   "• TCP_NODELAY recommended for LAN transfers"
        ttk.Label(info_frame, text=info_text, wraplength=550, justify=tk.LEFT).pack()
    
    def create_advanced_settings(self, parent):
        """Create advanced settings"""
        frame = ttk.LabelFrame(parent, text="Chunk Sizes", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Small chunk
        ttk.Label(frame, text="Small Files Chunk (KB):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.chunk_small = ttk.Entry(frame, width=20)
        chunk_kb = CONFIG.get('chunk_size_small', 8192) / 1024
        self.chunk_small.insert(0, str(int(chunk_kb)))
        self.chunk_small.grid(row=0, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame, text="(< 10 MB files)", foreground="gray").grid(row=0, column=2, sticky=tk.W, pady=5)
        
        # Medium chunk
        ttk.Label(frame, text="Medium Files Chunk (KB):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.chunk_medium = ttk.Entry(frame, width=20)
        chunk_kb = CONFIG.get('chunk_size_medium', 65536) / 1024
        self.chunk_medium.insert(0, str(int(chunk_kb)))
        self.chunk_medium.grid(row=1, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame, text="(10-100 MB files)", foreground="gray").grid(row=1, column=2, sticky=tk.W, pady=5)
        
        # Large chunk
        ttk.Label(frame, text="Large Files Chunk (KB):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.chunk_large = ttk.Entry(frame, width=20)
        chunk_kb = CONFIG.get('chunk_size_large', 524288) / 1024
        self.chunk_large.insert(0, str(int(chunk_kb)))
        self.chunk_large.grid(row=2, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame, text="(100 MB - 1 GB files)", foreground="gray").grid(row=2, column=2, sticky=tk.W, pady=5)
        
        # XLarge chunk
        ttk.Label(frame, text="Huge Files Chunk (MB):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.chunk_xlarge = ttk.Entry(frame, width=20)
        chunk_mb = CONFIG.get('chunk_size_xlarge', 1048576) / (1024 * 1024)
        self.chunk_xlarge.insert(0, str(int(chunk_mb)))
        self.chunk_xlarge.grid(row=3, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame, text="(> 1 GB files)", foreground="gray").grid(row=3, column=2, sticky=tk.W, pady=5)
        
        # Other settings
        other_frame = ttk.LabelFrame(parent, text="Other Settings", padding="10")
        other_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Label(other_frame, text="Auto-refresh Interval (seconds):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.auto_refresh = ttk.Entry(other_frame, width=20)
        self.auto_refresh.insert(0, str(CONFIG.get('auto_refresh_interval', 30)))
        self.auto_refresh.grid(row=0, column=1, sticky=tk.W, pady=5, padx=10)
        
        # Warning
        warning_frame = ttk.LabelFrame(parent, text="⚠️ Warning", padding="10")
        warning_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        warning_text = "Advanced settings should only be changed if you understand their impact.\n" \
                      "Incorrect values may degrade performance or cause errors."
        ttk.Label(warning_frame, text=warning_text, wraplength=550, justify=tk.LEFT, foreground="red").pack()
    
    def toggle_multithread(self):
        """Toggle multi-threading related controls"""
        state = tk.NORMAL if self.enable_multithread.get() else tk.DISABLED
        self.max_threads.config(state=state)
        self.min_multithread_size.config(state=state)
        self.thread_chunk_size.config(state=state)
    
    def validate_settings(self):
        """Validate all settings before saving"""
        try:
            # Validate file sizes
            max_file = int(self.max_file_size.get())
            warn_file = int(self.warn_file_size.get())
            max_total = int(self.max_total_size.get())
            
            if max_file <= 0 or warn_file <= 0 or max_total <= 0:
                raise ValueError("File sizes must be positive numbers")
            
            if warn_file > max_file:
                raise ValueError("Warning threshold cannot exceed maximum file size")
            
            # Validate performance settings
            max_threads = int(self.max_threads.get())
            if max_threads < 1 or max_threads > 16:
                raise ValueError("Max threads must be between 1 and 16")
            
            min_multithread = int(self.min_multithread_size.get())
            if min_multithread < 1:
                raise ValueError("Min file size for multi-threading must be positive")
            
            thread_chunk = int(self.thread_chunk_size.get())
            if thread_chunk < 1:
                raise ValueError("Thread chunk size must be positive")
            
            max_concurrent = int(self.max_concurrent.get())
            if max_concurrent < 1 or max_concurrent > 20:
                raise ValueError("Max concurrent downloads must be between 1 and 20")
            
            # Validate network settings
            tcp_buffer = int(self.tcp_buffer.get())
            if tcp_buffer < 8 or tcp_buffer > 2048:
                raise ValueError("TCP buffer size must be between 8 KB and 2048 KB")
            
            download_timeout = int(self.download_timeout.get())
            if download_timeout < 10 or download_timeout > 3600:
                raise ValueError("Download timeout must be between 10 and 3600 seconds")
            
            connection_timeout = int(self.connection_timeout.get())
            if connection_timeout < 5 or connection_timeout > 300:
                raise ValueError("Connection timeout must be between 5 and 300 seconds")
            
            # Validate chunk sizes
            chunk_small = int(self.chunk_small.get())
            chunk_medium = int(self.chunk_medium.get())
            chunk_large = int(self.chunk_large.get())
            chunk_xlarge = int(self.chunk_xlarge.get())
            
            if any(c <= 0 for c in [chunk_small, chunk_medium, chunk_large, chunk_xlarge]):
                raise ValueError("Chunk sizes must be positive numbers")
            
            auto_refresh = int(self.auto_refresh.get())
            if auto_refresh < 5 or auto_refresh > 300:
                raise ValueError("Auto-refresh interval must be between 5 and 300 seconds")
            
            return True
            
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e), parent=self.window)
            return False
    
    def save_settings(self):
        """Save settings to config file"""
        if not self.validate_settings():
            return
        
        try:
            # Update CONFIG dictionary
            CONFIG['max_file_size_mb'] = int(self.max_file_size.get())
            CONFIG['warn_file_size_mb'] = int(self.warn_file_size.get())
            CONFIG['max_total_share_size_gb'] = int(self.max_total_size.get())
            CONFIG['show_file_size_warning'] = self.show_warnings.get()
            
            CONFIG['enable_multithreaded_download'] = self.enable_multithread.get()
            CONFIG['max_download_threads'] = int(self.max_threads.get())
            CONFIG['min_file_size_for_multithread'] = int(self.min_multithread_size.get()) * 1024 * 1024
            CONFIG['thread_chunk_size'] = int(self.thread_chunk_size.get()) * 1024 * 1024
            CONFIG['max_concurrent_downloads'] = int(self.max_concurrent.get())
            
            CONFIG['tcp_buffer_size'] = int(self.tcp_buffer.get()) * 1024
            CONFIG['download_timeout'] = int(self.download_timeout.get())
            CONFIG['connection_timeout'] = int(self.connection_timeout.get())
            CONFIG['enable_tcp_nodelay'] = self.tcp_nodelay.get()
            CONFIG['enable_keepalive'] = self.tcp_keepalive.get()
            
            CONFIG['chunk_size_small'] = int(self.chunk_small.get()) * 1024
            CONFIG['chunk_size_medium'] = int(self.chunk_medium.get()) * 1024
            CONFIG['chunk_size_large'] = int(self.chunk_large.get()) * 1024
            CONFIG['chunk_size_xlarge'] = int(self.chunk_xlarge.get()) * 1024 * 1024
            CONFIG['auto_refresh_interval'] = int(self.auto_refresh.get())
            
            # Save to file
            save_config_to_file()
            
            messagebox.showinfo("Success", "Settings saved successfully!\n\nSome settings may require restarting the application to take effect.", parent=self.window)
            self.window.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}", parent=self.window)
    
    def cancel(self):
        """Cancel and close window"""
        # Restore original config
        CONFIG.update(self.original_config)
        self.window.destroy()
    
    def reset_defaults(self):
        """Reset all settings to defaults"""
        if messagebox.askyesno("Reset to Defaults", 
                              "Are you sure you want to reset all settings to their default values?",
                              parent=self.window):
            # Reset to defaults
            self.max_file_size.delete(0, tk.END)
            self.max_file_size.insert(0, "10240")
            
            self.warn_file_size.delete(0, tk.END)
            self.warn_file_size.insert(0, "1024")
            
            self.max_total_size.delete(0, tk.END)
            self.max_total_size.insert(0, "50")
            
            self.show_warnings.set(True)
            self.enable_multithread.set(True)
            
            self.max_threads.set(4)
            
            self.min_multithread_size.delete(0, tk.END)
            self.min_multithread_size.insert(0, "10")
            
            self.thread_chunk_size.delete(0, tk.END)
            self.thread_chunk_size.insert(0, "2")
            
            self.max_concurrent.set(5)
            
            self.tcp_buffer.delete(0, tk.END)
            self.tcp_buffer.insert(0, "256")
            
            self.download_timeout.delete(0, tk.END)
            self.download_timeout.insert(0, "300")
            
            self.connection_timeout.delete(0, tk.END)
            self.connection_timeout.insert(0, "30")
            
            self.tcp_nodelay.set(True)
            self.tcp_keepalive.set(True)
            
            self.chunk_small.delete(0, tk.END)
            self.chunk_small.insert(0, "8")
            
            self.chunk_medium.delete(0, tk.END)
            self.chunk_medium.insert(0, "64")
            
            self.chunk_large.delete(0, tk.END)
            self.chunk_large.insert(0, "512")
            
            self.chunk_xlarge.delete(0, tk.END)
            self.chunk_xlarge.insert(0, "1")
            
            self.auto_refresh.delete(0, tk.END)
            self.auto_refresh.insert(0, "30")
            
            messagebox.showinfo("Reset Complete", "All settings have been reset to default values.\nClick 'Save' to apply changes.", parent=self.window)

def open_settings(parent):
    """Open the settings window"""
    SettingsWindow(parent)
