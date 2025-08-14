#!/usr/bin/env python3
"""
Simple test script to verify logo loading works correctly.
This can be run by users to test their installation.
"""

def test_logo_loading():
    """Test that the logo loads correctly from package resources."""
    try:
        from musicweb.web.app import get_logo_base64
        
        print("Testing MusicWeb logo loading...")
        logo_b64 = get_logo_base64()
        
        if logo_b64:
            print(f"✅ SUCCESS: Logo loaded ({len(logo_b64)} characters)")
            print(f"✅ First 50 chars: {logo_b64[:50]}...")
            return True
        else:
            print("❌ FAILED: Logo not loaded")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_logo_loading()
    exit(0 if success else 1)