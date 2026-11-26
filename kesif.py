import requests, json
B='https://api.kariyerkapisi.gov.tr/api'
H={'User-Agent':'Mozilla/5.0','Content-Type':'application/json','Accept':'application/json','Origin':'https://kariyerkapisi.gov.tr','Referer':'https://kariyerkapisi.gov.tr/'}
for ep,body in [('/ilan/GetIseAlimPage',{"krM_ID":0,"searchText":"","il":"0","ilanTuru":"0"}),('/ilan/SearchIlanPublic',{"krM_ID":0,"searchText":"","il":"0","ilanTuru":"0"})]:
    try:
        r=requests.post(B+ep,json=body,headers=H,timeout=40)
        print('EP',ep,r.status_code,len(r.text))
        print('RAW',r.text[:1500].replace('\n',' '))
        try:
            j=r.json()
            def walk(o,p=''):
                if isinstance(o,dict):
                    for k,v in o.items():
                        if isinstance(v,list): print('LIST',p+'/'+k,len(v), json.dumps(v[0],ensure_ascii=False)[:600] if v else '')
                        walk(v,p+'/'+k)
            walk(j)
        except Exception as e: print('json err',e)
    except Exception as e: print('ERR',ep,e)
