# YouTube Music Authentication Setup Guide

## Step 1: Open YouTube Music
1. Go to https://music.youtube.com in your browser
2. Make sure you're logged into your Google account
3. Navigate to your library (any page will work)

## Step 2: Open Developer Tools
1. Press F12 (or Ctrl+Shift+I on Windows/Linux, Cmd+Opt+I on Mac)
2. Click on the "Network" tab
3. Make sure "Preserve log" is checked (if available)

## Step 3: Refresh and Find Request
1. Refresh the YouTube Music page (F5 or Ctrl+R)
2. Wait for the page to load completely
3. In the Network tab, look for requests to:
   - `music.youtube.com/youtubei/v1/browse`
   - `music.youtube.com/youtubei/v1/search`
   - Any request starting with `music.youtube.com/youtubei/v1/`

## Step 4: Copy Request Headers
1. Click on one of the requests from step 3
2. In the right panel, find the "Request Headers" section
3. Right-click in the Request Headers area
4. Select "Copy" → "Copy request headers" (or similar option)

## Step 5: Create Authentication File
1. Create a new file called `headers_auth.json` in the same folder as this script
2. The file should contain JSON like this:

```json
{
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "X-Goog-AuthUser": "0",
    "x-origin": "https://music.youtube.com",
    "Cookie": "VISITOR_INFO1_LIVE=...; CONSENT=...; [VERY LONG COOKIE STRING]"
}
```

## Important Notes:
- The Cookie field is the most important - it contains your authentication
- Headers may vary slightly between browsers
- You may need to repeat this process if authentication expires
- Never share your headers_auth.json file - it contains your login credentials

## Troubleshooting:
- If authentication fails, try getting fresh headers
- Make sure you're logged into YouTube Music when copying headers
- Some ad blockers may interfere - try disabling them temporarily
- If you see CORS errors, make sure the server is running on localhost

## Security Warning:
The headers_auth.json file contains your YouTube Music login credentials.
Keep this file private and never share it with others.
