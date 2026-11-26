"""Ilan metninden bilgi cikaran yardimci fonksiyonlar (veritabani gerektirmez)."""
import html
from datetime import date, datetime
import re

BASE = "https://www.ilan.gov.tr"
DETAIL_URL = BASE + "/api/api/services/app/AdDetail/GetAdDetail"
SEARCH_URL = BASE + "/api/api/services/app/Ad/AdsByFilter"
AD_TYPE_PERSONEL = 5
PAGE_SIZE = 12
MAX_PAGES = 60
SKIP_WORDS = ["OGRETIM UYESI", "OGRETIM GOREVLISI", "ARASTIRMA GOREVLISI", "DOCENT", "PROFESOR", "AKADEMIK"]
DELAY = 1.0
KK_RSS_URL = "https://kariyerkapisi.gov.tr/RSS"
KK_ATLA_KATEGORI = ["EGITIM"]
HEADERS = {
    "accept": "text/plain",
    "content-type": "application/json-patch+json",
    "origin": BASE,
    "referer": BASE + "/ilan/tum-ilanlar",
    "x-request-origin": "IGT-UI",
    "x-requested-with": "XMLHttpRequest",
    "user-agent": "KamuRadar/1.0 (kisisel kullanim)",
}

_TR = str.maketrans("İıÖöÜüŞşÇçĞğ", "IiOoUuSsCcGg")


def norm(text):
    """Turkce karakterleri sadelestirip BUYUK harfe cevirir (regex icin)."""
    return text.translate(_TR).upper()


def strip_html(raw):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw or ""))).strip()


def parse_education(text):
    t = norm(text).replace("ONLISANS", "ON LISANS")
    found = set()
    if "ON LISANS" in t:
        found.add("Ön Lisans")
    if re.search(r"(?<!ON )LISANS(?!USTU)", t):
        found.add("Lisans")
    if re.search(r"ORTAOGRETIM|LISE MEZUN|\bLISE\b", t):
        found.add("Ortaöğretim")
    return found.pop() if len(found) == 1 else ""   # emin degilsek bos birak


def parse_egitimler(text):
    """Metinde ACIKCA yazan egitim duzeylerini listeler (bulamazsa bos liste)."""
    t = norm(text).replace("ONLISANS", "ON LISANS")
    s = []
    if re.search(r"ON LISANS|2 YILLIK|MESLEK YUKSEKOKUL", t):
        s.append("Ön Lisans")
    if re.search(r"(?<!ON )(?<!YUKSEK )LISANS(?!USTU)|4 YILLIK", t):
        s.append("Lisans")
    if re.search(r"ORTAOGRETIM|LISE MEZUN|\bLISE\b", t):
        s.append("Ortaöğretim")
    return s


_KES = re.compile(r"[.:\n]|\s-\s|\b(?:kurumlar[a-zçğıöşü]*|fakülteler[a-zçğıöşü]*|yüksekokullar[a-zçğıöşü]*|programlar[a-zçğıöşü]*|alanlar[a-zçğıöşü]*|bölümler[a-zçğıöşü]*|mezun\s+olup|olmak)\b")
_BOLUM_SONU = re.compile(r"\b(?:bölümlerinden|bölümünden|bölümlerinin|programlarından|programından|alanlarından|alanından)\b")
_YASAK = re.compile(r"\d|mezun|olmak|kadro|sınav|puan|başvuru|kurum|yükseköğretim|üniversite|diğer|ilgili|benzeri|denk|tanınan|yurt|eşdeğer|şartı|şart|tercihen|lisans|önlisans|ön lisans|öğrenim|eğitim|tamamla|bitir|yeterlil|belge|sertifika|yaş|cinsiyet|erkek|kadın|askerlik|ve diğer|vb|vs|bölüm|program")
_KUCUK = {"ve", "veya", "ile", "ya", "da", "de"}


def _tr_kucuk(t):
    return t.replace("İ", "i").replace("I", "ı").lower()


def _baslik(t):
    out = []
    for w in t.split():
        if w in _KUCUK:
            out.append(w)
        else:
            ilk = "İ" if w[0] == "i" else ("I" if w[0] == "ı" else w[0].upper())
            out.append(ilk + w[1:])
    return " ".join(out)


