import requests, re
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Accept-Language':'tr-TR,tr;q=0.9'}
u='https://www.iskur.gov.tr/ilanlar/kamu-memur-alim-ilanlari/'
t=requests.get(u,headers=H,timeout=30).text
i=t.find('Kamu Memur Alım İlanları',2000)
body=re.sub(r'<script.*?</script>|<style.*?</style>','',t,flags=re.S)
txt=re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',body))
j=txt.find('Kamu Memur Alım İlanları',200)
print('INF TXT',txt[j:j+1800])
ls=re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',body,flags=re.S)
ls=[(h,re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',x)).strip()) for h,x in ls]
ls=[(h,x) for h,x in ls if x and re.search(r'ilan|alım|alim|işçi|isci|personel|\.pdf',h+x,re.I)]
print('INF LINKS',len(ls))
for h,x in ls[:40]: print('INF L',h[:110],'|',x[:90])
k=body.find('<table')
print('INF TABLE',k, re.sub(r'\s+',' ',body[k:k+1500]) if k>=0 else '')
