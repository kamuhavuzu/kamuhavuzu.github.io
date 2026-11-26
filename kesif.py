import requests, re
UA = {"user-agent": "Mozilla/5.0 (compatible; KamuRadar/1.0; kisisel kullanim)"}
kok = "https://kariyerkapisi.gov.tr"
t = requests.get(kok + "/isealim", headers=UA, timeout=30).text
main = re.findall(r'src="(/js/Index/Main[^"]+)"', t)[0]
js = requests.get(kok + main, headers=UA, timeout=30).text
print("ARAMA-CAGRI")
for m in re.finditer(r"fillIseAlimPageAsync|ilanObject|getAsyncFetchResult", js[6000:]):
    s = 6000 + m.start(); print("MAINCALL", repr(js[max(0, s-300):s+500])); 
inf = requests.get(kok + re.findall(r'src="(/js/Infrastructure[^"]+)"', t)[0], headers=UA, timeout=30).text
for m in re.finditer(r"apiURL|getAsyncFetchResult\s*=", inf):
    print("INF", repr(inf[max(0, m.start()-200):m.end()+500])); 
for i, b in enumerate(re.findall(r"<script(?![^>]*src)[^>]*>(.*?)</script>", t, re.S)):
    print("INLINEFULL", i, repr(b[:900]))
