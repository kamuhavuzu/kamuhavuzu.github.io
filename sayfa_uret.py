# -*- coding: utf-8 -*-
"""ilanlar.json'dan kesfet/ klasorune sehir, egitim ve KPSS turu sayfalari + sitemap.xml uretir."""
import json, os, re, html
from datetime import date

KLASOR = os.path.dirname(os.path.abspath(__file__))
SITE = "https://kamuradar.github.io"
TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.translate(TR).lower()).strip("-")

def e(s):
    return html.escape(str(s or ""), quote=True)

def gun(d):
    try:
        y, m, g = d[:10].split("-")
        return f"{g}.{m}.{y}" if y != "0000" else ""
    except Exception:
        return ""

def acik(r, bugun):
    if r.get("iptal"):
        return False
    d = (r.get("deadline") or "")[:10]
    return not d or d >= bugun

SAYFA = """<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; base-uri 'none'; form-action 'none'">
<meta name="referrer" content="no-referrer">
<title>{baslik} | KamuHavuzu</title>
<meta name="description" content="{aciklama}">
<link rel="canonical" href="{site}/kesfet/{dosya}">
<link rel="icon" href="../favicon-32.png">
<style>
:root{{--bg:#f6f7f9;--kart:#fff;--yazi:#1c2430;--soluk:#5b6675;--cizgi:#dfe3e8;--vurgu:#1b5fd1}}
@media(prefers-color-scheme:dark){{:root{{--bg:#12161c;--kart:#1b212a;--yazi:#e8ecf1;--soluk:#9aa6b6;--cizgi:#2b3440;--vurgu:#6aa3ff}}}}
body{{margin:0;font:16px/1.5 system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--yazi)}}
.k{{max-width:860px;margin:0 auto;padding:16px}}
a{{color:var(--vurgu)}}h1{{font-size:24px;margin:8px 0}}
.i{{background:var(--kart);border:1px solid var(--cizgi);border-radius:12px;padding:12px 14px;margin:10px 0}}
.i b{{display:block}}.i small{{color:var(--soluk)}}
.btn{{display:inline-block;background:var(--vurgu);color:#fff;padding:8px 14px;border-radius:8px;text-decoration:none;margin:6px 0}}
.dis{{font-size:13px;color:var(--soluk);margin-top:22px}}
nav a{{margin-right:10px;font-size:14px}}
</style></head><body><div class="k">
<nav><a href="../">← KamuHavuzu</a><a href="./">Tüm başlıklar</a></nav>
<h1>{baslik}</h1>
<p>{aciklama}</p>
<a class="btn" href="../{sorgu}">Puanıma göre süz (🟢🟡🔴)</a>
{liste}
<p class="dis">KamuHavuzu resmî bir kurum sitesi değildir. Bilgiler ilan metinlerinden otomatik okunur ve hatalı olabilir; başvurudan önce resmî ilanı kontrol edin. Son güncelleme: {tarih}.</p>
</div></body></html>"""

def kart(r):
    son = gun(r.get("deadline") or "")
    alt = " · ".join(x for x in [r.get("city"), r.get("employment_type"), ("Son başvuru: " + son) if son else "Son tarih belirtilmemiş"] if x)
    link = str(r.get("link") or "")
    ok = f'<a href="{e(link)}" rel="noopener nofollow" target="_blank">Resmî ilana git →</a>' if link.startswith("http") else ""
    return f'<div class="i"><b>{e(r.get("title"))}</b><small>{e(r.get("institution"))}</small><br><small>{e(alt)}</small><br>{ok}</div>'

def yaz(dosya, baslik, aciklama, sorgu, ilanlar, bugun):
    ilanlar = sorted(ilanlar, key=lambda r: (r.get("deadline") or "9999")[:10])[:200]
    liste = "".join(kart(r) for r in ilanlar) or "<p>Şu an bu başlıkta açık ilan görünmüyor.</p>"
    with open(os.path.join(KLASOR, "kesfet", dosya), "w", encoding="utf-8") as f:
        f.write(SAYFA.format(baslik=e(baslik), aciklama=e(aciklama), site=SITE, dosya=dosya, sorgu=sorgu, liste=liste, tarih=gun(bugun)))

