#!/usr/bin/env python3
"""KamuRadar toplayici: birden cok kaynaktan ilan toplar, ilanlar.json'a yazar.

Her kaynak ayri calisir; biri hata verirse digerleri devam eder. Sonuc durumu
(tamam / hata / kontrol-edilmeli) ilanlar.json icindeki "kaynaklar" alanina yazilir,
sitede kaynak rozetleri olarak gorunur.

Kaynak listesi:
  1) ilan.gov.tr         (Basin Ilan Kurumu, ic servisi)
  2) Kariyer Kapisi      (resmi RSS)
  3) ek_kaynaklar.json   (RSS ya da HTML sayfa: istedigin kadar kaynak eklenebilir)
  4) manuel_ilanlar.json (elle yazdigin ilanlar)

Bilgisayarinda:  python ilan_cek_web.py
"""
import hashlib
import html
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urljoin

if sys.platform == "win32":   # Windows'ta sistemin sertifika deposunu kullan (SSL hatasini onler)
    try:
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass

import requests

import ayristir as ic

KLASOR = os.path.dirname(os.path.abspath(__file__))
CIKTI = os.path.join(KLASOR, "ilanlar.json")
EK_KAYNAK_DOSYASI = os.path.join(KLASOR, "ek_kaynaklar.json")
MANUEL_DOSYASI = os.path.join(KLASOR, "manuel_ilanlar.json")
ESKI_GUN = 30            # geriye donuk uyumluluk: ilanlar silinmez, arsivlenir
TARIHSIZ_GUN = 60        # tarihsiz ilanlar silinmez; kontrol gerektiren olarak korunur
ACIKLAMA_SINIR = 6000
DETAY_METIN_LIMIT = 30000
PDF_EK_LIMIT = 5
PDF_BOYUT_LIMIT = 12 * 1024 * 1024
DETAY_LIMIT = 80         # her kaynakta bir calismada en fazla bu kadar ilan sayfasi acilir
UA = {"user-agent": "Mozilla/5.0 (compatible; KamuRadar/1.0; kisisel kullanim)"}


def iso(d):
    return d.isoformat() if d else None


def satir_id(link):
    return int(hashlib.md5(link.encode("utf-8")).hexdigest()[:8], 16)


def temel_satir(link, **alanlar):
    row = {
        "id": satir_id(link), "institution": "", "title": "", "city": "", "department": "Herhangi",
        "education_level": "", "kpss_type": "", "min_kpss": None, "quota": None,
        "deadline": None, "application_start": None, "link": link, "source_url": link,
        "source_name": "", "employment_type": "Diğer", "description": "",
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    row.update(alanlar)
    return row


def _pdf_metinini_oku(session, url):
    """PDF ekindeki metni guvenli boyut/sayfa sinirlariyla cikarir."""
    try:
        r = session.get(url, headers=UA, timeout=35, stream=True)
        if r.status_code != 200:
            return ""
        uzunluk = int(r.headers.get("content-length") or 0)
        if uzunluk > PDF_BOYUT_LIMIT:
            return ""
        parca = bytearray()
        for blok in r.iter_content(65536):
            if not blok:
                continue
            parca.extend(blok)
            if len(parca) > PDF_BOYUT_LIMIT:
                return ""
        if not parca.startswith(b"%PDF"):
            return ""
        from io import BytesIO
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(bytes(parca)), strict=False)
        sayfalar = []
        for sayfa in reader.pages[:40]:
            try:
                metin = sayfa.extract_text() or ""
                if metin:
                    sayfalar.append(metin)
            except Exception:
                continue
        return "\n".join(sayfalar)[:DETAY_METIN_LIMIT]
    except Exception as e:
        print(f"[PDF] metin okunamadi: {type(e).__name__}: {url}")
        return ""


def detay_oku(session, url):
    """Ilan sayfasini ve bagli PDF eklerini okuyup tam metni dondurur."""
    try:
        r = session.get(url, headers=UA, timeout=25)
        if r.status_code != 200:
            return ""
        ham = r.content.decode(r.encoding or "utf-8", "replace")
        metin = ic.duz_metin(ham)
        # Ilan sayfasindaki PDF eklerini de oku; metin ana sayfa metninin
        # arkasina eklenir, boylece ust menu puan bilgisini gizleyemez.
        pdfler = []
        for m in re.finditer(r"""href\s*=\s*["']([^"']+\.pdf(?:\?[^"']*)?)["']""", ham, re.I):
            pdf_url = urljoin(url, html.unescape(m.group(1)))
            if pdf_url not in pdfler:
                pdfler.append(pdf_url)
            if len(pdfler) >= PDF_EK_LIMIT:
                break
        ekler = []
        for pdf_url in pdfler:
            pdf_metin = _pdf_metinini_oku(session, pdf_url)
            if pdf_metin:
                ekler.append(f"\n[PDF EKI: {pdf_url}]\n{pdf_metin}")
        return (metin + "\n" + "\n".join(ekler))[:DETAY_METIN_LIMIT]
    except requests.RequestException:
        return ""


