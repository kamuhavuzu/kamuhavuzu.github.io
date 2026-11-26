import requests, re
UA = {"user-agent": "Mozilla/5.0 (compatible; KamuRadar/1.0; kisisel kullanim)"}
kok = "https://kariyerkapisi.gov.tr"
t = requests.get(kok + "/isealim", headers=UA, timeout=30).text
inline = re.findall(r"<script(?![^>]*src)[^>]*>(.*?)</script>", t, re.S)
print("INLINE sayisi", len(inline))
for i, b in enumerate(inline):
    for m in re.finditer(r"(ajax|url|Url|fetch|post\(|get\()", b):
        print("INLINE", i, repr(b[max(0, m.start()-80):m.end()+200])); break
srcs = re.findall(r'<script[^>]+src="([^"]+)"', t)
print("SRC", srcs)
for sc in srcs:
    if sc.startswith("http") and "kariyerkapisi" not in sc: continue
    u = sc if sc.startswith("http") else kok + sc
    js = requests.get(u, headers=UA, timeout=30).text
    for m in list(re.finditer(r"(?:url|Url)\s*[:=]\s*[\"'`]([^\"'`]+)[\"'`]", js))[:8]:
        print("JS", sc.split('/')[-1][:30], m.group(1))
print("SELECT/FORM", re.findall(r'(?:action|data-url|data-ajax)="([^"]+)"', t)[:20])
