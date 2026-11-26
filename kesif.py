import requests
UA = {"user-agent": "Mozilla/5.0 (compatible; KamuRadar/1.0; kisisel kullanim)"}
for yol in ["assets/appconfig.json", "assets/appconfig.production.json", "assets/appconfig.prod.json", "appconfig.json", "assets/config.json"]:
    u = "https://www.ilan.gov.tr/" + yol
    try:
        r = requests.get(u, headers=UA, timeout=30)
        print(r.status_code, u, r.text[:500].replace("\n", " "))
    except Exception as e:
        print("hata", u, type(e).__name__)
