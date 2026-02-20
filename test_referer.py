import requests
import re

def decode(val, base):
    chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if val < base: return chars[val]
    return decode(val // base, base) + chars[val % base]

def extract_cdnvp_and_resolve(player_url):
    """
    Fetch the player embed page, unpack eval(), extract the CDN _h URL,
    then resolve it with the correct Referer to get the final signed .mp4 URL.
    """
    print(f'Player URL: {player_url}')
    
    # Route based on domain: callistanise -> /f/, everything else -> /e/
    if 'callistanise' in player_url or 'dintezuvio' in player_url:
        target = player_url.replace('/v/', '/f/').replace('/e/', '/f/').replace('/d/', '/f/').replace('/download/', '/f/')
    else:
        target = player_url.replace('/v/', '/e/').replace('/f/', '/e/').replace('/d/', '/e/').replace('/download/', '/e/')
    
    print(f'Fetching: {target}')
    
    headers_player = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': player_url  # Refer to original player domain
    }
    
    resp = requests.get(target, headers=headers_player, timeout=10)
    if resp.status_code != 200:
        print(f'Error: {resp.status_code}')
        return None
    
    html = resp.text
    
    # Unpack the eval()
    eval_m = re.search(r'eval\(function\(p,a,c,k,e,d\)\{.*?return p\}\(\'(.*?)\',\s*(\d+),\s*(\d+),\s*\'(.*?)\'\.split\(\'\|\'\)', html, re.DOTALL)
    if not eval_m:
        print('No eval block found')
        return None
    
    p, a, c, k = eval_m.groups()
    a = int(a); c = int(c); k = k.split('|')
    for i in range(c - 1, -1, -1):
        if k[i]:
            p = re.sub(r'\b' + decode(i, a) + r'\b', k[i], p)
    
    hls_m = re.search(r'"hls2"\s*:\s*"(https?://[^"]+)"', p)
    if not hls_m:
        print('No hls2 key in unpacked JS')
        return None
    
    hls_url = hls_m.group(1)
    domain_m = re.search(r'(https?://[^/]+)', hls_url)
    path_m = re.search(r'/hls2(/.*?/)([a-zA-Z0-9]+)_', hls_url)
    
    if not (domain_m and path_m):
        print('Could not parse hls2 path')
        return None
    
    domain = domain_m.group(1)
    folder = path_m.group(1)
    vid = path_m.group(2)
    cdn_h_url = f'{domain}/vp{folder}{vid}_h'
    print(f'\nCDN _h URL: {cdn_h_url}')
    
    # NOW resolve with proper Referer header
    headers_cdn = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': target  # Referer = the player embed page
    }
    
    print('Resolving CDN _h with Referer...')
    cdn_resp = requests.get(cdn_h_url, headers=headers_cdn, allow_redirects=False, timeout=10)
    print(f'Status: {cdn_resp.status_code}')
    
    if cdn_resp.status_code in (301, 302, 303, 307, 308):
        final_url = cdn_resp.headers.get('Location')
        print(f'=> SUCCESS! Final MP4 URL: {final_url}')
        return final_url
    else:
        print(f'No redirect from CDN. Body: {cdn_resp.text[:200]}')
        return None

# Test
r1 = extract_cdnvp_and_resolve('https://iplayerhls.com/e/svikinp1ac0e')
r2 = extract_cdnvp_and_resolve('https://callistanise.com/f/9gp927whjpub')
