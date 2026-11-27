import requests, re
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Accept-Language':'tr-TR,tr;q=0.9'}
def txt(t):
    t=re.sub(r'<script.*?</script>|<style.*?</style>','',t,flags=re.S)
    return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',t))
for u in ['https://www.iskur.gov.tr/ilanlar/','https://www.iskur.gov.tr/ilanlar/kurumdisi-kamu-isci-alim-ilanlari/','https://www.iskur.gov.tr/ilanlar/kamu-memur-alim-ilanlari/','https://www.iskur.gov.tr/ilanlar/kamu-isci-alim-ilanlari/']:
    try:
        r=requests.get(u,headers=H,timeout=30);t=r.text
        print('INF',u,r.status_code,len(t))
        links=re.findall(r'href="([^"]+)"',t)
        keep=[l for l in dict.fromkeys(links) if re.search(r'isci|ilan|kamu|alim|pdf|esube|api|json',l,re.I)]
        print('INF links',keep[:35])
        print('INF txt',txt(t)[300:1100])
        for m in re.finditer(r'(https?://[^"\' ]*(?:api|json|ilan)[^"\' ]*)',t): print('INF u',m.group(1)[:150]);break
    except Exception as e: print('INF ERR',u,type(e).__name__)
