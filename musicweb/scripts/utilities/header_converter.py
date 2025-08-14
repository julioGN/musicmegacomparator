#!/usr/bin/env python3
"""
Convert raw HTTP headers to JSON format for YouTube Music API.
"""

import json
import sys
from pathlib import Path

def convert_raw_headers_to_json(raw_headers_text: str) -> dict:
    """Convert raw HTTP headers text to JSON format."""
    headers = {}
    
    for line in raw_headers_text.splitlines():
        line = line.strip()
        if not line or ':' not in line:
            continue
        
        # Skip the first line if it's an HTTP request line (starts with GET/POST/etc)
        if any(line.startswith(method) for method in ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS']):
            continue
            
        key, val = line.split(':', 1)
        headers[key.strip()] = val.strip()
    
    # Ensure required defaults if missing
    headers.setdefault('X-Goog-AuthUser', '0')
    headers.setdefault('x-origin', 'https://music.youtube.com')
    
    return headers

def main():
    # Convert the example file
    input_file = Path("ytm-dedup-main/headers_auth_example.json")
    output_file = Path("headers_auth.json")
    
    if not input_file.exists():
        print(f"Error: {input_file} not found")
        sys.exit(1)
    
    print(f"Converting {input_file} to proper JSON format...")
    
    # Read raw headers
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_content = f.read()
    
    # Convert to JSON
    headers_dict = convert_raw_headers_to_json(raw_content)
    
    # Save as JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(headers_dict, f, indent=2)
    
    print(f"✅ Converted headers saved to {output_file}")
    print(f"📊 Extracted {len(headers_dict)} headers")
    
    # Show key headers for verification
    key_headers = ['Authorization', 'Cookie', 'X-Goog-Visitor-Id', 'X-Youtube-Client-Version']
    print("\n🔍 Key headers found:")
    for header in key_headers:
        if header in headers_dict:
            value = headers_dict[header]
            # Truncate long values for display
            if len(value) > 50:
                value = value[:47] + "..."
            print(f"  ✓ {header}: {value}")
        else:
            print(f"  ❌ {header}: Missing")

if __name__ == "__main__":
    main()