def bolum_adaylari(text):
    """Ilan metnindeki 'X, Y, Z bolumlerinden mezun' kaliplarindan bolum adi adaylari (kucuk harf listesi)."""
    t = _tr_kucuk(re.sub(r"\s+", " ", text or ""))
    adaylar = set()
    for m in _BOLUM_SONU.finditer(t):
        onc = t[max(0, m.start() - 600):m.start()]
        kesimler = list(_KES.finditer(onc))
        if kesimler:
            onc = onc[kesimler[-1].end():]
        for parca in re.split(r"[,;/]", onc):
            parca = re.sub(r"^(?:ve|veya|ile|ya da|en az|bir)\s+", "", parca.strip())
            parca = re.sub(r"\s+(?:ve|veya|ile)$", "", parca).strip(" ()-")
            kel = parca.split()
            if not (2 <= len(parca) <= 70) or len(kel) > 6 or _YASAK.search(parca):
                continue
            if len(kel) == 1 and len(parca) < 4:
                continue
            adaylar.add(parca)
    return adaylar


def bolum_ogren(satirlar, onceki=None, esik=2):
    """Tum ilanlardan bolum adi ogrenir: en az `esik` farkli ilanda gecen adaylar kalici listeye eklenir."""
    sayac = {}
    for r in satirlar:
        duzeyler = r.get("egitimler") or []
        if not duzeyler:
            continue
        for ad in bolum_adaylari(f"{r.get('title', '')} {r.get('description', '')}"):
            for d in duzeyler:
                sayac.setdefault(d, {}).setdefault(ad, set()).add(r.get("id") or r.get("link"))
    sonuc = {d: set(v) for d, v in (onceki or {}).items()}
    for d, adlar in sayac.items():
        for ad, idler in adlar.items():
            if len(idler) >= esik:
                sonuc.setdefault(d, set()).add(_baslik(ad))
    return {d: sorted(v) for d, v in sonuc.items()}


def parse_kpss_type(text):
    t = norm(text)
    found = set(re.findall(r"(?<![A-Z0-9])P\s?(93|94|3)(?![0-9])", t))
    found |= set(re.findall(r"KPSSP(93|94|3)(?![0-9])", t))
    return "P" + found.pop() if len(found) == 1 else ""


_AYLAR = {"OCAK": 1, "SUBAT": 2, "MART": 3, "NISAN": 4, "MAYIS": 5, "HAZIRAN": 6,
          "TEMMUZ": 7, "AGUSTOS": 8, "EYLUL": 9, "EKIM": 10, "KASIM": 11, "ARALIK": 12}
_TARIH_RE = re.compile(
    r"(\d{1,2})\s*[./\-]\s*(\d{1,2})\s*[./\-]\s*(\d{4})"
    r"|(\d{1,2})\s+(" + "|".join(_AYLAR) + r")\s+(\d{4})"
)


def _tarihler(window):
    """Metin parcasindaki tarihleri (baslangic konumu, date) listesi olarak dondurur."""
    out = []
    for m in _TARIH_RE.finditer(window):
        try:
            if m.group(1):
                d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            else:
                d = date(int(m.group(6)), _AYLAR[m.group(5)], int(m.group(4)))
        except ValueError:
            continue
        if 2020 <= d.year <= 2035:
            out.append((m.start(), m.end(), d))
    return out


def parse_application_dates(text):
    """Ilan metninden (baslangic, bitis) basvuru tarihlerini cikarir; bulamazsa None.

    Sadece acik tarihler okunur. "Ilandan itibaren 10 gun" gibi goreli sureler
    tahmin edilmez, o durumda bitis None kalir.
    """
    t = norm(text)
    start = end = None
    for m in re.finditer(r"BASVURU", t):
        window = t[m.start(): m.start() + 260]
        found = _tarihler(window)
        if len(found) >= 2 and found[1][2] >= found[0][2]:
            return found[0][2], found[1][2]
        if len(found) == 1 and end is None and start is None:
            a, b, d = found[0]
            after = window[b: b + 40]
            son_basvuru = "SON" in t[max(0, m.start() - 6): m.start()]   # "SON BASVURU"
            if son_basvuru or re.search(r"KADAR|SONA ER|SON GUN", after):
                end = d
            elif re.search(r"ITIBAREN|BASLA", after):
                start = d
    return start, end


