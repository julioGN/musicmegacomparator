#!/usr/bin/env python3
"""
Debug YouTube Music API responses
"""

import json
import requests
from urllib.parse import urlencode

def debug_ytm_request():
    # Load headers
    with open('headers_auth.json', 'r') as f:
        headers = json.load(f)
    
    # Basic YouTube Music API endpoint
    url = "https://music.youtube.com/youtubei/v1/search?prettyPrint=false"
    
    # Basic search payload
    data = {
        "context": {
            "client": {
                "clientName": "WEB_REMIX",
                "clientVersion": "1.20250805.07.00"
            }
        },
        "query": "Queen"
    }
    
    try:
        print("Making request to YouTube Music API...")
        # Requests should automatically handle compression, but let's be explicit
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        print(f"Status code: {response.status_code}")
        print(f"Content-Encoding: {response.headers.get('Content-Encoding', 'none')}")
        print(f"Response length (raw): {len(response.content)}")
        print(f"Response length (text): {len(response.text)}")
        
        if response.text:
            try:
                json_data = response.json()
                print("✅ Valid JSON response received")
                print(f"JSON keys: {list(json_data.keys())}")
                
                # Check if we have search results
                if 'contents' in json_data:
                    print("✅ Search results found in response")
                else:
                    print("⚠️ No 'contents' key in response")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON in response: {e}")
                print(f"First 200 chars: {response.text[:200]}")
        else:
            print("❌ Empty response body")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    debug_ytm_request()