import requests, re
UA = {"user-agent": "Mozilla/5.0 (compatible; KamuRadar/1.0; kisisel kullanim)"}
for u in ["https://kariyerkapisi.gov.tr/", "https://kariyerkapisi.gov.tr/isealim", "https://kariyerkapisi.gov.tr/IlanListe", "https://kariyerkapisi.gov.tr/Ilanlar"]:
    try:
        r = requests.get(u, headers=UA, timeout=30)
    except Exception as e:
        print("HATA", u, type(e).__name__); continue
    print("DURUM", r.status_code, u, len(r.text))
    t = r.text
    for pat in [r"ajax\s*:\s*\{[^}]{0,300}", r"url\s*:\s*['\"][^'\"]+['\"]", r"href=\"(/[A-Za-z][^\"#?]{2,40})\"", r"IlanDetay[^\"' ]{0,80}", r"fetch\(['\"][^'\"]+", r"\$\.(?:get|post|ajax)\(['\"][^'\"]+"]:
        bul = list(dict.fromkeys(re.findall(pat, t)))[:25]
        if bul: print("  ", pat[:22], bul)
