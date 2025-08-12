#!/usr/bin/env python3
"""
Simple utility to convert raw HTTP headers to headers_auth.json format.
"""

import json
import sys
from pathlib import Path
from typing import Dict


def convert_raw_headers_to_json(raw_headers_text: str) -> Dict[str, str]:
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
    """Convert raw headers file to JSON format."""
    if len(sys.argv) != 3:
        print("Usage: python convert_headers.py <input_file> <output_file>")
        print("Example: python convert_headers.py headers_auth.i headers_auth.json")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        sys.exit(1)
    
    try:
        # Read raw headers
        raw_content = input_file.read_text(encoding='utf-8')
        
        # Convert to JSON format
        headers_dict = convert_raw_headers_to_json(raw_content)
        
        if not headers_dict:
            print("❌ No valid headers found in input file")
            sys.exit(1)
        
        # Write JSON output
        output_file.write_text(json.dumps(headers_dict, indent=2), encoding='utf-8')
        
        print(f"✅ Successfully converted headers:")
        print(f"   Input:  {input_file}")
        print(f"   Output: {output_file}")
        print(f"   Found {len(headers_dict)} headers")
        
        # Show essential headers for verification
        essential = ['Cookie', 'Authorization', 'User-Agent']
        missing = [h for h in essential if h not in headers_dict]
        
        if missing:
            print(f"⚠️  Missing essential headers: {', '.join(missing)}")
            print("   The authentication may not work without these.")
        else:
            print("✅ All essential headers found")
            
    except Exception as e:
        print(f"❌ Error converting headers: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()