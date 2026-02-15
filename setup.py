#!/usr/bin/env python3
"""
Setup script for Windows LAN File Share Utility
Creates desktop shortcut and registers file associations
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def create_desktop_shortcut():
    """Create desktop shortcut for the application"""
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        path = os.path.join(desktop, "LAN File Share.lnk")
        target = os.path.join(os.getcwd(), "start.bat")
        wDir = os.getcwd()
        icon = target
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = wDir
        shortcut.IconLocation = icon
        shortcut.save()
        
        print("Desktop shortcut created successfully!")
        return True
    except ImportError:
        print("Could not create desktop shortcut - missing pywin32")
        print("Install with: pip install pywin32")
        return False
    except Exception as e:
        print(f"Failed to create desktop shortcut: {e}")
        return False

def add_to_path():
    """Add application directory to Windows PATH"""
    try:
        current_dir = os.getcwd()
        
        # Get current PATH
        result = subprocess.run(['echo', '%PATH%'], shell=True, capture_output=True, text=True)
        current_path = result.stdout.strip()
        
        if current_dir not in current_path:
            print(f"To add {current_dir} to PATH:")
            print("1. Press Windows key, type 'environment variables'")
            print("2. Click 'Edit the system environment variables'")
            print("3. Click 'Environment Variables...'")
            print("4. Under 'System variables', find 'Path' and click 'Edit...'")
            print("5. Click 'New' and add the following path:")
            print(f"   {current_dir}")
            print("6. Click OK on all windows")
        else:
            print("Application directory is already in PATH")
            
    except Exception as e:
        print(f"Error checking PATH: {e}")

def install_dependencies():
    """Install optional dependencies for enhanced features"""
    optional_deps = [
        'pywin32',  # For desktop shortcuts
        'pillow',   # For image thumbnails
        'psutil',   # For system information
        'requests'  # For enhanced HTTP client
    ]
    
    print("Installing optional dependencies for enhanced features...")
    for dep in optional_deps:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', dep], 
                         check=True, capture_output=True)
            print(f"✓ Installed {dep}")
        except subprocess.CalledProcessError:
            print(f"✗ Failed to install {dep}")

def check_python_version():
    """Check Python version compatibility"""
    if sys.version_info < (3, 6):
        print("Error: Python 3.6 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    else:
        print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")
        return True

def check_tkinter():
    """Check if tkinter is available"""
    try:
        import tkinter
        print("✓ tkinter is available")
        return True
    except ImportError:
        print("✗ tkinter is not available")
        print("Install tkinter with:")
        print("  python -m pip install tk")
        return False

def create_config_file():
    """Create default configuration file"""
    config = {
        'default_port': 8000,
        'discovery_port': 8001,
        'max_file_size_mb': 100,
        'enable_security': False,
        'log_access': True,
        'rate_limit_per_minute': 60
    }
    
    try:
        import json
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)
        print("✓ Default configuration file created")
    except Exception as e:
        print(f"Failed to create config file: {e}")

def main():
    """Main setup function"""
    print("=== Windows LAN File Share Setup ===")
    print()
    
    # Check requirements
    print("Checking requirements...")
    python_ok = check_python_version()
    tkinter_ok = check_tkinter()
    
    if not python_ok or not tkinter_ok:
        print("\nSetup failed due to missing requirements")
        return
    
    print()
    
    # Create configuration
    print("Creating configuration...")
    create_config_file()
    
    # Install optional dependencies
    print("\nInstalling optional dependencies...")
    response = input("Install optional dependencies? (y/n): ").lower().strip()
    if response in ['y', 'yes']:
        install_dependencies()
    
    # Create desktop shortcut
    print("\nCreating desktop shortcut...")
    response = input("Create desktop shortcut? (y/n): ").lower().strip()
    if response in ['y', 'yes']:
        create_desktop_shortcut()
    
    # PATH instructions
    print("\nPATH configuration...")
    add_to_path()
    
    print("\n=== Setup Complete ===")
    print("\nTo run the application:")
    print("  1. Double-click start.bat")
    print("  2. Or run: python main.py")
    print("  3. Or use the desktop shortcut (if created)")
    print("\nFor help and documentation, see README.md")

if __name__ == "__main__":
    main()