def main():
    with open(os.path.join(KLASOR, "ilanlar.json"), encoding="utf-8") as f:
        veri = json.load(f)
    bugun = date.today().isoformat()
    L = [r for r in veri.get("ilanlar", []) if acik(r, bugun) and not r.get("akademik")]
    os.makedirs(os.path.join(KLASOR, "kesfet"), exist_ok=True)
    for f in os.listdir(os.path.join(KLASOR, "kesfet")):
        if f.endswith(".html"):
            os.remove(os.path.join(KLASOR, "kesfet", f))
    girisler = []  # (grup, ad, dosya, sayi)

    sehirler = {}
    for r in L:
        if r.get("city"):
            sehirler.setdefault(r["city"], []).append(r)
    for c, l in sehirler.items():
        d = f"sehir-{slug(c)}.html"
        yaz(d, f"{c} kamu personel alım ilanları", f"{c} için {len(l)} açık kamu ilanı. Başvuru tarihine göre sıralıdır.", "?sehir=" + c.translate(str.maketrans({" ": "%20"})), l, bugun)
        girisler.append(("Şehirler", c, d, len(l)))

    for eg in ("Ortaöğretim", "Ön Lisans", "Lisans"):
        l = [r for r in L if eg in (r.get("egitimler") or []) or (not r.get("egitimler") and r.get("education_level") == eg)]
        d = f"egitim-{slug(eg)}.html"
        yaz(d, f"{eg} mezunu kamu alım ilanları", f"{eg} mezunlarının başvurabileceği {len(l)} açık kamu ilanı.", "?egitim=" + eg.replace(" ", "%20"), l, bugun)
        girisler.append(("Eğitim durumu", eg, d, len(l)))

    turler = {}
    for r in L:
        t = r.get("kpss_type")
        if t:
            turler.setdefault(t, []).append(r)
        for t2 in (r.get("puanlar") or {}):
            if t2 != t:
                turler.setdefault(t2, []).append(r)
    for t, l in turler.items():
        d = f"kpss-{slug(t)}.html"
        yaz(d, f"{t} ile başvurulabilen kamu ilanları", f"KPSS {t} puanıyla başvurulabilen {len(l)} açık ilan.", "?tur=" + t.replace(" ", "%20"), l, bugun)
        girisler.append(("KPSS türü", t, d, len(l)))

    for ct in ("Memur", "Sözleşmeli personel", "İşçi"):
        l = [r for r in L if r.get("employment_type") == ct]
        d = f"calisma-{slug(ct)}.html"
        yaz(d, f"{ct} alım ilanları", f"{ct} kategorisinde {len(l)} açık ilan.", "?calisma=" + ct.replace(" ", "%20"), l, bugun)
        girisler.append(("Çalışma türü", ct, d, len(l)))

    # dizin sayfasi
    govde = ""
    for grup in dict.fromkeys(g for g, *_ in girisler):
        govde += f"<h2>{e(grup)}</h2><p>" + " · ".join(
            f'<a href="{d}">{e(ad)} ({n})</a>' for g, ad, d, n in sorted(girisler, key=lambda x: -x[3]) if g == grup and n) + "</p>"
    with open(os.path.join(KLASOR, "kesfet", "index.html"), "w", encoding="utf-8") as f:
        f.write(SAYFA.format(baslik="Kamu ilanlarını başlığa göre keşfet", aciklama="Şehir, eğitim durumu, KPSS türü ve çalışma türüne göre açık kamu personel alım ilanları.", site=SITE, dosya="", sorgu="", liste=govde, tarih=gun(bugun)))

    urls = [f"{SITE}/", f"{SITE}/kesfet/", f"{SITE}/bilgi.html"] + [f"{SITE}/kesfet/{d}" for _, _, d, n in girisler if n]
    with open(os.path.join(KLASOR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
                "".join(f"<url><loc>{u}</loc><lastmod>{bugun}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    with open(os.path.join(KLASOR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    print(f"{len(girisler)} sayfa uretildi")

if __name__ == "__main__":
    main()
