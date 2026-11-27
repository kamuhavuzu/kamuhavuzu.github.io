import requests, re, html
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36'}
B='https://www.iskur.gov.tr/ilanlar/kamu-memur-alim-ilanlari/'
t=requests.get(B,headers=H,timeout=30).text
gs=re.findall(r'<g[^>]*data-count[^>]*>',t)
print('INF g',len(gs))
for g in gs[:6]: print('INF gtag',g[:260])
tot=0
for g in gs:
    m=re.search(r'data-count="(\d+)"',g); tot+=int(m.group(1)) if m else 0
print('INF toplam data-count',tot)
sel=re.search(r'<select.*?</select>',t,flags=re.S)
print('INF select',re.sub(r'\s+',' ',sel.group(0))[:500] if sel else None)
i=t.find('idId');print('INF idId ctx',re.sub(r'\s+',' ',t[max(0,i-300):i+200]))
