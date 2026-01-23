#!/usr/bin/env python3
"""
Installation Test Script for Ledger Scrolls Viewer

This script checks if all dependencies are installed correctly
and the viewer is ready to run.
"""

import sys
from pathlib import Path

def test_python_version():
    """Test Python version"""
    print("Testing Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 7:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - FAIL (need 3.7+)")
        return False

def test_import(module_name, package_name=None):
    """Test if a module can be imported"""
    package_name = package_name or module_name
    try:
        __import__(module_name)
        print(f"✅ {package_name} - OK")
        return True
    except ImportError:
        print(f"❌ {package_name} - NOT FOUND")
        return False

def test_core_dependencies():
    """Test core dependencies"""
    print("\nTesting core dependencies...")
    
    results = []
    results.append(test_import("tkinter"))
    results.append(test_import("requests"))
    results.append(test_import("cbor2"))
    
    return all(results)

def test_optional_dependencies():
    """Test optional dependencies"""
    print("\nTesting optional dependencies (for QR scanning)...")
    
    cv2_ok = test_import("cv2", "opencv-python")
    pyzbar_ok = test_import("pyzbar")
    
    if cv2_ok and pyzbar_ok:
        print("✅ QR code scanning available")
        return True
    else:
        print("⚠️  QR code scanning not available (optional)")
        print("   Install with: pip install opencv-python pyzbar")
        return False

def test_file_structure():
    """Test if viewer file exists"""
    print("\nTesting file structure...")
    
    viewer_path = Path("viewer_v2.py")
    if viewer_path.exists():
        print(f"✅ viewer_v2.py found")
        return True
    else:
        print(f"❌ viewer_v2.py not found")
        print(f"   Expected at: {viewer_path.absolute()}")
        return False

def test_permissions():
    """Test if viewer is executable"""
    print("\nTesting file permissions...")
    
    viewer_path = Path("viewer_v2.py")
    if not viewer_path.exists():
        print("⚠️  Skipping (file not found)")
        return True
    
    if viewer_path.stat().st_mode & 0o111:
        print("✅ viewer_v2.py is executable")
        return True
    else:
        print("⚠️  viewer_v2.py is not executable")
        print("   Make executable with: chmod +x viewer_v2.py")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Ledger Scrolls Viewer - Installation Test")
    print("=" * 60)
    
    results = {}
    
    results['python'] = test_python_version()
    results['core'] = test_core_dependencies()
    results['optional'] = test_optional_dependencies()
    results['file'] = test_file_structure()
    results['permissions'] = test_permissions()
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    if results['python'] and results['core'] and results['file']:
        print("✅ READY TO RUN!")
        print("\nStart the viewer with:")
        print("  python3 viewer_v2.py")
        if results['permissions']:
            print("or:")
            print("  ./viewer_v2.py")
        
        if not results['optional']:
            print("\nNote: QR code scanning is not available (optional)")
        
        return 0
    else:
        print("❌ NOT READY - Fix issues above")
        print("\nCommon fixes:")
        print("1. Install core dependencies:")
        print("   pip install requests cbor2")
        print("\n2. Install tkinter (if missing):")
        print("   Ubuntu/Debian: sudo apt-get install python3-tk")
        print("   macOS: Reinstall Python from python.org")
        print("   Windows: Reinstall Python with tcl/tk option")
        print("\n3. Make sure viewer_v2.py is in current directory")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
