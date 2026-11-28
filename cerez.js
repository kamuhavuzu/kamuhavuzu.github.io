/* KH-fb91ce4cf50a-2026 © KamuHavuzu. Tüm hakları saklıdır. */
/* KamuHavuzu çerez tercihi: reklam kişiselleştirme izni. Sunucuya hiçbir şey göndermez. */
(function(){
 var K='k_cerez',v=null;
 try{v=localStorage.getItem(K)}catch(e){}
 var base=document.currentScript?document.currentScript.src.replace(/cerez\.js.*$/,''):'';
 // Karar "red" ise (veya henüz verilmediyse) reklamlar kişiselleştirilmemiş istenir.
 if(v!=='kabul'){(window.adsbygoogle=window.adsbygoogle||[]).requestNonPersonalizedAds=1}
 function kaydet(x){try{localStorage.setItem(K,x)}catch(e){}}
 function kapat(){var b=document.getElementById('krCerez');if(b)b.remove()}
 function goster(){
  if(document.getElementById('krCerez'))return;
  var d=document.createElement('div');d.id='krCerez';d.setAttribute('role','dialog');d.setAttribute('aria-label','Çerez tercihi');
  d.style.cssText='position:fixed;left:12px;right:12px;bottom:12px;z-index:2147483000;background:#fff;color:#13233a;border:1px solid #cfd9e6;border-radius:14px;padding:14px 16px;box-shadow:0 10px 40px rgba(0,0,0,.3);font:14px/1.45 system-ui,Arial,sans-serif;max-width:560px;margin:0 auto';
  d.innerHTML='<b>Çerez tercihin</b><p style="margin:6px 0 10px">Sitede Google reklamları gösterilebilir. “Kabul et” dersen reklamlar ilgi alanlarına göre kişiselleştirilebilir. “Yalnızca gerekli” dersen kişiselleştirilmemiş reklam istenir. Ayrıntılar: <a href="'+base+'bilgi.html#cerez" style="color:#174d7a;font-weight:700">Çerez politikası</a>.</p><div style="display:flex;gap:8px;flex-wrap:wrap"><button type="button" id="krCerezK" style="flex:1;min-width:130px;background:#173e66;color:#fff;border:0;border-radius:9px;padding:10px;font-weight:700;cursor:pointer">Kabul et</button><button type="button" id="krCerezR" style="flex:1;min-width:130px;background:#eef2f7;color:#173e66;border:0;border-radius:9px;padding:10px;font-weight:700;cursor:pointer">Yalnızca gerekli</button></div>';
  document.body.appendChild(d);
  document.getElementById('krCerezK').onclick=function(){kaydet('kabul');kapat()};
  document.getElementById('krCerezR').onclick=function(){kaydet('red');kapat()};
 }
 window.krCerezAc=goster;
 function hazir(){
  if(v!=='kabul'&&v!=='red')setTimeout(goster,600);
  var a=document.getElementById('krCerezDegis');if(a)a.onclick=goster;
  var s=document.getElementById('krVeriSil');
  if(s)s.onclick=function(){
   if(!confirm('Bu cihazdaki tüm KamuHavuzu verileri (favoriler, KPSS bilgileri, tercihler) silinsin mi?'))return;
   try{localStorage.clear();sessionStorage.clear()}catch(e){}
   if(window.caches)caches.keys().then(function(k){k.forEach(function(x){caches.delete(x)})});
   var m=document.getElementById('krVeriSilSonuc');if(m)m.textContent='Bu cihazdaki veriler silindi.';
  };
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',hazir);else hazir();

 // Telif uyarısı: sayfa orijinal adresin dışında çalışıyorsa ziyaretçi bilgilendirilir.
 // Bu kontrol veri toplamaz, hiçbir yere bilgi göndermez.
 var OK=['kamuhavuzu.github.io','localhost','127.0.0.1'];
 if(location.protocol!=='file:'&&OK.indexOf(location.hostname)<0){
  document.addEventListener('DOMContentLoaded',function(){
   var b=document.createElement('div');
   b.style.cssText='position:sticky;top:0;z-index:2147483647;background:#b3261e;color:#fff;padding:12px 16px;font:700 15px/1.4 system-ui,Arial,sans-serif;text-align:center';
   b.innerHTML='⚠ Bu sayfa KamuHavuzu’nun izinsiz bir kopyası olabilir. Orijinal site: <a href="https://kamuhavuzu.github.io" style="color:#ffd23f">kamuhavuzu.github.io</a>';
   document.body.insertBefore(b,document.body.firstChild);
  });
 }
})();
