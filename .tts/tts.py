import os,json,base64,wave,urllib.request,urllib.error,time
L=["Kamu işi mi arıyorsun? Onlarca siteyi tek tek gezme.",
"KamuHavuzu, bakanlık, üniversite ve belediye ilanlarını tek havuzda topluyor. Ara, bul, başvur.",
"Yapay zekâ, ilanın şartlarını senin için okuyor: KPSS puanı, kontenjan, son başvuru tarihi. Hepsi tek ekranda.",
"Resmî kaynaklardan gelir, üyelik gerektirmez, tamamen ücretsizdir. Son günü yaklaşan ilanları da öne çıkarır.",
"Ana ekrana ekle, tek dokunuşla aç.",
"KamuHavuzu. Tüm kamu alımları tek havuzda. Site linki profilimizde."]
os.makedirs('out',exist_ok=True)
key=os.environ['GEMINI_API_KEY']
STIL="Sen 25 yaşında, enerjik, neşeli ve samimi bir İstanbullu genç kadınsın; sosyal medya için tanıtım videosu seslendiriyorsun. Gülümseyerek, canlı ve doğal bir tonla, hafif tempolu ve vurgulu oku. Robotik veya düz okuma yapma. Sadece şu metni oku: "
for voice in ['Leda']:
    for i,t in enumerate(L,1):
        for deneme in range(8):
            try:
                body=json.dumps({"contents":[{"parts":[{"text":STIL+t}]}],"generationConfig":{"responseModalities":["AUDIO"],"speechConfig":{"voiceConfig":{"prebuiltVoiceConfig":{"voiceName":voice}}}}}).encode()
                r=urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent",body,{"Content-Type":"application/json","x-goog-api-key":key})
                d=json.load(urllib.request.urlopen(r,timeout=120))
                pcm=base64.b64decode(d["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
                w=wave.open(f'out/{voice.lower()}_{i}.wav','wb');w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(pcm);w.close()
                print('ok',voice,i,flush=True);time.sleep(8);break
            except Exception as e:
                print('hata',voice,i,deneme,str(e)[:120],flush=True);time.sleep(25)
print(sorted(os.listdir('out')))