def detaydan_doldur(row, metin):
    """Detay metninden bos kalan alanlari doldurur."""
    if not metin:
        return
    tum = f"{row.get('title', '')} {metin}"
    row["description"] = (row.get("description", "") + " | " + metin)[:ACIKLAMA_SINIR]
    if not row.get("min_kpss"):
        row["min_kpss"] = ic.parse_min_kpss(tum)
    if row.get("kpss_type") in ("", None):
        row["kpss_type"] = ic.parse_kpss_type(tum)
    puanlar = ic.parse_puan_tablosu(tum)
    if puanlar:
        row["puanlar"] = {**(row.get("puanlar") or {}), **puanlar}
        row["min_kpss"] = min(puanlar.values())
    if not row.get("education_level"):
        row["education_level"] = ic.parse_education(tum)
    if not row.get("deadline"):
        b, e = ic.parse_application_dates(metin)
        row["deadline"] = row["deadline"] or iso(e)
        row["application_start"] = row.get("application_start") or iso(b)
    if not row.get("city"):
        row["city"] = ic.bul_sehir(f"{row.get('institution', '')} {row.get('title', '')}", metin)
    if row.get("employment_type") in ("", None, "Diğer"):
        row["employment_type"] = ic.guess_employment(tum)


# ---------------------------------------------------------------- 1) ilan.gov.tr
def ek_sertifika_paketi(host):
    """Sitenin eksik 'ara sertifika'sini kendi sertifikasindaki adresten (AIA) indirip
    certifi listesiyle birlestirir. Linux sunucularda 'SSLCertVerificationError' hatasini cozer."""
    import socket
    import ssl
    import tempfile

    import certifi
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, 443), timeout=20) as s, ctx.wrap_socket(s, server_hostname=host) as t:
        der = t.getpeercert(binary_form=True)
    cert = x509.load_der_x509_certificate(der)
    pemler = []
    for _ in range(4):
        try:
            aia = cert.extensions.get_extension_for_class(x509.AuthorityInformationAccess).value
        except x509.ExtensionNotFound:
            break
        urller = [d.access_location.value for d in aia
                  if d.access_method == x509.oid.AuthorityInformationAccessOID.CA_ISSUERS]
        if not urller:
            break
        veri = requests.get(urller[0], timeout=20).content
        try:
            cert = x509.load_der_x509_certificate(veri)
        except ValueError:
            cert = x509.load_pem_x509_certificate(veri)
        pemler.append(cert.public_bytes(serialization.Encoding.PEM))
    yol = os.path.join(tempfile.gettempdir(), "kamuradar_ca.pem")
    with open(certifi.where(), "rb") as f:
        temel = f.read()
    with open(yol, "wb") as f:
        f.write(temel + b"\n" + b"\n".join(pemler))
    print(f"[ilan.gov.tr] eksik ara sertifika tamamlandi ({len(pemler)} sertifika eklendi)")
    return yol


def ilan_gov_tr(session, mevcut, **_):
    try:
        session.post(ic.SEARCH_URL, json={"keys": {"ats": [ic.AD_TYPE_PERSONEL]}, "skipCount": 0, "maxResultCount": 1},
                     headers=ic.HEADERS, timeout=30)
    except requests.exceptions.SSLError:
        print("[ilan.gov.tr] SSL sertifika hatasi, eksik ara sertifika araniyor...")
        session.verify = ek_sertifika_paketi("www.ilan.gov.tr")
    eklenen = 0
    geri_hak = 250
    for page in range(ic.MAX_PAGES):
        keys = {"ats": [ic.AD_TYPE_PERSONEL]}
        if page > 0:
            keys["currentPage"] = [page + 1]
        payload = {"keys": keys, "skipCount": page * ic.PAGE_SIZE, "maxResultCount": ic.PAGE_SIZE}
        r = session.post(ic.SEARCH_URL, json=payload, headers=ic.HEADERS, timeout=30)
        r.raise_for_status()
        result = r.json().get("result") or {}
        ads = result.get("ads") or []
        if page == 0:
            print(f"[ilan.gov.tr] sitedeki toplam ilan: {result.get('numFound', '?')}")
        if not ads:
            break
        toplam = int(result.get("numFound") or 0)
        for ad in ads:
            if ad.get("isArchived") or not ad.get("urlStr"):
                continue
            # Sonuc duyurulari ve kamu alimi olmayan mesleki sinavlari detay
            # sayfasini indirmeden ele; asil personel alimi ilanlari korunur.
            baslik_on = str(ad.get("title") or "")
            kurum_on = str(ad.get("advertiserName") or "")
            duz_on = ic.norm(baslik_on + " " + kurum_on)
            if _TURMOB_RE.search(duz_on) or _ILAN_DISI.search(duz_on):
                continue
            if not getattr(ilan_gov_tr, "_anahtar_yazildi", False):
                ilan_gov_tr._anahtar_yazildi = True
                print("[ilan.gov.tr] ilan alanlari:", sorted(ad.keys()))
            if not getattr(ilan_gov_tr, "_logo_yazildi", False):
                ilan_gov_tr._logo_yazildi = True
                print("[ilan.gov.tr] logo ornekleri:", {k: str(ad.get(k))[:120] for k in ("advertiserLogo", "adSourceLogoPath", "mainPhoto")})
            logo = logo_al(ad, session)
            akademik = any(w in ic.norm(f"{ad.get('title', '')} {ad.get('advertiserName', '')}") for w in ic.SKIP_WORDS)
            link = ic.build_link(ad["urlStr"])
            if link in mevcut:
                eski_r = mevcut[link]
                if not str(eski_r.get("logo") or "").startswith("https://"):
                    eski_r["logo"] = logo_al(ad, session)
                if "basvuru_adresleri" not in eski_r and geri_hak > 0:   # eski kayitlara basvuru adresini sonradan ekle
                    geri_hak -= 1
                    time.sleep(ic.DELAY)
                    try:
                        govde, _d = ic.fetch_detail(session, ad.get("id"))
                        eski_r["basvuru_adresleri"] = adresleri_bul(govde)
                        eski_r["basvuru_oneri"] = oneri_bul(govde)
                        eski_r["basvuru_eposta"] = eposta_bul(govde)
                        eski_r["description"] = govde[:ACIKLAMA_SINIR] or eski_r.get("description", "")
                    except (requests.RequestException, ValueError):
                        pass
                continue
            time.sleep(ic.DELAY)
            try:
                body, _d = ic.fetch_detail(session, ad.get("id"))
            except (requests.RequestException, ValueError) as e:
                print(f"Detay alinamadi ({ad.get('id')}): {e}")
                body = ""
            metin = f"{ad.get('title', '')} {body}"
            bas, bit = ic.parse_application_dates(metin)
            mevcut[link] = temel_satir(
                link, institution=ad.get("advertiserName") or "", title=ad.get("title") or "",
                city=ad.get("addressCityName") or "", education_level=ic.parse_education(metin),
                kpss_type=ic.parse_kpss_type(metin), min_kpss=ic.parse_min_kpss(metin),
                deadline=iso(bit), application_start=iso(bas), puanlar=ic.parse_puan_tablosu(metin),
                source_name="ilan.gov.tr", employment_type=ic.guess_employment(metin),
                description=body[:ACIKLAMA_SINIR], akademik=akademik, logo=logo,
                basvuru_adresleri=adresleri_bul(body), basvuru_oneri=oneri_bul(body), basvuru_eposta=eposta_bul(body))
            eklenen += 1
            print(f"+ {ad.get('advertiserName')} - {ad.get('title')}")
        time.sleep(ic.DELAY)
        if toplam and (page + 1) * ic.PAGE_SIZE >= toplam:
            break
    return eklenen


