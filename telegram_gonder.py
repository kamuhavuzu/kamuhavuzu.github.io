# -*- coding: utf-8 -*-
"""Yeni ilanlari Telegram kanalina gonderir. TELEGRAM_TOKEN ve TELEGRAM_KANAL tanimli degilse hicbir sey yapmaz."""
import json, os, sys, urllib.request, urllib.parse
from datetime import date

K = os.path.dirname(os.path.abspath(__file__))
TOKEN, KANAL = os.environ.get("TELEGRAM_TOKEN", ""), os.environ.get("TELEGRAM_KANAL", "")
GONDERILEN = os.path.join(K, "gonderilen.json")
SITE = "https://kamuhavuzu.github.io/"

def main():
    if not TOKEN or not KANAL:
        print("Telegram ayari yok, atlandi."); return
    ilanlar = json.load(open(os.path.join(K, "ilanlar.json"), encoding="utf-8")).get("ilanlar", [])
    bugun = date.today().isoformat()
    acik = [r for r in ilanlar if not r.get("iptal") and not r.get("akademik") and ((r.get("deadline") or "9999")[:10] >= bugun)]
    eski = json.load(open(GONDERILEN, encoding="utf-8")) if os.path.exists(GONDERILEN) else None
    ids = [str(r["id"]) for r in acik]
    if eski is None:           # ilk calisma: eski ilanlari gonderme, sadece kaydet
        json.dump(ids, open(GONDERILEN, "w", encoding="utf-8")); print("Ilk kayit, mesaj atilmadi."); return
    yeni = [r for r in acik if str(r["id"]) not in set(eski)][:10]
    for r in yeni:
        son = (r.get("deadline") or "")[:10]
        metin = f"🆕 {r.get('institution','')}\n{r.get('title','')}\n📍 {r.get('city') or '—'}" + (f"\n⏰ Son: {son[8:]}.{son[5:7]}.{son[:4]}" if son and not son.startswith("0000") else "") + f"\n🔗 {r.get('link','')}\n\nPuanına göre süz: {SITE}"
        data = urllib.parse.urlencode({"chat_id": KANAL, "text": metin, "disable_web_page_preview": "true"}).encode()
        try:
            urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data), timeout=20)
        except Exception as ex:
            print("Telegram hatasi:", type(ex).__name__); break
    json.dump(sorted(set(eski) | set(ids))[-3000:], open(GONDERILEN, "w", encoding="utf-8"))
    print(f"{len(yeni)} ilan gonderildi")

if __name__ == "__main__":
    main()
