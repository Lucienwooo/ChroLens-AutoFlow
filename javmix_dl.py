import requests
import re
import subprocess
import sys
import os
from pathlib import Path

def decode(val, base):
    chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if val < base: return chars[val]
    return decode(val // base, base) + chars[val % base]

def get_hls2_url(player_url):
    """從播放器頁面提取 HLS M3U8 串流 URL（含有效 t= 簽章）"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    is_calli = any(d in player_url for d in ('callistanise', 'dintezuvio'))
    target = re.sub(r'/(?:v|e|d|download)/', '/f/', player_url) if is_calli else re.sub(r'/(?:v|f|d|download)/', '/e/', player_url)
    
    print(f'Fetching: {target}')
    resp = requests.get(target, headers=headers, timeout=10)
    if resp.status_code != 200:
        print(f'Error: {resp.status_code}')
        return None
    
    html = resp.text
    eval_m = re.search(r'eval\(function\(p,a,c,k,e,d\)\{.*?return p\}\(\'(.*?)\',\s*(\d+),\s*(\d+),\s*\'(.*?)\'\.split\(\'\|\'\)', html, re.DOTALL)
    if not eval_m:
        return None
    
    p, a, c, k = eval_m.groups()
    a = int(a); c = int(c); k = k.split('|')
    for i in range(c - 1, -1, -1):
        if k[i]:
            p = re.sub(r'\b' + decode(i, a) + r'\b', k[i], p)
    
    hls_m = re.search(r'"hls2"\s*:\s*"(https?://[^"]+\.m3u8[^"]*)"', p)
    return hls_m.group(1) if hls_m else None

def download_with_ytdlp(m3u8_url, output_path, referer=None):
    """使用 yt-dlp 下載 HLS 串流"""
    cmd = [
        sys.executable, '-m', 'yt_dlp',
        '--no-warnings',
        '--hls-prefer-native',
        '-o', str(output_path),
    ]
    if referer:
        cmd += ['--add-header', f'Referer:{referer}']
    cmd.append(m3u8_url)
    
    print(f'Running yt-dlp...')
    result = subprocess.run(cmd)
    return result.returncode == 0

# ============================================================
if __name__ == '__main__':
    code = sys.argv[1] if len(sys.argv) > 1 else 'DVMM-357'
    use_mosaic = '--mosaic' in sys.argv or '-m' in sys.argv
    
    print(f'=== Javmix HLS Downloader: {code} ===\n')
    
    sys.path.insert(0, 'main')
    from link_search_tool import LinkSearchWorker
    worker = LinkSearchWorker(code)
    links = worker.find_javmix_dual_links(code)
    print('Links:', links)
    
    dl_url = (links.get('mosaic_dl') if use_mosaic else None) or links.get('origin_dl') or links.get('mosaic_dl') or ''
    print(f'\nUsing download page: {dl_url}')
    
    if not dl_url:
        print('No download URL found.'); sys.exit(1)
    
    vid_m = re.search(r'/download/([a-zA-Z0-9]+)_h', dl_url)
    if not vid_m:
        print('Cannot parse video ID from download URL'); sys.exit(1)
    
    vid = vid_m.group(1)
    from urllib.parse import urlparse
    parsed = urlparse(dl_url)
    domain_base = f'{parsed.scheme}://{parsed.netloc}'
    
    hls2_url = None
    for route in ['/e/', '/f/']:
        player_url = f'{domain_base}{route}{vid}'
        hls2_url = get_hls2_url(player_url)
        if hls2_url:
            print(f'\n✅ M3U8 URL:\n{hls2_url}\n')
            break
    
    if not hls2_url:
        print('❌ Failed to extract M3U8 URL'); sys.exit(1)
    
    downloads = Path.home() / 'Downloads'
    out_file = downloads / f'{code}.mp4'
    
    success = download_with_ytdlp(hls2_url, out_file, referer=player_url)
    if success:
        print(f'\n✅ Saved to: {out_file}')
    else:
        print(f'\n❌ Download failed. Try manually with:\n  yt-dlp "{hls2_url}"')
