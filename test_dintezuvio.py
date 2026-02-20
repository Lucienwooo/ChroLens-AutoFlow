import requests
import re

def decode(val, base):
    chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if val < base: return chars[val]
    return decode(val // base, base) + chars[val % base]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://dintezuvio.com/',
}

url = 'https://dintezuvio.com/e/9gp927whjpub'
print(f'Fetching: {url}')
resp = requests.get(url, headers=headers, timeout=10)
print(f'Status: {resp.status_code}, len: {len(resp.text)}')

with open('dintezuvio_response.html', 'w', encoding='utf-8') as f:
    f.write(resp.text)
print('Saved dintezuvio_response.html')

# Also try /f/ route
url2 = 'https://dintezuvio.com/f/9gp927whjpub'
print(f'\nFetching: {url2}')
resp2 = requests.get(url2, headers=headers, timeout=10)
print(f'Status: {resp2.status_code}, len: {len(resp2.text)}')

html = resp2.text if resp2.status_code == 200 else resp.text

# Find ALL urls in the page
print('\nAll URLs containing CDN patterns:')
cdns = re.findall(r'https?://[^\s"\'<>]+(?:premilkyway|cdn-centaurus|acek-cdn)[^\s"\'<>]*', html)
for c in set(cdns):
    print(' CDN:', c[:200])

print('\nAll .mp4 URLs:')
mp4s = re.findall(r'https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*', html)
for m in set(mp4s):
    print(' MP4:', m[:200])
    
print('\nAll m3u8 URLs:')
m3us = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html)
for m in set(m3us[:5]):
    print(' M3u8:', m[:200])
    
# Try eval unpack
eval_m = re.search(r'eval\(function\(p,a,c,k,e,d\)\{.*?return p\}\(\'(.*?)\',\s*(\d+),\s*(\d+),\s*\'(.*?)\'\.split\(\'\|\'\)', html, re.DOTALL)
if eval_m:
    print('\nFound eval block, unpacking...')
    p, a, c, k = eval_m.groups()
    a = int(a); c = int(c); k = k.split('|')
    for i in range(c - 1, -1, -1):
        if k[i]:
            p = re.sub(r'\b' + decode(i, a) + r'\b', k[i], p)
    print('hls2:', re.search(r'"hls2"\s*:\s*"([^"]+)"', p))
    
    cdns2 = re.findall(r'https?://[^\s"\'<>]+(?:premilkyway|cdn-centaurus|acek-cdn)[^\s"\'<>]*', p)
    for c2 in set(cdns2):
        print(' CDN in unpacked JS:', c2[:200])
else:
    print('No eval block found.')
