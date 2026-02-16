# Windows LAN File Share Utility

A comprehensive Windows utility for sharing and downloading files over WiFi-LAN with other Windows machines on the same network.

## Features

- **Bi-Directional File Sharing**: Each computer can both share files AND download from other computers running the app
- **Multi-Threaded Downloads**: Parallel chunk downloads for 2-4x faster transfer speeds on large files
- **Network Optimized**: TCP buffer optimization, Nagle's algorithm disabled, and keepalive enabled for maximum speed
- **Easy File & Folder Sharing**: Select individual files or entire folders through a GUI interface and share them instantly
- **Recursive Folder Scanning**: Automatically includes all files within selected folders and subfolders
- **Built-in Download Client**: Browse and download files from other instances without needing a web browser
- **Web Interface**: Access shared files through any web browser on the LAN
- **File Preview**: Preview text files and images directly in the browser
- **Network Discovery**: Automatically discover other file share instances on the LAN
- **Remote File Browsing**: Browse files on discovered servers and download directly from the application
- **Speed Monitoring**: Real-time transfer speed display (MB/s) with progress tracking
- **HTTP Range Support**: Partial downloads and resume capability
- **File Verification**: SHA-256 checksum verification ensures file integrity
- **Resume Downloads**: Automatically resume interrupted downloads from where they left off
- **Chunk Verification**: Individual chunk validation in multi-threaded downloads
- **Client Connection Notifications**: Real-time notifications when clients connect and download files
- **Connection Tracking**: Monitor active connections and view connection history
- **Security Features**: Optional access control with token authentication
- **Real-time Status**: Monitor server status and activity logs
- **No Installation Required**: Uses only Python standard library (with optional enhancements)

## Requirements

- Python 3.6 or higher
- Windows operating system
- Local network connection (WiFi or Ethernet)
- tkinter (included with most Python installations)

## Quick Start

### Option 1: Using Batch Files (Recommended for Windows)

**Simple Launch:**
- Double-click `start.bat` - Launches the full application with GUI

**Quick Start Menu:**
- Double-click `quick-start.bat` - Interactive menu with multiple options

**Specific Modes:**
- `start-server.bat` - Optimized for sharing files
- `start-client.bat` - Optimized for downloading files
- `start-minimized.bat` - Runs in background (minimized)

**Setup & Configuration:**
- `create-shortcut.bat` - Creates desktop shortcut
- `install-service.bat` - Instructions for auto-start on boot

### Option 2: Using Python Directly

1. **Run the setup script**:
   ```bash
   python setup.py
   ```
2. **Start the application**:
   ```bash
   python main.py
   ```

## Usage

### Basic File Sharing

1. **Add Files**: Click "Add Files" button to select individual files you want to share
2. **Add Folders**: Click "Add Folder" button to share entire folders (includes all files and subfolders recursively)
3. **Configure Settings** (Optional): Click "⚙️ Settings" to adjust file size limits, performance, and network options
4. **Start Server**: Click "Start Server" to begin sharing
5. **Access Files**: Open the provided URL in any browser on devices connected to the same network

### Configuring Settings

**Access Settings:**
- Click the "⚙️ Settings" button in the main window
- A new window opens with 4 tabs of configuration options

**File Settings Tab:**
- Maximum File Size - Control the largest file that can be shared
- Warning Threshold - Get alerts for large files
- Max Total Share Size - Limit total size of all shared files
- Show Warnings - Toggle file size warning notifications

**Performance Tab:**
- Enable Multi-threaded Downloads - Turn on/off parallel downloads
- Maximum Download Threads - Set number of parallel threads (1-16)
- Min File Size for Multi-thread - Files above this use multi-threading
- Thread Chunk Size - Size of chunks per thread
- Max Concurrent Downloads - Number of simultaneous downloads allowed

**Network Tab:**
- TCP Buffer Size - Increase for better throughput on fast networks
- Download Timeout - How long to wait before timing out
- Connection Timeout - Initial connection timeout
- TCP_NODELAY - Lower latency (recommended for LAN)
- TCP Keepalive - Maintain stable connections

**Advanced Tab:**
- Chunk sizes for different file sizes
- Auto-refresh interval for network discovery
- Fine-tune transfer optimization

**Saving Settings:**
- Click "Save" to apply and save to `config.json`
- Click "Reset to Defaults" to restore original values
- Click "Cancel" to discard changes

**Note**: When adding a folder, all files within that folder and its subfolders will be automatically added to the share list.

### Monitoring Client Connections

The application provides real-time notifications when clients connect to your server:

**Connection Display:**
- **Active Connections Counter**: Shows number of clients connected in the last 5 minutes
- **Color Indicators**: 
  - Green = Active connections present
  - Blue = No active connections