_SAYI = r"(?<![\d.,])(\d{2}(?:[.,]\d{1,2})?)(?!\d)"
_KPSS_PATTERNS = [
    r"EN AZ\s*" + _SAYI + r"\s*(?:\([^)]*\))?\s*PUAN",
    _SAYI + r"\s*(?:\([^)]*\))?\s*(?:PUAN\w*\s*)?(?:VE UZERI|VE YUKARI|VE USTU)",
    r"TABAN\s*PUAN\w*[^0-9]{0,40}" + _SAYI,
    r"PUAN\w*\s*EN AZ\s*" + _SAYI,
    # "70'ten az olmamak uzere", "70 puandan az olmamak"
    _SAYI + r"\s*['\u2019]?\s*(?:PUAN\w*\s*)?(?:DEN|DAN|TEN|TAN)?\s*(?:AZ|DUSUK)\s+OLMAMAK",
    # "KPSS (P93) puan turunden en az 70", "KPSS ... en dusuk 65"
    r"KPSS[^.]{0,80}?(?:EN AZ|EN DUSUK)\s*" + _SAYI,
    # "KPSS P3 taban puani 80", "KPSS P93 puan: 72"
    r"KPSS\s*\(?\s*P\s?(?:93|94|3)\s*\)?[^0-9.]{0,25}(?:TABAN|PUAN\w*)[^0-9]{0,25}" + _SAYI,
]
_KPSS_DISQUALIFY = re.compile(r"YDS|ALES|YABANCI DIL|MULAKAT|YAZILI|SOZLU")


def parse_min_kpss(text):
    """KPSS taban puanini bulur (birden fazla kadro varsa EN DUSUGUNU); yoksa None."""
    t = norm(text)
    values = []
    for pat in _KPSS_PATTERNS:
        for m in re.finditer(pat, t):
            if "KPSS" not in t[max(0, m.start() - 250): m.end() + 50]:
                continue
            if _KPSS_DISQUALIFY.search(t[max(0, m.start() - 50): m.start()]):
                continue
            v = float(m.group(1).replace(",", "."))
            if 40 <= v <= 100:
                values.append(v)
    return min(values) if values else None


def build_link(url_str):
    """API'nin verdigi yolu tam adrese cevirir."""
    u = re.sub(r"\s+", "-", (url_str or "").strip())   # API bazen slug icinde bosluk veriyor
    if u.lower().startswith("http"):
        return u
    return BASE + (u if u.startswith("/") else "/" + u)


def guess_employment(text):
    """Alim turunu metinden tahmin eder (kesin degil)."""
    t = norm(text)
    if "SOZLESMELI" in t:
        return "Sözleşmeli personel"
    if re.search(r"\bISCI\b", t):
        return "İşçi"
    if "MEMUR" in t:
        return "Memur"
    return "Diğer"



def fetch_detail(session, ad_id):
    """Ilan detayini ceker: (duz metin, ham json)"""
    r = session.get(DETAIL_URL, params={"id": ad_id}, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("success", False):
        return "", data
    return strip_html((data.get("result") or {}).get("content", "")), data



def kk_calisma_turu(kategori):
    c = norm(kategori)
    if "MEMUR" in c:
        return "Memur"
    if "SOZLESMELI" in c:
        return "Sözleşmeli personel"
    if "ISCI" in c:
        return "İşçi"
    return "Diğer"


def kk_ayir(baslik):
    """'KURUM - Ilan basligi' -> (kurum, baslik); basta tekrar eden kurum adini atar."""
    parts = baslik.split(" - ", 1)
    if len(parts) < 2:
        return "", baslik.strip()
    kurum, rest = parts[0].strip(), parts[1].strip()
    while kurum and rest.startswith(kurum + " - "):
        rest = rest[len(kurum) + 3:].strip()
    return kurum, rest



# ---------------------------------------------------------------- sehir / baslik / tarih yardimcilari
SEHIRLER = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin",
            "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa",
            "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum",
            "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir",
            "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kilis", "Kırıkkale", "Kırklareli",
            "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Mersin", "Muğla", "Muş", "Nevşehir",
            "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Şanlıurfa", "Siirt", "Sinop", "Sivas", "Şırnak",
            "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"]
