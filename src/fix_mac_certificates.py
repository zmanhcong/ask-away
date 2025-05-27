#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MacOS Certificate Fix

This module provides a function to fix SSL certificate verification issues on macOS.
"""

import os
import sys
import subprocess
import ssl

def fix_mac_certificates():
    """Fix SSL certificate verification issues on macOS.
    
    On macOS, Python doesn't use the system certificates by default.
    This function attempts to fix that by running the Install Certificates.command script
    that comes with Python installations on macOS, or by configuring Python to use
    an unverified context as a fallback (less secure).
    
    Returns:
        bool: True if certificates were successfully fixed, False otherwise
    """
    if sys.platform != 'darwin':
        # Not macOS, no fix needed
        return True
    
    try:
        # Try to use certifi if available
        import certifi
        os.environ['SSL_CERT_FILE'] = certifi.where()
        # Test the fix
        try:
            import urllib.request
            urllib.request.urlopen('https://www.google.com')
            print("Certificate verification successful using certifi")
            return True
        except Exception:
            # Certifi didn't work, continue to other methods
            pass
        
        # Look for the Install Certificates.command script in various Python installation locations
        possible_paths = [
            "/Applications/Python 3.*/Install Certificates.command",
            "/Applications/Python/Install Certificates.command",
            "/usr/local/bin/Install Certificates.command"
        ]
        
        for path_pattern in possible_paths:
            try:
                # Use subprocess to find the actual path
                cert_paths = subprocess.check_output(f"ls {path_pattern}", shell=True).decode().strip().split('\n')
                if cert_paths:
                    # Run the first found certificate installation script
                    subprocess.run(cert_paths[0], shell=True, check=True)
                    print(f"Successfully ran certificate installation script: {cert_paths[0]}")
                    return True
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
        
        # If all else fails, use the insecure fallback (not recommended for production)
        ssl._create_default_https_context = ssl._create_unverified_context
        print("WARNING: Using unverified HTTPS context. This is not secure for production.")
        return False
    
    except Exception as e:
        print(f"Error fixing certificates: {e}")
        return False

if __name__ == "__main__":
    fix_mac_certificates()
