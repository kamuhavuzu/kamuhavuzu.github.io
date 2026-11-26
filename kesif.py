import requests, json, sys
sys.path.insert(0, ".")
import ayristir as ic
s = requests.Session()
for ats in range(1, 16):
    try:
        r = s.post(ic.SEARCH_URL, json={"keys": {"ats": [ats]}, "skipCount": 0, "maxResultCount": 3}, headers=ic.HEADERS, timeout=30)
        d = r.json().get("result", {})
        items = d.get("ads") or d.get("items") or []
        print(f"ats={ats} toplam={d.get('totalCount')} ornek={[ (a.get('title') or '')[:50] for a in items][:3]}")
    except Exception as e:
        print("ats", ats, "hata", type(e).__name__)
# kategori anahtarlari: ilk personel ilanindaki categories
r = s.post(ic.SEARCH_URL, json={"keys": {"ats": [5]}, "skipCount": 0, "maxResultCount": 2}, headers=ic.HEADERS, timeout=30)
d = r.json().get("result", {})
print("KATEGORI", json.dumps([a.get("categories") for a in (d.get("ads") or d.get("items") or [])], ensure_ascii=False)[:800])
print("ADTYPEFILTERS", json.dumps([a.get("adTypeFilters") for a in (d.get("ads") or d.get("items") or [])], ensure_ascii=False)[:800])
