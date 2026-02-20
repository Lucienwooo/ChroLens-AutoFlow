import re

# The eval block from the user's provided HTML for javmix.tv/xvideo/x_dvmm-357/
# The key array from the eval at end of the HTML contains:
# 'Rmm9ZJRkAqSdwXq' -> iplayerhls ID (e1s1 = HG server) -> player 1
# 'zkolcqmqaqa3'     -> streamtape ID but used with streamtape (e1s2 = EV server) -> player 2
# '9gp927whjpub'     -> dintezuvio ID (e1s3 = ST server) -> player 3
# 'dintezuvio'       -> third-party player domain for mosaic

# From the split key array:
# 'iplayerhls' -> e1s1 server
# 'streamtape' doesn't appear; but the streamtape result is for 'e1s2'
# The actual domains from the decoded script:
#   b = iplayerhls.com/e/Rmm9ZJRkAqSdwXq
#   h = (streamtape/second domain)/v/zkolcqmqaqa3
#   g = dintezuvio.com/e/9gp927whjpub

# Let's decode it properly
packed = "11(10()&&Z()){$(2(){$(\'#1\').U(\'3\',2(){$(\'#1\').4(b)});$(\'.b\').3(2(){$(\'#1\').4(b)});$(\'.h\').3(2(){$(\'#1\').4(h)});$(\'.g\').3(2(){$(\'#1\').4(g)});$(\'#1\').U(\'3\',2(){$(\'#5\').4(B)});$(\'.b\').3(2(){$(\'#5\').4(B)});$(\'.h\').3(2(){$(\'#5\').4(K)});$(\'.g\').3(2(){$(\'#5\').4(H)});$(\'#D c\').3(2(){6 E=$(\'#D c\').E(C);$(\'#T S\').R(\'Q\',\'X\');$(\'#T S\').W(E).R(\'Q\',\'V\');$(\'#D c\').O(\'k-j\');$(C).N(\'k-j\')});$(\'#P c\').3(2(){$(\'#P c\').O(\'k-j\');$(C).N(\'k-j\')});6 b=\'<1 A=\"z\" y=\"9://M.8/e/L\" x=\"0\" w=\"u\" t></1>\';6 B=\'s.<a r=\"9://M.8/f/L\" q=\"p\"><i o=\"7 7-5\" n-m=\"l\"></i></a>\';6 h=\'<1 A=\"z\" y=\"9://J.8/v/I\" x=\"0\" w=\"u\" t></1>\';6 K=\'s.<a r=\"9://J.8/d/I\" q=\"p\"><i o=\"7 7-5\" n-m=\"l\"></i></a>\';6 g=\'<1 A=\"z\" y=\"9://G.8/e/F\" x=\"0\" w=\"u\" t></1>\';6 H=\'s.<a r=\"9://G.8/v/F/\" q=\"p\"><i o=\"7 7-5\" n-m=\"l\"></i></a>\'}"

keys = '|iframe|function|click|html|download|var|fa|fa|com|https||e1s1|span||||e1s3|e1s2||select|tab|true|hidden|aria|class|_blank|target|href|DL|allowfullscreen|no||scrolling|frameborder|src|embed|id|e1s1d|this|episode|index|Rmm9ZJRkAqSdwXq|streamtape|e1s3d|9gp927whjpub|dintezuvio|e1s2d|zkolcqmqaqa3|iplayerhls|addClass|removeClass|e1|display|css|div|server|one|block|eq|none|else|ChromeCheck|UACheck|if'.split('|')

a = 62
c = 64
k = keys

def decode(val, base):
    chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if val < base: return chars[val]
    return decode(val // base, base) + chars[val % base]

p = packed
for i in range(c - 1, -1, -1):
    if k[i]:
        encoded = decode(i, a)
        p = re.sub(r'\b' + encoded + r'\b', k[i], p)

print('Decoded script:')
print(p[:2000])

print('\n\n--- Extracted URLs ---')
urls = re.findall(r'src=\\?"(https?://[^"\\]+)"', p)
for u in urls:
    print('embed URL:', u)

hrefs = re.findall(r'href=\\?"(https?://[^"\\]+)"', p) 
for h in hrefs:
    print('download URL:', h)
