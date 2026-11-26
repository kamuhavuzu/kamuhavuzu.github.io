# Gecici kesif: ilan.gov.tr ve kariyerkapisi.gov.tr sayfalarindaki JS dosyalarinda logo/veri adreslerini arar.
import re, sys, requests
UA = {"user-agent": "Mozilla/5.0 (compatible; KamuRadar/1.0; kisisel kullanim)"}
HEDEF = [("https://www.ilan.gov.tr/", ["cdnBaseUrl:", "cdnBaseUrl=", "cdnBaseUrl\""]),
         ("https://kariyerkapisi.gov.tr/", ["/UPS/", "UPS/", "IlanListe", "api/", "Logo"])]
for kok, anahtarlar in HEDEF:
    print("=====", kok)
    try:
        r = requests.get(kok, headers=UA, timeout=30)
    except Exception as e:
        print("hata", type(e).__name__); continue
    print("durum", r.status_code, len(r.text))
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', r.text)
    print("scriptler:", scripts[:30])
    for sc in scripts[:30]:
        url = requests.compat.urljoin(kok, sc)
        if not url.startswith(kok.rstrip("/")):
            continue
        try:
            js = requests.get(url, headers=UA, timeout=30).text
        except Exception as e:
            print("js hata", url); continue
        for a in anahtarlar:
            for m in list(re.finditer(re.escape(a), js))[:4]:
                print(f"[{sc}] {a}: ...{js[max(0, m.start()-120):m.end()+160]!r}")
