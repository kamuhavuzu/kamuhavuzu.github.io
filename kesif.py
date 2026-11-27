import requests, re, html
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36'}
for u in ['https://www.iskur.gov.tr/ilanlar/kamu-memur-alim-ilanlari/','https://www.iskur.gov.tr/ilanlar/kurumdisi-kamu-isci-alim-ilanlari/']:
    t=requests.get(u,headers=H,timeout=30).text
    t2=re.sub(r'<script.*?</script>|<style.*?</style>|<svg.*?</svg>','',t,flags=re.S)
    k=t2.find('city-dropdown')
    body=t2[k:]
    # strip select
    body=re.sub(r'<select.*?</select>','',body,flags=re.S)
    print('INF',u,len(t2))
    cards=re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',body,flags=re.S)
    cards=[(h,re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',x))).strip()) for h,x in cards]
    cards=[c for c in cards if c[1] and not c[0].startswith('http://www.iskur.gov.tr/')]
    print('INF n',len(cards))
    for h,x in cards[:60]: print('INF A',h[:100],'|',x[:130])
    print('INF text',re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',body)))[:600])
