import requests, re
UA = {"user-agent": "Mozilla/5.0 (compatible; KamuRadar/1.0; kisisel kullanim)"}
kok = "https://kariyerkapisi.gov.tr"
t = requests.get(kok + "/isealim", headers=UA, timeout=30).text
main = re.findall(r'src="(/js/Index/Main[^"]+)"', t)[0]
js = requests.get(kok + main, headers=UA, timeout=30).text
print("MAINLEN", len(js))
for m in list(re.finditer(r"(createAjaxRequest|ajax|/Ilan|\"/[A-Z][A-Za-z/]+\"|'/[A-Z][A-Za-z/]+')", js))[:25]:
    print("MAIN", repr(js[max(0, m.start()-60):m.end()+220]))
