# Windows LAN File Share Utility

A comprehensive Windows utility for sharing and downloading files over WiFi-LAN with other Windows machines on the same network.

## Features

- **Bi-Directional File Sharing**: Each computer can both share files AND download from other computers running the app
- **Easy File & Folder Sharing**: Select individual files or entire folders through a GUI interface and share them instantly
- **Recursive Folder Scanning**: Automatically includes all files within selected folders and subfolders
- **Built-in Download Client**: Browse and download files from other instances without needing a web browser
- **Web Interface**: Access shared files through any web browser on the LAN
- **File Preview**: Preview text files and images directly in the browser
- **Network Discovery**: Automatically discover other file share instances on the LAN
- **Remote File Browsing**: Browse files on discovered servers and download directly from the application
- **Progress Tracking**: Monitor download progress in real-time
- **Security Features**: Optional access control with token authentication
- **Real-time Status**: Monitor server status and activity logs
- **No Installation Required**: Uses only Python standard library (with optional enhancements)

## Requirements

- Python 3.6 or higher
- Windows operating system
- Local network connection (WiFi or Ethernet)
- tkinter (included with most Python installations)

## Quick Start

1. **Download or clone** this repository
2. **Run the setup script**:
   ```bash
   python setup.py
   ```
3. **Start the application**:
   ```bash
   python main.py
   ```
   Or double-click `start.bat`

## Usage

### Basic File Sharing

1. **Add Files**: Click "Add Files" button to select individual files you want to share
2. **Add Folders**: Click "Add Folder" button to share entire folders (includes all files and subfolders recursively)
3. **Start Server**: Click "Start Server" to begin sharing
4. **Access Files**: Open the provided URL in any browser on devices connected to the same network

**Note**: When adding a folder, all files within that folder and its subfolders will be automatically added to the share list.

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
- **Max File Size**: 100MB
- **Rate Limit**: 60 requests per minute

### Custom Configuration
Create a `config.json` file to override defaults:
```json
{
  "default_port": 8080,
  "discovery_port": 8001,
  "max_file_size_mb": 100,
  "enable_security": false,
  "log_access": true,
  "rate_limit_per_minute": 60
}
```

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

### Network Discovery Not Working
- Ensure all instances are on the same network
- Check if discovery port (8001) is blocked by firewall
- Try manual refresh of the discovery list
- Verify network discovery is not blocked by router settings

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
├── main.py           # Main application with GUI
├── client.py         # Download client for bi-directional sharing
├── discovery.py      # Network discovery
├── security.py       # Security features
├── setup.py         # Setup script
├── start.bat        # Windows batch file
├── requirements.txt # Dependencies
├── README.md        # Documentation
└── config.json      # Configuration (optional)
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