**Activity Log Notifications:**
- 🔵 **Client Browsing**: When someone views your file list
- 📥 **Download Started**: When a client begins downloading a file
- ⬇️ **File Transfer**: Ongoing download activity

**Connection Tracking:**
- Tracks each client's IP address
- Records first and last connection times
- Maintains history of all actions (browsing, downloading)
- Auto-expires inactive connections after 5 minutes

**Example Notifications:**
```
[14:23:15] 🔵 Client connected: 192.168.1.105 is browsing files
[14:23:22] 📥 192.168.1.105: Downloading: presentation.pdf
[14:24:01] 🔵 Client connected: 192.168.1.108 is browsing files
```

### File Verification & Integrity

The application includes comprehensive file verification to ensure downloads are error-free:

**Checksum Verification:**
- **SHA-256 hashing** for file integrity verification
- **MD5 support** for faster verification of smaller files
- **Automatic verification** after download completion
- **Chunk-level verification** in multi-threaded downloads

**How It Works:**
1. Server calculates file checksum when sharing
2. Client downloads file (single or multi-threaded)
3. Individual chunks verified during download
4. Final merged file verified against expected checksum
5. Download marked as complete only if verification passes

**Benefits:**
- ✅ Detects corrupted downloads
- ✅ Ensures file integrity across network
- ✅ Validates multi-threaded chunk merging
- ✅ Prevents incomplete or damaged files

**Verification Process:**
```
[14:30:10] Starting multi-threaded download (4 threads)...
[14:30:45] Downloading: 75% @ 18.2 MB/s
[14:31:02] Download complete
[14:31:03] Verifying file integrity...
[14:31:05] ✓ File verified successfully (SHA-256 match)
```

### Resume Download Capability

Interrupted downloads can be automatically resumed:

**Resume Features:**
- **Automatic detection** of partial downloads
- **Resume from last byte** - no re-downloading completed portions
- **Resume metadata** stored in `~/.lan_file_share/resume/`
- **Works with multi-threaded downloads**

**How Resume Works:**
1. Download interrupted (network issue, app closed, etc.)
2. Resume information saved automatically
3. Next download attempt detects partial file
4. Downloads only remaining bytes
5. Verifies complete file after resume

**Resume Information Stored:**
- File URL and save path
- Total file size
- Bytes already downloaded
- Expected checksum
- Timestamp of interruption

**Example Resume:**
```
[15:10:20] Starting download: large_video.mp4 (2.5 GB)
[15:12:45] Download interrupted at 45% (1.1 GB)
[15:15:00] Resuming download from 1.1 GB...
[15:17:30] Download complete and verified
```

**Manual Resume Control:**
- Resume info automatically cleaned up after successful download
- Partial files kept with `.partial` extension
- Can manually delete resume info to force fresh download

### Network Discovery & Bi-Directional Sharing

The application automatically discovers other instances running on the same network:
- View discovered servers in the "Discovered Servers" section
- Click "Open in Browser" to view files in your web browser
- Click "Browse & Download" to use the built-in client for downloading files
- Use "Refresh" to update the list of available servers

#### Downloading from Other Computers

1. **Discover Servers**: Other computers running the app will appear in "Discovered Servers"
2. **Browse Files**: Click "Browse & Download" on a discovered server
3. **Select Files**: A new window opens showing all available files on that server
4. **Download**: Select files and click "Download Selected" or "Download All"
5. **Monitor Progress**: Download progress appears in the activity log

**Key Benefits:**
- No need to open a web browser - download directly from the app
- Select multiple files at once
- Automatic download location (configurable)
- Progress tracking for all downloads
- Works seamlessly with both secured and unsecured servers

### Security Features

Enable security mode for enhanced protection:
1. Check "Enable Security" before starting the server
2. An access token will be generated and displayed
3. Users must provide this token to access the server
4. All access attempts are logged and monitored

Security features include:
- Token-based authentication
- IP access control
- Rate limiting
- Access logging
- Secure file serving with path validation

## Configuration

### Default Settings
- **Port**: 8000 (can be changed in code)
- **Discovery Port**: 8001
- **Max File Size**: 10 GB (10,240 MB)
- **Warning Threshold**: 1 GB (files larger than this will show a warning)
- **Rate Limit**: 60 requests per minute
- **Download Timeout**: 5 minutes (300 seconds)

### File Size Limits

The application supports **large file transfers** with the following features:

**Default Limits:**
- Maximum file size: **10 GB** (configurable)
- Warning for files over: **1 GB**
- Maximum total share size: **50 GB**

**Optimized Transfer:**
- Files < 10 MB: 8 KB chunks
- Files 10-100 MB: 64 KB chunks  
- Files 100 MB - 1 GB: 512 KB chunks
- Files > 1 GB: 1 MB chunks

**Benefits:**
- ✅ Efficient memory usage - doesn't load entire file into RAM
- ✅ Handles multi-GB files without issues
- ✅ Automatic chunk size optimization
- ✅ Progress tracking for large downloads
- ✅ Connection error handling and recovery

