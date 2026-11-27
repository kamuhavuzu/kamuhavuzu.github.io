import asyncio,os,json,base64,wave,urllib.request
L=["Kamu işi mi arıyorsun? Onlarca siteyi tek tek gezme.",
"KamuHavuzu, bakanlık, üniversite ve belediye ilanlarını tek havuzda topluyor. Ara, bul, başvur.",
"Yapay zekâ, ilanın şartlarını senin için okuyor: KPSS puanı, kontenjan, son başvuru tarihi. Hepsi tek ekranda.",
"Resmî kaynaklardan gelir, üyelik gerektirmez, tamamen ücretsizdir. Son günü yaklaşan ilanları da öne çıkarır.",
"Ana ekrana ekle, tek dokunuşla aç.",
"KamuHavuzu. Tüm kamu alımları tek havuzda. Site linki profilimizde."]
os.makedirs('out',exist_ok=True)
async def edge():
    import edge_tts
    for v in ['tr-TR-EmelNeural','tr-TR-AhmetNeural']:
        for i,t in enumerate(L,1):
            await edge_tts.Communicate(t,v,rate='+6%').save(f'out/{v[6:11].lower()}_{i}.mp3')
asyncio.run(edge())
key=os.environ.get('GEMINI_API_KEY')
if key:
    for voice in ['Kore','Puck']:
        for i,t in enumerate(L,1):
            try:
                body=json.dumps({"contents":[{"parts":[{"text":"Samimi, enerjik, doğal bir Türkçe ile söyle: "+t}]}],"generationConfig":{"responseModalities":["AUDIO"],"speechConfig":{"voiceConfig":{"prebuiltVoiceConfig":{"voiceName":voice}}}}}).encode()
                r=urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent",body,{"Content-Type":"application/json","x-goog-api-key":key})
                d=json.load(urllib.request.urlopen(r,timeout=90))
                pcm=base64.b64decode(d["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
                w=wave.open(f'out/gem_{voice.lower()}_{i}.wav','wb');w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(pcm);w.close()
            except Exception as e:
                print('gemini hata',voice,i,str(e)[:200])
print(os.listdir('out'))
