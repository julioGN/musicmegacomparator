#!/usr/bin/env python3
"""
YouTube Music Header Extraction Helper

This script helps you extract fresh headers from your browser.
Run this and follow the instructions to update your headers safely.
"""

import json
import os

def main():
    print("🔧 YouTube Music Header Extraction Helper")
    print("=" * 50)
    print()
    print("To get fresh headers:")
    print("1. Open YouTube Music in your browser (music.youtube.com)")
    print("2. Open Developer Tools (F12 or right-click -> Inspect)")
    print("3. Go to the 'Network' tab")
    print("4. Clear the network log (trash icon)")
    print("5. In YouTube Music, search for any song")
    print("6. In Network tab, look for a POST request to 'youtubei/v1/search'")
    print("7. Click on it, go to 'Headers' tab")
    print("8. Scroll to 'Request Headers' section")
    print("9. Copy ALL the headers (not the response headers)")
    print()
    print("Current headers file:", os.path.abspath("headers_auth.json"))
    print()
    
    # Check if current headers exist
    if os.path.exists("headers_auth.json"):
        try:
            with open("headers_auth.json", 'r') as f:
                headers = json.load(f)
            print("✅ Current headers file found with", len(headers), "headers")
            
            # Check for key authentication headers
            auth_keys = ['Authorization', 'Cookie', 'X-Goog-Visitor-Id']
            missing = [key for key in auth_keys if key not in headers]
            if missing:
                print("⚠️  Missing key headers:", missing)
            else:
                print("✅ All key authentication headers present")
                
        except Exception as e:
            print("❌ Error reading current headers:", e)
    else:
        print("❌ No headers file found")
    
    print()
    print("💡 Tip: Headers typically expire every few hours/days")
    print("💡 If you get 'Expecting value' errors, your headers likely expired")
    
if __name__ == "__main__":
    main()