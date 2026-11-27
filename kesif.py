import requests
for i in range(3):
    try:
        r=requests.get('https://kk-test.nazanamk.workers.dev/',timeout=40)
        print('INF',r.status_code,r.text[:200].replace('\n',' '))
    except Exception as e: print('INF ERR',type(e).__name__,str(e)[:150])