_SEHIR_RE = {s: re.compile(r"(?<![A-Z0-9])" + re.escape(norm(s)) + r"(?:'?(?:DA|DE|TA|TE|DAKI|DEKI|IN|UN))?(?![A-Z0-9])") for s in SEHIRLER}
_SEHIR_ESKI = {"URFA": "Şanlıurfa", "ANTEP": "Gaziantep", "MARAS": "Kahramanmaraş", "ICEL": "Mersin"}


def bul_sehir(oncelikli, detay=""):
    """Once baslik/kurumda arar; yoksa detay metninde en az 2 kez gecen sehri alir."""
    t = norm(oncelikli or "")
    for s, re_ in _SEHIR_RE.items():
        if s in ("Van", "Ordu", "Kars") and not re.search(r"(?<![A-Z])" + norm(s) + r"(?:\s+(?:IL|VALILIGI|BELEDIYE|BUYUKSEHIR|UNIVERSITE))", t):
            continue
        if re_.search(t):
            return s
    d = norm(detay or "")
    en, n = "", 1
    for s, re_ in _SEHIR_RE.items():
        if s in ("Van", "Ordu", "Kars"):
            continue
        k = len(re_.findall(d))
        if k > n:
            en, n = s, k
    return en


_AY_NO = {"OCAK": 1, "SUBAT": 2, "MART": 3, "NISAN": 4, "MAYIS": 5, "HAZIRAN": 6,
          "TEMMUZ": 7, "AGUSTOS": 8, "EYLUL": 9, "EKIM": 10, "KASIM": 11, "ARALIK": 12}
_AYLAR_RE = "|".join(_AY_NO)
_ARALIK_RE = re.compile(r"(\d{1,2})\s*(" + _AYLAR_RE + r")\s*(?:(\d{4}))?\s*[-–—]\s*(\d{1,2})\s*(" + _AYLAR_RE + r")\s*(?:(\d{4}))?")


def baslik_duzelt(t):
    """'ALACAK25 Kasim - 14 Aralik' -> 'ALACAK 25 Kasim - 14 Aralik'"""
    t = re.sub(r"\s+", " ", t or "").strip()
    return re.sub(r"([A-Za-zÇĞİÖŞÜçğıöşü\)])(\d{1,2}\s+(?:%s))" % "|".join(
        m.capitalize() for m in ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")),
        r"\1 \2", t)


def parse_tarih_araligi(text, bugun=None):
    """'25 Kasim - 14 Aralik' (yilsiz olabilir) -> (baslangic, bitis) ya da (None, None)."""
    from datetime import date, timedelta
    bugun = bugun or date.today()
    m = _ARALIK_RE.search(norm(text))
    if not m:
        return None, None
    d1, a1, y1, d2, a2, y2 = m.groups()
    try:
        for y in ([int(y1)] if y1 else [bugun.year - 1, bugun.year, bugun.year + 1]):
            bas_ = date(y, _AY_NO[a1], int(d1))
            yb = int(y2) if y2 else (y if _AY_NO[a2] >= _AY_NO[a1] else y + 1)
            bit = date(yb, _AY_NO[a2], int(d2))
            if bit >= bas_ and (bugun - timedelta(days=60)) <= bit <= (bugun + timedelta(days=300)):
                return bas_, bit
    except ValueError:
        pass
    return None, None


_KURUM_SON = r"(?:BASKANLIGI|BASKANLIK|MUDURLUGU|BAKANLIGI|AJANSI|REKTORLUGU|BELEDIYESI|BELEDIYE BASKANLIGI|UNIVERSITESI|KURUMU|KURULU|ODASI|KOMUTANLIGI|MUSTESARLIGI|HASTANESI|VALILIGI|KAYMAKAMLIGI|BIRLIGI)"


def baslik_ayir(baslik):
    """Basliktan (kurum, kontenjan) tahmin eder."""
    n = norm(baslik)
    kurum, kontenjan = "", None
    m = re.search(r"^(.+?" + _KURUM_SON + r")\b", n)
    if m:
        kurum = baslik[:m.end()].strip()
    else:
        m = re.search(r"^(.+?)\s+\d+\s+(?:SOZLESMELI|MEMUR|ISCI|PERSONEL|KADRO|ENGELLI|SURekli)", n, re.I)
        if m:
            kurum = baslik[:m.end(1)].strip()
    q = re.search(r"(?<!\d)(\d{1,4})\s+(?:SOZLESMELI|MEMUR|ISCI|PERSONEL|ENGELLI|KADRO|ADET|KISI)", n)
    q = q or re.search(r"\((\d{1,4})\s*ADET\)", n)
    if q:
        kontenjan = int(q.group(1))
    return kurum, kontenjan


def duz_metin(raw):
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw or "")
    return strip_html(raw)


