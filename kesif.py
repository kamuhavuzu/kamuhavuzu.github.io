import requests, re
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36'}
t=requests.get('https://www.iskur.gov.tr/ilanlar/kamu-memur-alim-ilanlari/',headers=H,timeout=30).text
for s in re.findall(r'<script[^>]*>(.*?)</script>',t,flags=re.S):
    if len(s)>5000:
        for i in range(0,len(s),900): print('INF',s[i:i+900].replace('\n',' '))
print('INF SRC',re.findall(r'<script[^>]+src="([^"]+)"',t))