# ---------------------------------------------------------------- 2) Kariyer Kapisi
KK_LOGO_RE = re.compile(r"(?:https?://(?:www\.)?kariyerkapisi\.gov\.tr)?/UPS/[0-9a-fA-F\-]{30,40}\.(?:png|jpe?g|webp|gif)", re.I)


def kk_logo(item):
    """Kariyer Kapisi RSS ogesinde (enclosure, aciklama, herhangi bir alan) kurum logosu adresi varsa dondurur."""
    ham = ET.tostring(item, encoding="unicode")
    for m in KK_LOGO_RE.finditer(ham):
        u = m.group(0)
        return ("https://kariyerkapisi.gov.tr" + u) if u.startswith("/") else u.replace("http://", "https://", 1)
    enc = item.find("enclosure")
    if enc is not None and str(enc.get("url", "")).lower().startswith("https://kariyerkapisi.gov.tr/"):
        return enc.get("url")
    return ""


def kariyer_kapisi(session, mevcut, **_):
    r = session.get(ic.KK_RSS_URL, headers={**UA, "accept": "application/rss+xml, application/xml"}, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    eklenen = 0
    detay_hak = 0   # Kariyer Kapisi ilan sayfalari JavaScript ile yukleniyor, okunamaz
    for item in root.iter("item"):
        link = (item.findtext("link") or "").strip()
        baslik = (item.findtext("title") or "").strip()
        if not getattr(kariyer_kapisi, "_alan_yazildi", False):
            kariyer_kapisi._alan_yazildi = True
            print("[kk] ilan alanlari:", sorted({c.tag for c in item}), "| logo:", kk_logo(item) or "yok")
        logo_kk = kk_logo(item)
        kategori = (item.findtext("category") or "").strip()
        if not link or not baslik or any(w in ic.norm(kategori) for w in ic.KK_ATLA_KATEGORI):
            continue
        if _ILAN_DISI.search(ic.norm(baslik)):
            continue
        try:
            tarih = parsedate_to_datetime(item.findtext("pubDate") or "").date()
        except (TypeError, ValueError):
            tarih = None
        if link in mevcut:
            if logo_kk and not mevcut[link].get("logo"):
                mevcut[link]["logo"] = logo_kk
            if tarih and not mevcut[link].get("application_start"):
                mevcut[link]["application_start"] = iso(tarih)
            continue
        kurum, ilan_basligi = ic.kk_ayir(baslik)
        metin = f"{baslik} {kategori}"
        mevcut[link] = temel_satir(
            link, institution=kurum or ilan_basligi, title=ilan_basligi, application_start=iso(tarih),
            source_name="Kariyer Kapısı", employment_type=ic.kk_calisma_turu(kategori),
            description=f"{baslik} ({kategori})", education_level=ic.parse_education(metin), logo=logo_kk,
            akademik=any(w in ic.norm(metin) for w in ic.SKIP_WORDS))
        if detay_hak > 0:
            detay_hak -= 1
            time.sleep(0.4)
            detaydan_doldur(mevcut[link], detay_oku(session, link))
        mevcut[link]["city"] = mevcut[link].get("city") or ic.bul_sehir(f"{kurum} {ilan_basligi}")
        eklenen += 1
        print(f"+ {kurum or ilan_basligi} - {ilan_basligi}")
    return eklenen


# ---------------------------------------------------------------- 3) ek kaynaklar
class _LinkOkuyucu(HTMLParser):
    def __init__(self):
        super().__init__()
        self.linkler, self._href, self._metin = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._metin = []

    def handle_data(self, data):
        if self._href is not None:
            self._metin.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.linkler.append((self._href, re.sub(r"\s+", " ", "".join(self._metin)).strip()))
            self._href = None


def ek_kaynak(session, mevcut, kaynak=None, **_):
    """ek_kaynaklar.json'daki bir kaynagi okur. tur: 'rss' ya da 'html'."""
    ad, url = kaynak["ad"], kaynak["url"]
    anahtar = [ic.norm(k) for k in kaynak.get("anahtar", [])]
    kontrol = bool(kaynak.get("deneme", False))
    r = session.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    bulunan = []   # (link, baslik, tarih)
    if kaynak.get("tur") == "rss":
        root = ET.fromstring(r.content)
        for item in root.iter("item"):
            try:
                t = parsedate_to_datetime(item.findtext("pubDate") or "").date()
            except (TypeError, ValueError):
                t = None
            bulunan.append(((item.findtext("link") or "").strip(), (item.findtext("title") or "").strip(), t))
    else:
        p = _LinkOkuyucu()
        p.feed(r.content.decode("utf-8", "replace"))
        for href, metin in p.linkler:
            if href and not href.startswith(("#", "javascript:", "mailto:")):
                bulunan.append((urljoin(url, href), metin, None))
    link_liste = bool(kaynak.get("link_liste", False))   # detay adresi gecici ise listeye yonlendir
    # Liste adresi kullanan kaynaklarin eski ilanlarini silme.
    # Kaynaktaki ilan gecici olarak listeden kalksa bile kayit arsivde korunur.
    eklenen = 0
    detay_hak = DETAY_LIMIT if kaynak.get("detay") else 0
    for gercek, baslik, tarih in bulunan:
        if not gercek or len(baslik) < 25:
            continue
        if anahtar and not any(k in ic.norm(baslik) for k in anahtar):
            continue
        baslik = ic.baslik_duzelt(baslik)
        duz_baslik = ic.norm(baslik)
        if _TURMOB_RE.search(duz_baslik) or _ILAN_DISI.search(duz_baslik):
            continue
        link = (url + "#" + hashlib.md5(baslik.encode("utf-8")).hexdigest()[:10]) if link_liste else gercek
        if link in mevcut:
            # Daha once eklenen ilanlarda da eksik KPSS puanlarini yeniden tara.
            # Yeni uzun-metin/PDF okuyucusu eski kayitlari da geriye donuk tamamlar.
            eski_row = mevcut[link]
            if detay_hak > 0 and (not eski_row.get("min_kpss") or not eski_row.get("puanlar")):
                detay_hak -= 1
                time.sleep(0.25)
                detaydan_doldur(eski_row, detay_oku(session, gercek))
            continue
        bas, bit = ic.parse_tarih_araligi(baslik)
        if not bit:
            bas, bit = ic.parse_application_dates(baslik)
        kurum, kont = ic.baslik_ayir(baslik)
        mevcut[link] = temel_satir(
            link, institution=kurum or kaynak.get("kurum") or ad, title=baslik, source_name=ad, source_url=url,
            application_start=iso(bas or tarih), deadline=iso(bit), quota=kont,
            education_level=ic.parse_education(baslik), kpss_type=ic.parse_kpss_type(baslik),
            min_kpss=ic.parse_min_kpss(baslik), employment_type=ic.guess_employment(baslik),
            description=baslik, kontrol_gerekli=kontrol,
            akademik=any(w in ic.norm(baslik) for w in ic.SKIP_WORDS))
        if detay_hak > 0:
            detay_hak -= 1
            time.sleep(0.4)
            detaydan_doldur(mevcut[link], detay_oku(session, gercek))
        mevcut[link]["city"] = mevcut[link].get("city") or ic.bul_sehir(mevcut[link]["institution"] + " " + baslik)
        eklenen += 1
        print(f"+ [{ad}] {baslik}")
    return eklenen


# ---------------------------------------------------------------- 4) elle girilenler
def manuel_ilanlar(mevcut):
    if not os.path.exists(MANUEL_DOSYASI):
        return 0
    with open(MANUEL_DOSYASI, encoding="utf-8") as f:
        liste = json.load(f)
    n = 0
    for m in liste:
        if not m.get("link") or not m.get("title"):
            continue
        alanlar = {k: v for k, v in m.items() if k != "link"}
        alanlar.setdefault("source_name", "Manuel ekleme")
        satir = temel_satir(m["link"], **alanlar)
        eski = mevcut.get(m["link"])
        if eski:
            satir["checked_at"] = eski.get("checked_at", satir["checked_at"])
        mevcut[m["link"]] = satir
        n += 1
    return n


# ---------------------------------------------------------------- ortak
def puanlari_yenile(mevcut):
    n = 0
    for row in mevcut.values():
        metin = f"{row.get('title', '')} {row.get('description', '')}"
        if not row.get("min_kpss"):
            p = ic.parse_min_kpss(metin)
            if p is not None:
                row["min_kpss"] = p
                n += 1
        if not row.get("deadline"):
            _, bit = ic.parse_application_dates(metin)
            if bit:
                row["deadline"] = iso(bit)
        if not row.get("education_level"):
            row["education_level"] = ic.parse_education(metin)
        if not isinstance(row.get("puanlar"), dict) or not row.get("puanlar"):
            pt = ic.parse_puan_tablosu(metin)
            row["puanlar"] = pt
            if pt:
                row["min_kpss"] = min(pt.values())
                row["egitimler"] = sorted({ic.tur_egitim(t) for t in pt})
                n += 1
        # egitim: once ilan metninde ACIKCA yazan; yoksa KPSS turunden tahmin (isaretli)
        e = ic.parse_egitimler(metin)
        if e:
            row["egitimler"] = e
            row["egitim_tahmin"] = False
        elif row.get("puanlar"):
            row["egitimler"] = sorted({ic.tur_egitim(t) for t in row["puanlar"]})
            row["egitim_tahmin"] = True
        if not row.get("min_kpss"):
            p = ic.parse_puan_ek(metin)
            if p is not None:
                row["min_kpss"] = p
                n += 1
        nn = ic.norm(row.get("title", ""))
        ilk = ic.norm((row.get("description") or "")[:700])
        if re.search(r"\bIPTAL\b|DUZELTME ILANI", nn) or "IPTAL ILANI" in ilk[:250] or "DUZELTME ILANI" in ilk[:250]:
            row["iptal"] = True
        if any(w in ilk or w in nn for w in ("OGRETIM ELEMANI", "OGRETIM UYESI", "ARASTIRMA GOREVLISI", "OGRETIM GOREVLISI")):
            row["akademik"] = True
        d = row.get("description") or ""
        if "sayfa bulunamad" in d.lower() or "Ã" in d or "Ä" in d:   # bozuk/404 sayfa metni
            row["description"] = row.get("title", "")
        if not row.get("city"):
            row["city"] = ic.bul_sehir(f"{row.get('institution', '')} {row.get('title', '')}", row.get("description", ""))
    return n


URL_RE = re.compile(r"https?://[^\s)\]>\"'«»]+", re.I)
BOSLUK_ALAN_RE = re.compile(r"(?<![/\w@.\-])((?:www\.)?[a-z0-9\-]+(?:\.[a-z0-9\-]+)*\.(?:gov|edu|bel|org|com|net)\.tr(?:/[^\s)\]>\"'«»]*)?)", re.I)
ONERI_ATLA = ("ilan.gov.tr", "mevzuat.gov.tr", "resmigazete.gov.tr", "turkiye.gov.tr", "kariyerkapisi.gov.tr")


def _duzelt(u):
    u = u.strip().rstrip(".,;:")
    if not re.match(r"https?://", u, re.I):
        u = "https://" + u
    return re.sub(r"^http://", "https://", u, flags=re.I)


def _urller(metin):
    """(adres, metindeki konum) listesi; https olmayanlar https'e cevrilir, ayni adres tekrar edilmez."""
    bulunan, gorulen = [], set()
    for m in list(URL_RE.finditer(metin or "")) + list(BOSLUK_ALAN_RE.finditer(metin or "")):
        u = _duzelt(m.group(0) if m.re is URL_RE else m.group(1))
        anahtar = re.sub(r"^https://(www\.)?", "", u.lower()).rstrip("/")
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        bulunan.append((u, m.start()))
    return sorted(bulunan, key=lambda x: x[1])


LOGO_CDN = "https://medya.ilan.gov.tr/"   # ilan.gov.tr/assets/appconfig.production.json -> cdnBaseUrl
_LOGO = {"test": False}


def logo_al(ad, session=None):
    """Ilani yayimlayan kurumun logosu (advertiserLogo) icin tam adres; yoksa bos."""
    v = str(ad.get("advertiserLogo") or "").strip().replace("\\", "/").lstrip("/")
    if not v or v.lower() in ("null", "none"):
        return ""
    if v.lower().startswith(("http://", "https://")):
        url = v.replace("http://", "https://", 1)
    else:
        url = LOGO_CDN + v
    if not _LOGO["test"] and session is not None:   # ilk logoyu bir kez dene, sonucu kayda yaz
        _LOGO["test"] = True
        try:
            r = session.get(url, headers=UA, timeout=15, stream=True)
            print(f"[logo] test {r.status_code} {(r.headers.get('content-type') or '')[:20]} {url}")
            r.close()
        except requests.RequestException as e:
            print(f"[logo] test hata {type(e).__name__} {url}")
    return url


def _ayni_kurum(a, b):
    """Iki kurum adi ayni kurumu mu gosteriyor? (gurultu kelimeleri atilip belirteclerin ortusmesine bakilir)"""
    ka, kb = set(_kurum_anahtar(a).split()), set(_kurum_anahtar(b).split())
    if len(ka) < 2 or len(kb) < 2:
        return False
    return ka == kb or len(ka & kb) / len(ka | kb) >= 0.75


def logo_haritasi(mevcut):
    """Logosu olmayan ilanlara: (1) kurum_logolari.json, (2) ayni kurumun baska ilanindan/Kariyer Kapisi'ndan ogrenilen logo uygulanir."""
    yol = os.path.join(KLASOR, "kurum_logolari.json")
    bilinen = []   # (kurum adi, logo)
    if os.path.exists(yol):
        with open(yol, encoding="utf-8") as f:
            bilinen += [(k, v) for k, v in json.load(f).items() if str(v).startswith("https://")]
    for r in mevcut.values():
        if str(r.get("logo") or "").startswith("https://") and r.get("institution"):
            bilinen.append((r["institution"], r["logo"]))
    n = 0
    for r in mevcut.values():
        if str(r.get("logo") or "").startswith("https://") or not r.get("institution"):
            continue
        for k, v in bilinen:
            if _ayni_kurum(k, r["institution"]):
                r["logo"] = v; n += 1; break
    sayac = {}
    for r in mevcut.values():
        if not str(r.get("logo") or "").startswith("https://") and not r.get("akademik"):
            sayac[r.get("institution", "?")] = sayac.get(r.get("institution", "?"), 0) + 1
    print(f"Logo uygulanan: {n}; logolu ilan: {sum(1 for r in mevcut.values() if str(r.get('logo') or '').startswith('https://'))}/{len(mevcut)}")
    print("[logo] logosuz kurumlar:", " | ".join(f"{k} ({v})" for k, v in sorted(sayac.items(), key=lambda x: -x[1])[:60]))


def adresleri_bul(metin):
    """Ilan metnindeki disari giden (ilan.gov.tr disi) web adreslerini, sirayla en fazla 5 tane dondurur."""
    return [u for u, _ in _urller(metin) if "ilan.gov.tr" not in u.lower()][:5]


def oneri_bul(metin):
    """'Basvuru' kelimesinin yakininda gecen, yolu olan (ana sayfa olmayan) kurum adresi; yoksa bos."""
    for u, konum in _urller(metin):
        dusuk = u.lower()
        if any(x in dusuk for x in ONERI_ATLA):
            continue
        yol = re.sub(r"^https://[^/]+", "", u).strip("/")
        if len(yol) < 3:
            continue
        onceki = ic.norm((metin or "")[max(0, konum - 260):konum])
        if "BASVUR" in onceki:
            return u
    return ""


EPOSTA_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def eposta_bul(metin):
    """'Basvuru' kelimesinin yakininda gecen e-posta adresi (e-postayla basvuru yapilan ilanlar icin); yoksa bos."""
    for m in EPOSTA_RE.finditer(metin or ""):
        if "BASVUR" in ic.norm((metin or "")[max(0, m.start() - 400):m.start()]):
            return m.group(0).strip(".,;:").lower()
    return ""


def ana_sayfa_bul(metin):
    """'Basvuru' kelimesinin yakininda gecen kurum ana sayfasi (yolu olmayan adres); yoksa bos."""
    for u, konum in _urller(metin):
        if any(x in u.lower() for x in ONERI_ATLA):
            continue
        if "BASVUR" in ic.norm((metin or "")[max(0, konum - 260):konum]):
            return u
    return ""


def _kurum_anahtar(s):
    t = ic.norm(s or "")
    for w in ("REKTORLUGU", "BASKANLIGI", "MUDURLUGU", "GENEL", "T.C.", "TC"):
        t = t.replace(w, " ")
    return " ".join(t.split())


def _kelimeler(s):
    return {w for w in re.findall(r"[A-Z0-9]{3,}", ic.norm(s or "")) if w not in {"ILANI", "ILAN", "ALIM", "ALIMI", "PERSONEL"}}


def basvuru_coz(mevcut):
    """Her ilan icin dogrudan basvuru adresini bulur: ilan metnindeki ozel adres > Kariyer Kapisi'ndaki eslesen ilan > genel Kariyer Kapisi adresi."""
    kk = [r for r in mevcut.values() if r.get("source_name") == "Kariyer Kapısı"]
    n = 0
    for r in mevcut.values():
        if r.get("basvuru_tur") in ("diger", "genel", "ana", "eposta"):   # belirsiz olanlar her seferinde yeniden denenir
            r.pop("basvuru_link", None); r.pop("basvuru_tur", None)
    for r in mevcut.values():
        if r.get("source_name") == "Kariyer Kapısı" or r.get("basvuru_link"):
            continue
        adresler = list(r.get("basvuru_adresleri") or []) or adresleri_bul(r.get("description", ""))
        metin = ic.norm(r.get("description", ""))
        ozel = [u for u in adresler if "kariyerkapisi.gov.tr" in u.lower() and len(u.split("kariyerkapisi.gov.tr", 1)[1].strip("/")) > 8]
        genel_kk = [u for u in adresler if "kariyerkapisi.gov.tr" in u.lower()] or (["https://kariyerkapisi.gov.tr/isealim"] if "KARIYER KAPISI" in metin else [])
        link, tur = "", ""
        oneri = r.get("basvuru_oneri") or oneri_bul(r.get("description", ""))
        eposta = r.get("basvuru_eposta") or eposta_bul(r.get("description", ""))
        if ozel:
            link, tur = ozel[0], "ozel"
        elif oneri:
            link, tur = oneri, "ozel"
        elif genel_kk:
            # Kariyer Kapisi'ndaki ayni ilani bulmaya calis (kurum + baslik benzerligi + tarih yakinligi)
            ka = _kurum_anahtar(r.get("institution"))
            kelime = _kelimeler(r.get("title"))
            adaylar = []
            for k in kk:
                kka = _kurum_anahtar(k.get("institution"))
                if not ka or not kka or not (ka in kka or kka in ka):
                    continue
                kk_kel = _kelimeler(k.get("title"))
                if kelime and kk_kel and len(kelime & kk_kel) / max(1, min(len(kelime), len(kk_kel))) < 0.5:
                    continue
                adaylar.append(k)
            bas = (r.get("application_start") or "")[:10]
            if bas and len(adaylar) > 1:
                yakin = [k for k in adaylar if abs((date.fromisoformat((k.get("application_start") or bas)[:10]) - date.fromisoformat(bas)).days) <= 4]
                adaylar = yakin or adaylar
            if len(adaylar) == 1:
                link, tur = adaylar[0]["link"], "ozel"
                if adaylar[0].get("logo") and not str(r.get("logo") or "").startswith("https://"):
                    r["logo"] = adaylar[0]["logo"]
            elif eposta:
                link, tur = "mailto:" + eposta, "eposta"
            else:
                link, tur = genel_kk[0], "genel"
                if n < 400:
                    print(f"[basvuru] KK'da eslesme yok/belirsiz ({len(adaylar)} aday): {r.get('institution')}")
        else:
            ana = ana_sayfa_bul(r.get("description", ""))
            if eposta:
                link, tur = "mailto:" + eposta, "eposta"
            elif ana:
                link, tur = ana, "ana"
        if link:
            r["basvuru_link"], r["basvuru_tur"] = link, tur
            n += 1
    return n


def tekillestir(ilanlar):
    """Ayni kurumun ayni basligini tek kartta birlestirir; tum kaynak baglantilarini korur."""
    import re as _re
    def anahtar(r):
        t = f"{r.get('institution', '')}|{r.get('title', '')}".lower()
        return _re.sub(r"[^0-9a-zçğıöşü]+", "", t)[:140]
    gruplar = {}
    for r in ilanlar:
        gruplar.setdefault(anahtar(r), []).append(r)
    sonuc = []
    for g in gruplar.values():
        g.sort(key=lambda r: ("#" in str(r.get("link", "")), str(r.get("checked_at") or "")))
        ana = dict(g[0])
        if len(g) > 1:
            ana["checked_at"] = min([str(x.get("checked_at") or "") for x in g if x.get("checked_at")] or [""]) or ana.get("checked_at")
        baglantilar, gorulen = [], set()
        for x in g:
            link = str(x.get("link") or "")
            kaynak = str(x.get("source_name") or "")
            anahtar_link = (kaynak, link)
            if not link or anahtar_link in gorulen:
                continue
            gorulen.add(anahtar_link)
            baglantilar.append({
                "source_name": kaynak,
                "link": link,
                "source_url": x.get("source_url") or link
            })
        ana["kaynak_baglantilari"] = baglantilar
        ana["diger_kaynaklar"] = sorted({x.get("source_name", "") for x in g[1:] if x.get("source_name")})
        sonuc.append(ana)
    return sonuc


_AY_NUM = {
    "OCAK": 1, "SUBAT": 2, "MART": 3, "NISAN": 4, "MAYIS": 5, "HAZIRAN": 6,
    "TEMMUZ": 7, "AGUSTOS": 8, "EYLUL": 9, "EKIM": 10, "KASIM": 11, "ARALIK": 12
}
# Sonuç/yerleştirme ve sınav sonrası duyuruları yeni personel alımı değildir.
# "Müfettiş yardımcılığı giriş sınavı ilanı" gibi ilk alım ilanları özellikle korunur.
_ILAN_DISI = re.compile(
    r"\bSONUC(?:LAR(?:I|INA|INDA|INDAN)?)?\b|\bYERLESTIRME\b|\bYERLESTIRILEN ADAY|\bYERLESEN ADAY|\bYEDEK SIRADAN\b|"
    r"\bHAK KAZANAN\b|\bKAZANANLARA ILISKIN\b|\bISTENILEN BELGELER\b|\bBASARILI OLANLAR\b|"
    r"\bSINAV GIRIS BELGESI\b|\bSINAV YERI\b|\bSINAV TAKVIMI\b|"
    r"\bSINAVINDA BASARILI OLANLAR\b|\bSINAVININ .* BASARILI OLANLAR\b|"
    r"\bERTELEME\b|\bTERCIH DUYURUSU\b|\bTABAN VE TAVAN PUAN\b|"
    r"\bTAVAN VE TABAN PUAN\b|\bATANMAYA HAK\b",
    re.I
)
_TURMOB_RE = re.compile(r"\bTURMOB(?:'?(?:DAN|UN|A|DA))?\b|YEMINLI MALI MUSAVIRLIK SINAV", re.I)


def ilan_disi_temizle(mevcut):
    """Sonuç duyurularını ve kamu alımı olmayan TÜRMOB sınavlarını çıkarır;
    eski gerçek alım ilanlarını silmek yerine arşive taşır."""
    bugun = date.today()
    silinecek = []
    arsivlenen = 0
    for k, r in mevcut.items():
        baslik = str(r.get("title") or "")
        kurum = str(r.get("institution") or "")
        kaynak = str(r.get("source_name") or "")
        duz = ic.norm(" ".join((baslik, kurum)))
        # TÜRMOB kamu kurumu/personel alımı kaynağı değildir; ilan.gov.tr'de
        # yayımlanmış olsa bile kamu personel ilan havuzuna alınmaz.
        if _TURMOB_RE.search(duz):
            silinecek.append(k)
            continue
        # Sonuç, yerleştirme, sınav sonucu ve aday belge duyuruları bütün
        # kaynaklarda elenir. Gerçek ilk alım ilanları (giriş sınavı ilanı) kalır.
        if _ILAN_DISI.search(duz):
            silinecek.append(k)
            continue
        # Ek kaynaklarda tarihi başlığın başında bulunan eski gerçek alımlar,
        # son tarihi okunamamış olsa bile açık ilan gibi gösterilmez; arşivlenir.
        if kaynak not in ("ilan.gov.tr", "Kariyer Kapısı"):
            m = re.match(r"\s*(\d{1,2})\s+([A-Z]+)\s+(\d{4})", duz)
            if m and m.group(2) in _AY_NUM:
                try:
                    yayin = date(int(m.group(3)), _AY_NUM[m.group(2)], int(m.group(1)))
                    son = str(r.get("deadline") or "")[:10]
                    son_gecmis = not son or son < bugun.isoformat()
                    if (bugun - yayin).days > 45 and son_gecmis and r.get("durum") != "arsiv":
                        r["durum"] = "arsiv"
                        r["arsiv_nedeni"] = "Eski tarihli ek kaynak duyurusu; güncel başvuru ilanı değil"
                        r.setdefault("archived_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
                        arsivlenen += 1
                except ValueError:
                    pass
    for k in silinecek:
        del mevcut[k]
    print(f"İlan dışı sonuç/TÜRMOB kaydı çıkarıldı: {len(silinecek)}; eski ilan arşivlendi: {arsivlenen}")
    return len(silinecek)

def main():
    mevcut, eski_kaynaklar, eski_guncelleme = {}, {}, None
    if os.path.exists(CIKTI):
        with open(CIKTI, encoding="utf-8") as f:
            eski = json.load(f)
        eski_kaynaklar = eski.get("kaynaklar") or {}
        eski_guncelleme = eski.get("guncelleme")
        for row in eski.get("ilanlar") or []:
            mevcut[row["link"]] = row

    def imza(ilanlar, kaynaklar):
        k = {ad: {x: y for x, y in d.items() if x != "son_basari"} for ad, d in kaynaklar.items()}
        return json.dumps([sorted(ilanlar, key=lambda r: r["id"]), k], ensure_ascii=False, sort_keys=True)

    onceki = imza(list(mevcut.values()), eski_kaynaklar)

    isler = [("ilan.gov.tr", ilan_gov_tr, {}), ("Kariyer Kapısı", kariyer_kapisi, {})]
    if os.path.exists(EK_KAYNAK_DOSYASI):
        with open(EK_KAYNAK_DOSYASI, encoding="utf-8") as f:
            for k in json.load(f):
                if k.get("aktif", True):
                    isler.append((k["ad"], ek_kaynak, {"kaynak": k}))

    session = requests.Session()
    durumlar = {}
    for ad, fn, ekstra in isler:
        print(f"--- {ad}")
        try:
            eklenen = fn(session, mevcut, **ekstra)
            durumlar[ad] = {"durum": "tamam", "yeni": eklenen,
                            "son_basari": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            if ekstra.get("kaynak", {}).get("deneme"):
                durumlar[ad]["not"] = "deneme kaynağı: ilanlar resmî sayfadan kontrol edilmeli"
            print(f"{ad}: tamam, {eklenen} yeni")
        except Exception as e:  # bir kaynak cokse digerleri calissin
            mesaj = f"{type(e).__name__}: {e}"[:160]
            print(f"! {ad} hata verdi: {mesaj}")
            onceki_d = eski_kaynaklar.get(ad) or {}
            if onceki_d.get("durum") in ("tamam", "eski"):   # daha once okunduysa eski ilanlar duruyor
                durumlar[ad] = {"durum": "eski", "mesaj": mesaj, "son_basari": onceki_d.get("son_basari") or eski_guncelleme}
            else:
                durumlar[ad] = {"durum": "hata", "mesaj": mesaj}

    pasif_kaynaklar = [k for k in (json.load(open(EK_KAYNAK_DOSYASI, encoding="utf-8")) if os.path.exists(EK_KAYNAK_DOSYASI) else [])
                       if not k.get("aktif", True)]
    # Pasif kaynak sadece yeni taramayi durdurur; daha once bulunan ilanlar korunur.
    for k in pasif_kaynaklar:
        durumlar.setdefault(k["ad"], {"durum": "pasif", "mesaj": "Kaynak taramasi ayarlardan kapali; eski ilanlar korunuyor."})
    print(f"Manuel ilan: {manuel_ilanlar(mevcut)}")
    print(f"Puani/tarihi yeni bulunan: {puanlari_yenile(mevcut)}")
    print(f"Basvuru adresi bulunan: {basvuru_coz(mevcut)}")
    logo_haritasi(mevcut)
    print(f"Ilan disi/eski duyuru temizlendi: {ilan_disi_temizle(mevcut)}")
    _t = {}
    for _r in mevcut.values():
        _k = _r.get("basvuru_tur") or ("yok" if _r.get("source_name") != "Kariyer Kapısı" else "kk")
        _t[_k] = _t.get(_k, 0) + 1
    print("Basvuru adresi durumu:", _t)

    bugun = date.today()
    for r in mevcut.values():
        son = str(r.get("deadline") or "")[:10]
        if son:
            if son < bugun.isoformat():
                r["durum"] = "arsiv"
                r["arsiv_nedeni"] = "Basvuru son tarihi gecti"
                r.setdefault("archived_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
            else:
                r["durum"] = "aktif"
                r.pop("arsiv_nedeni", None)
                r.pop("archived_at", None)
        else:
            # Son tarihi belirtilmeyen ilanlarin kapandigini varsayma; kaydi koru ve kontrol iste.
            r.setdefault("durum", "tarih_belirsiz")
            if r.get("durum") == "arsiv" and not r.get("arsiv_nedeni"):
                r["arsiv_nedeni"] = "Son tarih bilgisi bulunamadigi icin manuel kontrol gerekli"

    sayilar = {}
    for r in mevcut.values():
        sayilar[r.get("source_name", "?")] = sayilar.get(r.get("source_name", "?"), 0) + 1
    for ad, d in durumlar.items():
        d["sayi"] = sayilar.get(ad, 0)

    ilanlar = sorted(tekillestir(list(mevcut.values())), key=lambda r: r["id"])
    # ilanlardan yeni bolum adlarini otomatik ogren (kalici; ilanlar silinse de listede kalir)
    try:
        onceki_bolum = {}
        if os.path.exists(CIKTI):
            with open(CIKTI, encoding="utf-8") as f:
                onceki_bolum = json.load(f).get("bolumler", {}) or {}
        bolumler = ic.bolum_ogren(ilanlar, onceki_bolum)
    except Exception as e:
        print("bolum ogrenme atlandi:", e)
        bolumler = {}
    simdi = datetime.now(timezone.utc).isoformat(timespec="seconds")
    degisti = imza(ilanlar, durumlar) != onceki
    # "guncelleme": ilanlar son ne zaman degisti; "son_kontrol": toplayici en son ne zaman calisti
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump({"guncelleme": simdi if degisti else (eski_guncelleme or simdi), "son_kontrol": simdi,
                   "kaynaklar": durumlar, "bolumler": bolumler, "ilanlar": ilanlar}, f, ensure_ascii=False, indent=1)
    print(f"ilanlar.json yazildi: {len(ilanlar)} ilan ({'degisiklik var' if degisti else 'degisiklik yok'})")
    if all(d["durum"] in ("hata", "eski") for d in durumlar.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