# ---------------------------------------------------------------- tablo bicimli puan ("P3 En az 75 puan")
_TABLO_RE = re.compile(r"(?<![A-Z0-9])(P\s?\d{1,3})\s+(?:EN AZ|ASGARI)\s+(\d{2}(?:[.,]\d{1,2})?)\s*(?:\([^)]*\))?\s*PUAN")
_ASGARI_RE = re.compile(r"(?:ASGARI|EN AZ)\s+(?:[A-Z]{3,12}\s*)?\(?(\d{2}(?:[.,]\d{1,2})?)\)?\s*(?:\([^)]*\))?\s*(?:PUAN|VE (?:DAHA )?(?:YUKSEK|UZERI))")


def parse_puan_tablosu(text):
    """KPSS puan turu ve esigini tablodan veya aciklama cumlesinden eslestirir."""
    t = norm(text)
    sonuc = {}
    for m in _TABLO_RE.finditer(t):
        tur = m.group(1).replace(" ", "")
        v = float(m.group(2).replace(",", "."))
        if 40 <= v <= 100:
            sonuc[tur] = min(sonuc.get(tur, v), v)

    # Bazi ilanlarda tablo yalnizca KPSSP3/P93 turunu yazar; asgari puan
    # asagidaki genel sartlarda gecer. Ayni metin blogundaki tur-puani bagla.
    tur_re = re.compile(r"KPSS\s*\(?\s*(P\s?(?:93|94|3))\s*\)?")
    for mt in tur_re.finditer(t):
        pencere = t[mt.start():mt.start() + 1200]
        # Farkli bir KPSS turu baslarsa bu tur icin aramayi orada durdur.
        sonraki = tur_re.search(t, mt.end())
        if sonraki and sonraki.group(1).replace(" ", "") != mt.group(1).replace(" ", ""):
            pencere = t[mt.start():sonraki.start()]
        puan_eslesme = re.search(
            r"(?:EN AZ|EN DUSUK|ASGARI)\s*(\d{2}(?:[.,]\d{1,2})?)\s*(?:PUAN)?",
            pencere
        )
        if not puan_eslesme:
            continue
        deger = float(puan_eslesme.group(1).replace(",", "."))
        if 40 <= deger <= 100:
            tur = mt.group(1).replace(" ", "")
            sonuc[tur] = min(sonuc.get(tur, deger), deger)
    return sonuc


def parse_puan_ek(text):
    """'KPSS ... asgari 70 (yetmis) puan' gibi cumlelerden tek puan (yoksa None)."""
    n = norm(text)
    if "KPSS" not in n:
        return None
    degerler = []
    for m in _ASGARI_RE.finditer(n):
        once = n[max(0, m.start() - 160):m.start() + 60]
        if "KPSS" not in once or _KPSS_DISQUALIFY.search(n[max(0, m.start() - 40):m.start()]):
            continue
        v = float(m.group(1).replace(",", "."))
        if 40 <= v <= 100:
            degerler.append(v)
    return min(degerler) if degerler else None


def tur_egitim(tur):
    t = tur.upper()
    if t == "P93":
        return "Ön Lisans"
    if t == "P94":
        return "Ortaöğretim"
    return "Lisans"
