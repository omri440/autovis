#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Startup script for Algorithm Visualizer API Server
Checks dependencies and starts the server with proper configuration
"""

import sys
import subprocess
import os
from pathlib import Path


def check_dependencies():
    """Check if required modules are installed"""
    required = ['flask', 'flask_cors']
    missing = []

    for module in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)

    if missing:
        print("❌ Missing dependencies:")
        for mod in missing:
            print(f"   - {mod}")
        print("\n💡 Install them with:")
        print("   pip install -r requirements.txt")
        return False

    return True


def check_pipeline_modules():
    """Check if pipeline modules exist"""
    required_files = [
        'analyzer.py',
        'blueprint_generator.py',
        'code_combiner.py',
        'indentation_fixer.py',
        'translator.py',
        'api_server.py'
    ]

    missing = []
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)

    if missing:
        print("❌ Missing pipeline modules:")
        for file in missing:
            print(f"   - {file}")
        print("\n💡 Make sure you're running this from the project root directory")
        return False

    return True


def check_port(port=5000):
    """Check if port is available"""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except OSError:
            print(f"⚠️  Warning: Port {port} is already in use")
            print("   The server might already be running, or another app is using this port")
            response = input("\n   Continue anyway? (y/N): ")
            return response.lower() == 'y'


def print_banner():
    """Print startup banner"""
    print("\n" + "=" * 80)
    print(" " * 15 + "🎨 ALGORITHM VISUALIZER - STARTUP SCRIPT")
    print("=" * 80 + "\n")


def print_instructions():
    """Print usage instructions"""
    print("\n" + "=" * 80)
    print("📖 QUICK START GUIDE")
    print("=" * 80)
    print("\n1. Server Status:")
    print("   ✅ API server running on http://localhost:5000")
    print("\n2. Install Chrome Extension:")
    print("   • Open Chrome → chrome://extensions/")
    print("   • Enable 'Developer mode'")
    print("   • Click 'Load unpacked'")
    print("   • Select the 'chrome-extension' folder")
    print("\n3. Use the Extension:")
    print("   • Click extension icon in Chrome toolbar")
    print("   • Paste Python code")
    print("   • Click 'Convert to JavaScript'")
    print("   • Copy or download the result")
    print("\n4. Stop Server:")
    print("   • Press Ctrl+C in this terminal")
    print("\n" + "=" * 80 + "\n")


def start_server():
    """Start the Flask server"""
    print("🚀 Starting API server...\n")

    try:
        # Import and run the server
        from api_server import app

        print_instructions()

        app.run(
            host='0.0.0.0',
            port=5001,
            debug=False,  # Set to False for cleaner output
            threaded=True,
            use_reloader=False  # Prevent double startup
        )

    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("👋 Server stopped by user")
        print("=" * 80 + "\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    print_banner()

    print("🔍 Checking system requirements...\n")

    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher required")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    print("✅ Python version: OK")

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    print("✅ Dependencies: OK")

    # Check pipeline modules
    if not check_pipeline_modules():
        sys.exit(1)
    print("✅ Pipeline modules: OK")

    # Check port
    if not check_port():
        sys.exit(1)
    print("✅ Port 5000: Available")

    print("\n" + "=" * 80)

    # Start server
    start_server()


if __name__ == '__main__':
    main()