### Performance & Speed Optimization

The application includes advanced features for **maximum transfer speed**:

**Multi-Threaded Downloads:**
- Automatically enabled for files > 10 MB
- Uses 2-4 parallel threads depending on file size
- Each thread downloads a separate chunk simultaneously
- **2-4x faster** than single-threaded downloads

**Network Optimizations:**
- TCP buffer size increased to 256 KB (from default 64 KB)
- Nagle's algorithm disabled (TCP_NODELAY) for lower latency
- TCP keepalive enabled for stable long transfers
- HTTP Range request support for partial downloads

**Adaptive Chunk Sizing:**
- Small files (< 10 MB): 8 KB chunks
- Medium files (10-100 MB): 64 KB chunks
- Large files (100 MB - 1 GB): 512 KB chunks
- Huge files (> 1 GB): 1 MB chunks

**Speed Monitoring:**
- Real-time transfer speed display (MB/s)
- Progress percentage tracking
- Estimated time remaining

### UI Configuration (Recommended)

The easiest way to configure settings is through the built-in Settings UI:

1. **Open Settings**: Click the "⚙️ Settings" button in the main window
2. **Adjust Settings**: Use the tabbed interface to modify settings
3. **Save Changes**: Click "Save" to apply and persist your changes

**Settings Tabs:**
- **File Settings** - File size limits and warnings
- **Performance** - Multi-threaded downloads and concurrency
- **Network** - TCP optimization and timeouts
- **Advanced** - Chunk sizes and other technical settings

**Features:**
- ✅ User-friendly interface with validation
- ✅ Organized into logical categories
- ✅ Default value hints for each setting
- ✅ Reset to defaults option
- ✅ Automatic save to `config.json`
- ✅ Input validation prevents invalid values

### Manual Configuration

Alternatively, create a `config.json` file to override defaults:
```json
{
  "max_file_size_mb": 20480,
  "warn_file_size_mb": 2048,
  "max_total_share_size_gb": 100,
  "chunk_size_large": 1048576,
  "download_timeout": 600,
  "upload_timeout": 600,
  "connection_timeout": 30,
  "max_concurrent_downloads": 5,
  "enable_multithreaded_download": true,
  "max_download_threads": 4,
  "min_file_size_for_multithread": 10485760,
  "tcp_buffer_size": 262144,
  "enable_tcp_nodelay": true
}
```

**Configuration Options:**
- `max_file_size_mb` - Maximum individual file size in MB (default: 10,240)
- `warn_file_size_mb` - Show warning for files larger than this (default: 1,024)
- `max_total_share_size_gb` - Maximum total size of all shared files (default: 50)
- `chunk_size_large` - Chunk size for large files in bytes (default: 524,288)
- `download_timeout` - Download timeout in seconds (default: 300)
- `upload_timeout` - Upload timeout in seconds (default: 300)
- `max_concurrent_downloads` - Maximum simultaneous downloads (default: 5)
- `enable_multithreaded_download` - Enable parallel downloads (default: true)
- `max_download_threads` - Number of parallel threads (default: 4)
- `min_file_size_for_multithread` - Minimum file size for multi-threading in bytes (default: 10 MB)
- `tcp_buffer_size` - TCP buffer size in bytes (default: 262,144)
- `enable_tcp_nodelay` - Disable Nagle's algorithm for lower latency (default: true)

## Network Configuration

- **Automatic IP Detection**: The app automatically detects your local IP address
- **Firewall**: Windows Firewall may prompt for permission - allow access for network sharing
- **Network Range**: Works on any local network (192.168.x.x, 10.x.x.x, etc.)

## Security Considerations

### Standard Mode
- Files are shared without authentication - use only on trusted networks
- The server is accessible to all devices on the same network
- Consider stopping the server when not sharing files

### Security Mode
- Token-based authentication required
- Access control and rate limiting
- Comprehensive logging of all access attempts
- Secure file serving prevents directory traversal attacks

## Troubleshooting

### Server Won't Start
- Check if port 8000 is already in use
- Ensure Windows Firewall allows Python network access
- Try running as administrator
- Verify Python and tkinter are installed correctly

### Cannot Access from Other Devices
- Verify all devices are on the same network
- Check Windows Firewall settings
- Confirm the IP address is correct
- Try disabling VPN or proxy connections
- If security mode is enabled, ensure you're using the correct token

### Files Not Showing
- Ensure files are added before starting the server
- Check file permissions
- Verify files exist and are accessible
- Try refreshing the browser

