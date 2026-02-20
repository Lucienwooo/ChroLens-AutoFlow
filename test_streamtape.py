import requests
import re

def decode(val, base):
    chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if val < base: return chars[val]
    return decode(val // base, base) + chars[val % base]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# DVMM-357 on streamtape: e1s2 server with id=zkolcqmqaqa3
# From the javmix HTML eval we can see: e1s2d = zkolcqmqaqa3, streamtape
# iplayerhls for the alternative (non-mosaic) version: Rmm9ZJRkAqSdwXq

test_cases = [
    ('streamtape', 'zkolcqmqaqa3', 'DVMM-357'),
    ('iplayerhls', 'Rmm9ZJRkAqSdwXq', 'DVMM-357'),
]

for domain_base, vid_id, code in test_cases:
    print(f'\n=== {domain_base}/{vid_id} ===')
    
    # Streamtape uses /e/ for embed
    url = f'https://{domain_base}.com/e/{vid_id}'
    print(f'Fetching: {url}')
    
    resp = requests.get(url, headers=headers, timeout=10)
    print(f'Status: {resp.status_code}, length: {len(resp.text)}')
    
    if resp.status_code != 200:
        continue
    
    html = resp.text
    
    # Try to find direct MP4 links (streamtape classic approach)
    # Streamtape splits the token across two HTML elements
    tok_m = re.search(r'document\.getElementById\(["\']ideoolink["\']\)\.innerHTML\s*=\s*"([^"]+)"', html)
    if tok_m:
        print('Found innerHTML token:', tok_m.group(1)[:100])
        continue
    
    # Try their newer obfuscation - look for token & partner parts
    part1 = re.search(r'id=["\']ideoolink["\'][^>]*>([^<]+)<', html)
    part2 = re.search(r'id=["\']iddoolink["\'][^>]*>([^<]+)<', html)
    if part1 and part2:
        token = part1.group(1) + part2.group(1)
        print('Concatenated token:', token[:100])
        continue
    
    # Try eval unpack
    eval_m = re.search(r'eval\(function\(p,a,c,k,e,d\)\{.*?return p\}\(\'(.*?)\',\s*(\d+),\s*(\d+),\s*\'(.*?)\'\.split\(\'\|\'\)', html, re.DOTALL)
    if eval_m:
        p, a, c, k = eval_m.groups()
        a = int(a); c = int(c); k = k.split('|')
        for i in range(c - 1, -1, -1):
            if k[i]:
                p = re.sub(r'\b' + decode(i, a) + r'\b', k[i], p)
        
        # Look for hls2 link in unpacked JS
        hls_m = re.search(r'"hls2"\s*:\s*"(https?://[^"]+)"', p)
        if hls_m:
            hls_url = hls_m.group(1)
            print('hls2 URL:', hls_url[:150])
            
            # Extract CDN _h URL
            domain_m = re.search(r'(https?://[^/]+)', hls_url)
            path_m = re.search(r'/hls2(/.*?/)([a-zA-Z0-9]+)_', hls_url)
            if domain_m and path_m:
                cdn_h = f"{domain_m.group(1)}/vp{path_m.group(1)}{path_m.group(2)}_h"
                print('CDN _h:', cdn_h)
                
                # Try resolving with various Referer values
                for ref in [url, f'https://{domain_base}.com/', None]:
                    h = dict(headers)
                    if ref:
                        h['Referer'] = ref
                    r2 = requests.get(cdn_h, headers=h, allow_redirects=False, timeout=10)
                    loc = r2.headers.get('Location', '')
                    print(f'  Referer={ref or "none"} => {r2.status_code} {loc[:100]}')
                    if r2.status_code in (301, 302, 303, 307, 308):
                        break
        else:
            # Check for direct mp4 links in unpacked JS
            for m in re.findall(r'"(https?://[^"]+\.mp4[^"]*)"', p):
                print('Direct MP4:', m[:150])
    else:
        print('No eval block')
        # try looking for direct .mp4 link
        for m in re.findall(r'"(https?://[^"]+\.mp4[^"]*)"', html):
            print('Direct MP4 in HTML:', m[:150])
