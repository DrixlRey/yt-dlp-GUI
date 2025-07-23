#!/usr/bin/env python3
"""
Test script to verify PyQt6 verification logic from the installer
This mimics the verification commands used in the NSIS installer
"""

import subprocess
import sys

def test_pyqt6_verification():
    """Test PyQt6 verification methods used in the installer"""
    
    print("Testing PyQt6 verification methods...")
    print("=" * 50)
    
    # Test 1: Primary verification (import PyQt6)
    print("\nTest 1: Primary verification - import PyQt6")
    try:
        result = subprocess.run([
            sys.executable, "-c", 
            "import sys; import PyQt6.QtCore; print('PyQt6 found')"
        ], capture_output=True, text=True)
        
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout.strip()}")
        print(f"Stderr: {result.stderr.strip()}")
        
        if result.returncode == 0:
            print("✅ Primary verification: PASSED")
        else:
            print("❌ Primary verification: FAILED")
            
    except Exception as e:
        print(f"❌ Primary verification: ERROR - {e}")
    
    # Test 2: Alternative verification (import PyQt6.QtCore)
    print("\nTest 2: Alternative verification - import PyQt6.QtCore")
    try:
        result = subprocess.run([
            sys.executable, "-c", "import PyQt6.QtCore"
        ], capture_output=True, text=True)
        
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout.strip()}")
        print(f"Stderr: {result.stderr.strip()}")
        
        if result.returncode == 0:
            print("✅ Alternative verification: PASSED")
        else:
            print("❌ Alternative verification: FAILED")
            
    except Exception as e:
        print(f"❌ Alternative verification: ERROR - {e}")
    
    # Test 3: Direct import test
    print("\nTest 3: Direct import test")
    try:
        import PyQt6
        print("✅ Direct import: PyQt6 successfully imported")
        print(f"PyQt6 version: {PyQt6.QtCore.PYQT_VERSION_STR}")
        print(f"Qt version: {PyQt6.QtCore.QT_VERSION_STR}")
    except ImportError as e:
        print(f"❌ Direct import: Failed to import PyQt6 - {e}")
    except Exception as e:
        print(f"❌ Direct import: ERROR - {e}")
    
    print("\n" + "=" * 50)
    print("PyQt6 verification test completed!")

if __name__ == "__main__":
    test_pyqt6_verification()