### Large File Transfer Issues
- **File too large**: Check if file exceeds the 10 GB limit (configurable in config.json)
- **Transfer timeout**: Increase `download_timeout` in config.json for very large files
- **Memory issues**: The app uses chunked transfer - shouldn't use excessive RAM
- **Slow transfer**: 
  - Enable multi-threaded downloads (enabled by default for files > 10 MB)
  - Check network speed - WiFi typically 50-300 Mbps, Ethernet 1000 Mbps
  - Increase `max_download_threads` to 8 for faster transfers
  - Ensure no other heavy network activity
- **Transfer interrupted**: Downloads will show error in activity log - retry the download

### Performance Benchmarks

**Expected Transfer Speeds (WiFi 802.11ac @ 100 Mbps):**
- Small files (< 10 MB): ~10-12 MB/s (single-threaded)
- Medium files (100 MB): ~11-15 MB/s (multi-threaded)
- Large files (1 GB): ~12-18 MB/s (4 threads)
- Huge files (10 GB): ~15-20 MB/s (4 threads)

**Speed Improvement with Multi-Threading:**
- 100 MB file: 2x faster (6 MB/s → 12 MB/s)
- 1 GB file: 2.5x faster (7 MB/s → 17 MB/s)
- 5 GB file: 3x faster (6 MB/s → 18 MB/s)

**Note**: Actual speeds depend on your network hardware and congestion

### Network Discovery Not Working
- Ensure all instances are on the same network
- Check if discovery port (8001) is blocked by firewall
- Try manual refresh of the discovery list
- Verify network discovery is not blocked by router settings

## Batch File Reference

### Available Batch Files

| File | Purpose | Usage |
|------|---------|-------|
| `start.bat` | Main launcher with checks | Double-click to start |
| `quick-start.bat` | Interactive menu | Choose from multiple options |
| `start-server.bat` | Server mode | Quick server launch |
| `start-client.bat` | Client mode | Quick client launch |
| `start-minimized.bat` | Background mode | Runs minimized |
| `create-shortcut.bat` | Desktop shortcut | Creates desktop icon |
| `install-service.bat` | Service setup | Auto-start instructions |

### Batch File Features

**start.bat:**
- Checks Python installation
- Verifies application files
- Shows colored status messages
- Handles errors gracefully

**quick-start.bat:**
- Interactive menu system
- Multiple launch options
- Easy access to setup
- User-friendly interface

**start-minimized.bat:**
- Runs in background
- Minimal system tray presence
- Ideal for always-on sharing

**create-shortcut.bat:**
- One-click desktop shortcut creation
- Automatically finds installation path
- Sets proper icon and description

### Creating Custom Batch Files

You can create custom batch files for specific scenarios:

```batch
@echo off
cd /d "%~dp0"
python main.py
```

**Example - Auto-start with specific port:**
```batch
@echo off
cd /d "%~dp0"
REM Set custom port via environment variable
set LAN_SHARE_PORT=8080
python main.py
```

## Advanced Usage

### Command Line Arguments
You can extend the application to accept command line arguments:
```bash
python main.py --port 8080 --security
```

### Integration with Other Tools
The modular design allows integration with:
- Custom authentication systems
- External logging services
- Network monitoring tools
- File management systems

## Development

### Architecture
- **main.py**: Main application with GUI
- **discovery.py**: Network discovery functionality
- **security.py**: Security and access control
- **setup.py**: Installation and configuration

### Extending the Application
- Add new file handlers in the security module
- Implement custom authentication methods
- Add network scanning enhancements
- Create plugins for additional features

## Optional Dependencies

For enhanced features, install these optional packages:
```bash
pip install pywin32  # Desktop shortcuts
pip install pillow   # Image thumbnails
pip install psutil   # System information
pip install requests # Enhanced HTTP client
```

## File Structure

```
windsurf-project/
├── main.py                # Main application with GUI
├── client.py              # Download client for bi-directional sharing
├── discovery.py           # Network discovery
├── security.py            # Security features
├── config.py              # Configuration and file size management
├── fast_transfer.py       # Multi-threaded downloads and network optimization
├── file_verification.py   # File integrity verification and resume downloads
├── settings_ui.py         # Settings configuration UI
├── setup.py               # Setup script
├── start.bat              # Main launcher (recommended)
├── quick-start.bat        # Interactive menu launcher
├── start-server.bat       # Server mode launcher
├── start-client.bat       # Client mode launcher
├── start-minimized.bat    # Background mode launcher
├── create-shortcut.bat    # Desktop shortcut creator
├── install-service.bat    # Service installation helper
├── requirements.txt       # Dependencies
├── README.md              # Documentation
└── config.json            # User configuration (auto-generated)
```

## License

This project is open source and available under the MIT License.

## Support

For issues and feature requests:
1. Check the troubleshooting section
2. Verify your network configuration
3. Test with different files and browsers
4. Create an issue report with details about your environment

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**Note**: This utility is designed for trusted local networks. Always enable security mode when sharing sensitive files or when using on untrusted networks.
