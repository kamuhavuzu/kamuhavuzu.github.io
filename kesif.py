import requests, re, json, time
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Accept-Language':'tr-TR,tr;q=0.9'}
def get(u,**k):
    try:
        r=requests.get(u,headers=H,timeout=25,**k);return r
    except Exception as e:
        print('INF ERR',u,type(e).__name__,str(e)[:120]);return None
r=get('https://kariyerkapisi.gov.tr/isealim')
if r:
    print('INF isealim',r.status_code,len(r.text))
    for s in re.findall(r'src="([^"]*Infrastructure[^"]*)"',r.text)[:2]:
        j=get('https://kariyerkapisi.gov.tr'+s if s.startswith('/') else s)
        if j:
            for m in re.finditer(r'.{80}apiURL.{160}',j.text):print('INF api',m.group(0).replace('\n',' ')[:260]);break
            for m in re.finditer(r'https?://[a-zA-Z0-9./_-]*api[a-zA-Z0-9./_-]*',j.text):print('INF url',m.group(0));
for u in ['https://api.kariyerkapisi.gov.tr/api/ilan/GetIseAlimPage','https://kariyerkapisi.gov.tr/api/ilan/GetIseAlimPage','https://apiv2.kariyerkapisi.gov.tr/api/ilan/GetIseAlimPage']:
    try:
        t=time.time();x=requests.post(u,json={"krM_ID":0,"searchText":"","il":"0","ilanTuru":"0"},headers={**H,'Content-Type':'application/json','Origin':'https://kariyerkapisi.gov.tr','Referer':'https://kariyerkapisi.gov.tr/'},timeout=20)
        print('INF POST',u,x.status_code,len(x.text),x.text[:300].replace('\n',' '),round(time.time()-t,1))
    except Exception as e: print('INF POSTERR',u,type(e).__name__,str(e)[:100])
for u in ['https://www.iskur.gov.tr/ilanlar/kamu-memur-alim-ilanlari/','https://kamuilan.sbb.gov.tr/','https://www.resmigazete.gov.tr/ilanlar']:
    x=get(u)
    if x: print('INF',u,x.status_code,len(x.text),re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',x.text))[:200])
