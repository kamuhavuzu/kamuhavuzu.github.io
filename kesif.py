import requests, re, html
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Accept-Language':'tr-TR,tr;q=0.9'}
for u in ['https://www.iskur.gov.tr/ilanlar/kamu-memur-alim-ilanlari/','https://www.iskur.gov.tr/ilanlar/kurumdisi-kamu-isci-alim-ilanlari/']:
    t=requests.get(u,headers=H,timeout=30).text
    print('INF',u,len(t))
    sc=re.findall(r'<script[^>]*>(.*?)</script>',t,flags=re.S)
    print('INF scripts',[len(s) for s in sc if len(s)>5000])
    for s in sc:
        if len(s)>5000: print('INF head',s[:300].replace('\n',' '))
    # inline json blobs / tables / data attrs
    print('INF tables',t.count('<table'),'tr',t.count('<tr'),'li',t.count('<li'),'select',t.count('<select'))
    for kw in ['işçi','Alım İlanı','Alım Duyurusu','KPSS','Belediye','ŞEHİR','data-url','ajax','fetch(','api/']:
        i=t.find(kw)
        print('INF kw',kw,t.count(kw),re.sub(r'\s+',' ',html.unescape(t[max(0,i-80):i+160])) if i>=0 else '')
    print('INF urls',list(dict.fromkeys(re.findall(r'https?://[a-zA-Z0-9./_-]*iskur[a-zA-Z0-9./_?=&%-]*',t)))[:25])
