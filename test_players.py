import requests
import re

def decode(val, base):
    chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if val < base: return chars[val]
    return decode(val // base, base) + chars[val % base]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

# Known player embeds from the javmix x_dvmm-357 page:
# Server HG: iplayerhls.com with ID Rmm9ZJRkAqSdwXq
# Server EV: streamtape.com/e/zkolcqmqaqa3  
# Server ST: dintezuvio.com/e/9gp927whjpub
players = [
    ('HG', 'https://iplayerhls.com/e/Rmm9ZJRkAqSdwXq'),
    ('EV-st', 'https://streamtape.com/e/zkolcqmqaqa3'),
    ('ST-din', 'https://dintezuvio.com/e/9gp927whjpub'),
    ('ST-din-f', 'https://dintezuvio.com/f/9gp927whjpub'),
]

for label, url in players:
    print(f'\n=== {label}: {url} ===')
    try:
        h = dict(headers)
        h['Referer'] = url
        resp = requests.get(url, headers=h, timeout=10)
        html = resp.text
        print(f'Status: {resp.status_code}, len: {len(html)}')
        
        # Look for direct MP4 URLs first
        mp4s = re.findall(r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)', html)
        for m in set(mp4s):
            print(f'  MP4: {m[:180]}')
        
        # Look for HLS m3u8 playlists
        m3us = re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
        for m in set(m3us[:3]):
            print(f'  M3U8: {m[:180]}')
        
        # Try eval unpack
        eval_m = re.search(r'eval\(function\(p,a,c,k,e,d\)\{.*?return p\}\(\'(.*?)\',\s*(\d+),\s*(\d+),\s*\'(.*?)\'\.split\(\'\|\'\)', html, re.DOTALL)
        if eval_m:
            p, a, c, k = eval_m.groups()
            a = int(a); c = int(c); k = k.split('|')
            for i in range(c - 1, -1, -1):
                if k[i]:
                    p = re.sub(r'\b' + decode(i, a) + r'\b', k[i], p)
            
            # Find hls2 URL
            hls2 = re.search(r'"hls2"\s*:\s*"(https?://[^"]+)"', p)
            if hls2:
                hls_url = hls2.group(1)
                print(f'  HLS2 URL: {hls_url[:180]}')
                
                # Extract CDN _h URL
                dm = re.search(r'(https?://[^/]+)', hls_url)
                pm = re.search(r'/hls2(/.*?/)([a-zA-Z0-9]+)_', hls_url)
                if dm and pm:
                    cdn_h = f"{dm.group(1)}/vp{pm.group(1)}{pm.group(2)}_h"
                    print(f'  CDN _h: {cdn_h}')
        
        # Check for streamtape-style link generation
        # Streamtape often has: var xstreamLink = ...
        st_m = re.search(r'var\s+(?:xstreamlink|XstreamLink|streamlink)\s*=\s*["\']([^"\']+)["\']', html, re.IGNORECASE)
        if st_m:
            print(f'  streamLink: {st_m.group(1)[:180]}')
            
    except Exception as e:
        print(f'  Error: {e}')
