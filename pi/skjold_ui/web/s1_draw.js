// AUTOGENERERT av pi/skjold_ui/extract.py fra designfilen s1/pultforsterker_revb_metall.js – ikke rediger.
// Pultforsterker v2 rev B — cutouts and screw points measured from v2_body_revb.stl / v2_lid_*_revb.stl / v2_frontplate_revb*.stl
// Body coords (mm): x right, y back (front face y=-80), z up (0 = bottom, 48 = top). Wall features: front/back in (x,z), sides in (y,z), bottom in (x,y).
// Shapes: {t:'c',x,y,d} circle · {t:'r',x,y,w,h,r} rounded rect · {t:'s',x,y,w,h} stadium (long axis = w)
const c=(x,y,d)=>({t:'c',x,y,d}), r=(x,y,w,h,rad=0)=>({t:'r',x,y,w,h,r:rad}), s=(x,y,w,h)=>({t:'s',x,y,w,h});
const HP_SIDE=(()=>{ try{ return localStorage.getItem('s1_hp_layout')==='side'; }catch(e){ return false; } })();
// Headphone layout: 'under' = jack under the power button; 'side' = jack left of the power button (power shifted 11 mm right, 3.75 mm clear of the display window)
const FRV=(()=>{ try{ let v=localStorage.getItem('s1_front')||'std'; if(v==='bart'){ v='bar'; localStorage.setItem('s1_front','bar'); } return v; }catch(e){ return 'std'; } })();
const BAR=FRV==='bar'||FRV==='bart'; // 2b: 4.58″ bar TFT 960×320, box 224 wide
const BT=FRV==='bart'; // 2b-A: bar TFT with touch glass 128.9 × 49.17 × 4 → box 226 × 180 × 56, front centre z 28.4
const DZ=BT?4.4:FRV==='bar'?0.6:0; // 2b: alt foran 0,6 mm opp → skjermvindu z 5,8–43,4 klar av panelleppene (z 6 / 43,5)
const B16=(()=>{ try{ return localStorage.getItem('s1_btn')==='16'; }catch(e){ return false; } })(); // 16 mm kildeknapper (hode Ø18,5) i stedet for 12 mm
const E=B16&&BAR?6.75:0; // 2b + 16 mm: kassen 13,5 mm bredere (6,75 per side) → lik luft på begge sider av volumknappen (3,25 mm)
const BZ=B16?[14,34]:[15.5,32.5], BL=B16?[45.4,2.5]:[41.6,6.4];
const PWR=BT?[-97,24+DZ]:BAR?[-91.5-E,24+DZ]:HP_SIDE?[-70,24]:[-76,24], HPJ=BT?[-97,8+DZ]:BAR?[-91.5-E,8]:HP_SIDE?[-84,24]:[-76,8];
const BX=BT?[54,69]:BAR?(B16?[49,70]:[51,68]):(B16?[14.5,35.5]:[25.5,41.5]), VX=BT?91:BAR?(B16?96:91):70; // 2b: 17 mm c/c both ways // 2b: 4 mm skjerm→knapper
const DXV=BT?-19.7:BAR?-18.35-E:-27; // 2b: skjerm 2 mm mot venstre + av/på 1,5 mm mot venstre → 2 mm luft bak frontplaten på begge sider, 5,35 mm synlig luft begge sider
const OX=BT?-18:BAR?-(17+E):0; // wider 2b box: board (+ Pi, back ports) pushed to the LEFT wall so the 4 USB-A on the board edge reach the left side (same 5.2 mm post-to-wall as in 190)
const SH=a=>a.map(f=>Object.assign({},f,{x:+(f.x+OX).toFixed(2)}));
const REVB={ ox:OX,
  hpSide:HP_SIDE&&!BAR, bar:BAR, touch:BT, b16:B16, bz:BZ, bl:BL, dz:DZ, zc:24+DZ, pwr:PWR, hpj:HPJ, bx:BX, vx:VX,
  W:BT?226:BAR?224+2*E:190, D:180, H:BT?56:49.6, R:6, dispX:DXV,   // rev F: original 190 mm width, 180 deep for the 180 × 120 board (M3 172 × 92), ~2.3 mm to each side wall
  front:[
    r(DXV,24+DZ,BAR?114:57,30,2),                    // display window
    c(PWR[0],PWR[1],16.4),                         // power (16 mm)
    c(BX[0],BZ[0]+DZ,B16?16.4:12.4), c(BX[1],BZ[0]+DZ,B16?16.4:12.4), c(BX[0],BZ[1]+DZ,B16?16.4:12.4), c(BX[1],BZ[1]+DZ,B16?16.4:12.4), // input buttons (12 mm) — x +3.5 (rev B kort: lodderørene klarer J9)
    c(VX,24+DZ,7.4),                           // volume encoder (knob Ø30)
    {...c(HPJ[0],HPJ[1],6.2),hp:true}, // PJ-392 (nickel): mounted in the metal wall only; plate has Ø10.4×2.4 nut pocket at the back + Ø6.4 front hole                           // 3.5 mm headphone jack (under power)
    ...(BT?[[-103,42+DZ],[103,8+DZ],[103,40+DZ],[61.5,4+DZ],[61.5,44+DZ]]:BAR?[[-102-E,42],[-101-E,8],[102+E,8],[102+E,40]]:[[-83,41],[83,10],[83,41],[12,8.5],[12,39.5]]).map(([x,z])=>({...c(x,z,2.6),screw:'front'})), // 2 extra in the middle stiffen the plate+panel sandwich // front plate screws (from inside)
  ],
  // sheet front panel: open behind the alu front plate (controls mount in the plate only). x,z polygon of the opening incl. bend relief x −80.5…16.5
  frontOpen:BT?{relief:[-88.5,48], lip:6, pts:[[-88.5,17.4],[-106,17.4],[-106,40.9],[-97,40.9],[-97,99],[97,99],[97,10.4],[48,10.4]]}:BAR?{relief:[-80.5,40], lip:6, pts:[[-81.5-E,13],[-103.5-E,13],[-103.5-E,36.5],[-96-E,36.5],[-96-E,99],[96+E,99],[96+E,6],[43-(B16?3:0),6]]}:{relief:[-80.5,16.5], lip:6, pts:[[-80.5,13],[-88,13],[-88,36.5],[-79,36.5],[-79,99],[79,99],[79,6],[16.5,6]]},
  back:SH([ // body coords (x as seen from the front). Rev B-kort: dype deler under kortnivå (z ≤ 27,5) eller utenfor flatkabelsonen x −72…−17
    r(68,13,19.4,13),                       // KCD1 rocker, under the board (body z 8.5–21.5, board underside 23.1)
    r(21.75,13,16.8,14.5,1), c(8,13,3.4), c(35.5,13,3.4), // RJ45 panel extension (flange 36.5 × 19 inside, M3 pitch 27.5), under the board
    c(49.5,13,11.4),                        // DC-099 24 V, under the board
    ...[[68,32.1],[49.5,32.1],[31,32.1],[12.5,32.1]].map(([x,z])=>c(x,z,9.5)), // binding posts in one row above the board: L+ L− R+ R− (L left seen from behind), next to J2/J3
    c(-52,14,6.4), c(-68,14,6.4),           // AUX 1, AUX 2 (PJ-392, 16 mm deep — fits behind the ribbon fold)
    ...[34.1,19.5,11].flatMap(z=>[r(-26,z,9.6,3.8), c(-35.5,z,2.7), c(-16.5,z,2.7)]), // USB-C ×3: PC 1 above the board, PC 2 + Pi under it
  ]),
  left:[39.05,16.85,-5.35,-27.55].map(y=>r(y,28.1,14.8,9)),          // 4× USB-A (UGREEN-switch uten kasse, kort 95 × 46, kontakter 8 mm fra endene, senteravstand 22,2)
  right:Array.from({length:23},(_,i)=>r(-44+4*i,28.5,2.4,19)), // vent slots, pitch 4 (web 1.6 ≥ t), z 19–38 (clear of the rail, top z 18)
  bottom:SH([
    r(-75.8,-9.8,18,16),
    ...Array.from({length:26},(_,i)=>r(+(-62.5+5*i-OX).toFixed(1),-16,2.4,84)), // centred on the box (x=0): 13 each side // 26 vents 2,4 × 84 (y −58…26): ends 6 mm before the laser label (y 32…62), 5 mm behind the display-clamp slots; x −63,7…63,7 clear of the Ø12,7 feet (x ±80) and the cut-out at x −84,8…−66,8
  ]),
  topVents:[], // no top vents: air in through the bottom vent field, out through the right-side slots
  lidScrews:BT?[[-103,-80],[-103,80],[103,-80],[103,80]]:BAR?[[-102-E,-80],[-102-E,80],[102+E,-80],[102+E,80]]:[[-85,-80],[-85,80],[85,-80],[85,80]],      // M3, lid Ø3.4 / c'bore Ø6.2
  boardPosts:[[-88.3,-44.3],[-88.3,47.7],[83.7,-44.3],[83.7,47.7]].map(([x,y])=>[+(x+OX).toFixed(2),y]), boardZ:23.1, // M3, board seat height (rev G: 25 mm from the standoff top to the lid inside at 48.1, i.e. 23.4 mm above the 1.6 mm board)
  lidMountSlots:(BT?[[-135.5,-40],[-135.5,40],[135.5,-40],[135.5,40]]:BAR?[[-134.5-E,-40],[-134.5-E,40],[134.5+E,-40],[134.5+E,40]]:[[-117.5,-40],[-117.5,40],[117.5,-40],[117.5,40]]).map(([x,y])=>s(x,y,10,4.6)), // pultfeste lid, W=251
  lidMountW:BT?287:BAR?285+2*E:251,
  // printed front plate (replaces v2_frontplate_revb*.stl): 4 mm, no visible screws — M3 from inside the box into heat-set inserts
  plate:{w:BT?214:BAR?212+2*E:178,h:BT?54:47.6,r:3,t:4,insertD:4.0,insertDepth:3.2,
    coverT:2, cover:{oled:[62,34,2],tft:BAR?[118,42,2]:[60,40,2]}, view:{oled:[59.5,31.5,1.5],tft:BAR?[114,41,1.5]:[62,40,1.5]},
    // printed in: face-down, back 1.0 / cavity 2.2 / front lip 0.8 (z from the back). Pause at print-Z 3.0, insert acrylic, resume.
    layers:{back:1.0,cavity:2.2,front:0.8}, face:{oled:[57.6,30,1],tft:BAR?[111.1,37.6,2.2]:[50.5,37.4,2.2]}, cavClr:0.3, frame:2.0},
  oledZ:29.2, // TZT 2.42″: AA 57 × 29,5, 2,16 fra øvre modulkant / 11,34 fra nedre (FPC ned) → AA-senter 4,59 over modulsenter (cz 24,6)
  dispCut:{oled:[58,31,1.5],tft:BAR?[114,39,2]:[57,39,2]}, // universal: OLED active 55×27,5 and TFT active 48,6×37 both fit; leaves a web for the BSO standoffs
  oledMount:null, // replaced by a printed PETG holder (see oledHolder)
  oledHolder:{mod:[72,43,1.6], glass:[62.1,38.8,2.0], pitch:[68,39], hole:2.8, cz:24.6, studs:[[-83,41],[12,8.5],[12,39.5]], studType:'FH-M3-10'}, // 2.42" SSD1309 (TZT datasheet): module 72×43×5.9, holes Ø2.8 2 mm from edge // one universal cut-out: fits the 2.42" OLED and the 2.4" TFT,
  // printable desk-mount brackets (PETG, 4 mm): clamped between lid-screw heads and the standard lid — no special lid needed.
  // right-hand outline (CCW) with corner radii; left bracket = mirror. Slots for Ø4 wood screws into the desk underside.
  bracket:{t:4, pts:[[75.5,-86,4],[95,-86,2],[95,-52,3],[114.5,-52,5],[114.5,-28,5],[95,-28,3],[95,28,3],[114.5,28,5],[114.5,52,5],[95,52,3],[95,86,2],[75.5,86,4]].map(([x,y,r])=>[BT?x+18:BAR?x+17+E:x,y,r]),
    slots:[[BT?113:BAR?112+E:95,-40],[BT?113:BAR?112+E:95,40]].map(([x,y])=>s(x,y,12,4.6)), screwCb:[6.6,2.2]}, // box front wall display cut-out per module
};
if(typeof window!=='undefined') window.REVB=REVB;
{ REVB };

const cvs=document.createElement('canvas'); cvs.width=512; cvs.height=256;
const cvt=document.createElement('canvas'); cvt.width=640; cvt.height=480;
const cvb=document.createElement('canvas'); cvb.width=960; cvb.height=320;
const texO={needsUpdate:false},texT={needsUpdate:false},texB={needsUpdate:false};
let LEDK=1; const setLed=()=>{}; const bc=null;
const WL={air:{k:'AIR',st:'AirPlay · iPhone',t:'Midnight City',s:'M83'},bt:{k:'BT',st:'Blåtann · Sebastians iPhone',t:'Teardrop',s:'Massive Attack'}};
const TRACKS={air:[['Midnight City','M83',243],['Intro','The xx',128],['Breathe','Télépopmusik',279]],bt:[['Teardrop','Massive Attack',331],['Angel','Massive Attack',379],['Unfinished Sympathy','Massive Attack',308]]};
const NOWP=[['Nyheter','NRK Dagsnytt'],['Ekko','Et aktuelt samfunnsprogram'],['Dance The Way I Feel','Ofenbach'],['Flowers','Miley Cyrus'],['Mr. Brightside','The Killers'],['Clair de lune','Claude Debussy']];
const AUXSRC=[['AUX 1','3,5 mm · analog'],['AUX 2','3,5 mm · analog']];
const USBSRC=[['PC','USB-C «PC 1» · 48 kHz · 24 bit'],['Switch','USB-C «PC 2» · 48 kHz · 16 bit']];
const PRESETS=[['NRK P1','Distriktsprogram'],['NRK P2','Kultur og samfunn'],['NRK P3','Pop og humor'],['P4 Norge','Hits'],['Radio Norge','Pop og rock'],['NRK Klassisk','Klassisk musikk']];
const INPUTS=[{k:'AIR',n:'AirPlay · BT',t:'Midnight City',s:'M83 · iPhone'},{k:'AUX',n:'AUX',t:'Linje inn',s:'3,5 mm · analog'},{k:'RADIO',n:'Radio',t:'NRK P2',s:'Lyrion · internettradio'},{k:'USB',n:'USB-lyd',t:'PC 1',s:'48 kHz · 24 bit'}];
const NIGHT_STEPS_ON=['Lys av · hele huset','Ytterdører låst','Alarm satt til natt','Varme senket til 18 °C'], NIGHT_STEPS_OFF=['Lys på · kjøkken og gang','Alarm av','Varme tilbake til 21 °C'];
function nightMode(src,on,steps){ const local=!src; S.night=on===undefined?!S.night:!!on; S.nightSrc=src||'S1'; S.nightSteps=steps||(S.night?NIGHT_STEPS_ON:NIGHT_STEPS_OFF); S.nightT=performance.now();
  if(local&&bc){ bc.postMessage({type:'event',name:'power_double_press',action:'nattmodus',device:devName()}); bc.postMessage({type:'nightState',on:S.night,src:'S1'}); }
  animate(); refresh(); }
const S={rebootT:0,wl:'air',btPaired:true,pairT:0,pairTO:0,preset:1,usb:0,aux:0,menuT:-1e9,hpT:-1e9,setup:{on:false,step:-1,ssid:'',name:'',upd:0,connecting:false,testCh:'',testT:-1e9},set:{open:false,cat:-1,idx:0,t:0,edit:false,page:'',confirm:0,clockStyle:0,name:0,lvlAux:0,lvlUsb:0,led:0,voice:false,lang:0,vv:1,hold:2,bass:0,treb:0,bal:0,vstart:0,vmax:0,perIn:true,hpOwn:true,dim:1,off:1,clock:true,auto:1,wake:true},vols:[42,42,42,42],trk:{air:0,bt:0},playT:performance.now(),pausedAt:0,paused:false,actT:-1e9,actK:'',err:0,errT:-1e9,holdWhat:'',saveT:-1e9,btDev:['Sebastians iPhone','MacBook Pro'],sig:[true,false,true,true],hpVol:25,lastAct:performance.now(),knobHoldT:0,wlT:-1e9,muteT:-1e9,volT:-1e9,toastT:-1e9,hp:false,flip:false,ac:'royk',fm:'alu',fcol:'champagne',form:'rund',surf:'beadanod',col:'black',v:'plate',l:'fritt',f:'tft',open:false,ex:false,xray:false,main:true,power:true,input:0,vol:42,muted:false};
// ---------- display drawing ----------
const T0=performance.now();
// boot splash: Skjold logo, bars fade in one by one, then wordmark (2.6 s)
let bootT=performance.now(), bootRAF=0; const BOOT=2600;
function startBoot(){ bootT=performance.now(); if(S.set.vstart) S.vol=VST[S.set.vstart]; S.lastAct=bootT; cancelAnimationFrame(bootRAF); const tick=()=>{ drawOLED(); drawTFT(); if(performance.now()-bootT<BOOT+1300) bootRAF=requestAnimationFrame(tick); else if(S.welcome) animate(); }; tick(); }
const SPLASH_COL=['#ff6b4a','#ffa23a','#ffd23f','#3fd68a','#3fa9ff'];
function drawSplash(g,w,h,sc,col){ const t=(performance.now()-bootT)/BOOT, bars=[[0,22],[9,33],[18.7,42],[28.4,33],[36.4,22]];
  { g.font='600 13px Sora,-apple-system,"Helvetica Neue",Arial,sans-serif'; if('letterSpacing' in g) g.letterSpacing='2px'; const unit=41*0.62+6+g.measureText('SKJOLD').width;
    sc=Math.min(w*0.78/unit, h*0.5/(42*0.62)); }
  const k=sc*0.62, mw=41*k, F='600 '+(13*sc)+'px Sora,-apple-system,"Helvetica Neue",Arial,sans-serif'; g.font=F; if('letterSpacing' in g) g.letterSpacing=(2*sc)+'px';
  const tw=g.measureText('SKJOLD').width, gap=6*sc, x0=(w-(mw+gap+tw))/2, y0=h/2-21*k;
  if(col){ const ga=Math.max(0,Math.min(1,t*1.6)); const rg=g.createRadialGradient(x0+mw/2,h/2,2,x0+mw/2,h/2,w*0.55); rg.addColorStop(0,'rgba(255,170,70,'+(0.28*ga)+')'); rg.addColorStop(0.45,'rgba(80,120,255,'+(0.12*ga)+')'); rg.addColorStop(1,'rgba(0,0,0,0)'); g.fillStyle=rg; g.fillRect(0,0,w,h); }
  bars.forEach(([x,bh],i)=>{ const a=Math.max(0,Math.min(1,(t*5-i*0.45))); g.globalAlpha=a; if(col){ const bg=g.createLinearGradient(0,y0,0,y0+bh*k); bg.addColorStop(0,SPLASH_COL[i]); bg.addColorStop(1,SPLASH_COL[(i+1)%5]); g.fillStyle=bg; } else g.fillStyle='#f2f2ee'; g.beginPath(); g.roundRect(x0+x*k,y0,4.6*k,bh*k*a,2.3*k); g.fill(); });
  const ta=Math.max(0,Math.min(1,(t-0.45)*3)); g.globalAlpha=ta; g.fillStyle='#f2f2ee'; g.textBaseline='middle'; g.fillText('SKJOLD',x0+mw+gap,h/2-2*sc);
  g.font='400 '+(3.6*sc)+'px "IBM Plex Mono",Menlo,monospace'; if('letterSpacing' in g) g.letterSpacing=(1.1*sc)+'px'; g.fillStyle=col?'#ffb547':'#8b8b86'; g.fillText('STREAMING AMPLIFIER',x0+mw+gap+1,h/2+9*sc);
  g.globalAlpha=1; if('letterSpacing' in g) g.letterSpacing='0px'; g.textBaseline='alphabetic'; }
const booting=()=>performance.now()-bootT<BOOT;
const volShown=()=>{ const t=(performance.now()-bootT-BOOT)/1200; return Math.round(S.vol*Math.max(0,Math.min(1,t))); }; // soft start: output muted during boot, ramps over 1.2 s
let fxRAF=0; function animate(){ cancelAnimationFrame(fxRAF); const tick=()=>{ const busy=performance.now()-(S.nightT||-1e9)<4800||(S.welcome&&S.power)||performance.now()-(S.clockPrevT||-1e9)<4100||S.setup.on||S.set.open||S.knobHoldT||performance.now()-S.actT<900||performance.now()-S.saveT<1700||(S.err&&performance.now()-S.errT<2700)||performance.now()-S.volT<2400||(S.power&&!booting()&&!S.muted&&S.f==='oled')||S.rebootT||S.pairT||performance.now()-(S.pairCancelT||-1e9)<1600||performance.now()-S.menuT<2600||performance.now()-S.toastT<2200||performance.now()-S.hpT<1800||performance.now()-S.wlT<950||performance.now()-S.muteT<1600; drawOLED(); drawTFT();
  if(S.rebootT){ const on=Math.sin(performance.now()/220)>0; setLed(pwrBtn.userData.led,on,1,pwrBtn.userData.ledOff); }
  else { const nt=performance.now()-(S.nightT||-1e9); if(nt<900) setLed(pwrBtn.userData.led,Math.floor(nt/150)%2===0,1,pwrBtn.userData.ledOff); }
  if(S.pairT) setLed(inBtns[0].userData.led,Math.floor(performance.now()/350)%2===0,1,inBtns[0].userData.ledOff); if(busy) fxRAF=requestAnimationFrame(tick); else refresh(); }; tick(); }
function overlay(g){ const now=performance.now(), F='"Helvetica Neue",Arial,sans-serif', W='#f2f2ee', Dm='#8b8b86';
  if(S.rebootT){ const t=now-S.rebootT; g.fillStyle='#000'; g.fillRect(0,0,128,64);
    if(t<380){ const u=t/380, h=Math.max(0.6,26*(1-u*u)), w=124*(u<0.7?1:1-(u-0.7)/0.3); g.fillStyle=W; g.globalAlpha=0.9; g.fillRect(64-w/2,32-h/2,w,h); g.globalAlpha=1; return true; }
    if(t<3800){ const T=t-380, fade=Math.min(1,T/250,(3420-T)/300); g.globalAlpha=Math.max(0,fade);
      g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText('OMSTART',4,8); if('letterSpacing' in g) g.letterSpacing='0px'; g.fillStyle='#2a2a28'; g.fillRect(4,11,120,0.6);
      const ST=['Stopper lydtjenester','Starter Raspberry Pi','Kobler til Lyrion'], D=900, cur=Math.min(3,Math.floor(T/D));
      ST.forEach((l,i)=>{ const y=23+i*11, done=i<cur, act=i===cur;
        if(done){ g.strokeStyle=W; g.lineWidth=1.2; g.lineCap='round'; g.lineJoin='round'; g.beginPath(); g.moveTo(5,y-3); g.lineTo(7,y-1); g.lineTo(10.5,y-5.5); g.stroke(); }
        else if(act){ for(let k=0;k<8;k++){ const an=k/8*Math.PI*2+now/140; g.fillStyle='rgba(242,242,238,'+(0.2+0.8*((k/8+now/1120)%1)).toFixed(2)+')'; g.beginPath(); g.arc(7.7+Math.cos(an)*2.6,y-3.3+Math.sin(an)*2.6,0.55,0,Math.PI*2); g.fill(); } }
        else { g.fillStyle='#3a3a37'; g.beginPath(); g.arc(7.7,y-3.3,1,0,Math.PI*2); g.fill(); }
        g.fillStyle=done||act?W:'#55554f'; g.font=(act?'bold ':'')+'7px '+F; g.fillText(l,15,y); });
      const p=Math.min(1,T/(3*D)); g.fillStyle='#2a2a28'; g.fillRect(4,56,120,2); g.fillStyle=W; g.fillRect(4,56,120*(1-Math.pow(1-p,2)),2);
      g.globalAlpha=1; }
    else { S.rebootT=0; startBoot(); }
    return true; }
  if(now-(S.clockPrevT||-1e9)<4000&&window.SKJOLD){ g.fillStyle='#000'; g.fillRect(0,0,128,64); window.SKJOLD.drawClock(g,128,64,S.set.clockStyle||0,new Date()); return true; }
  if(S.setup.on&&S.power){ const U=S.setup; g.fillStyle='#000'; g.fillRect(0,0,128,64); const hdr=t=>{ g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText(t,4,8); if('letterSpacing' in g) g.letterSpacing='0px'; };
    if(U.step<0||U.step===0){ const join=U.step<0; drawQR(g,2,4,56,join?'WIFI:T:WPA;S:'+SETUP_SSID+';P:'+SETUP_PW+';;':'http://10.42.0.1/oppsett');
      g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText(join?'SETT OPP':'TELEFON KOBLET TIL',63,10); if('letterSpacing' in g) g.letterSpacing='0px';
      g.fillStyle=W; g.font='bold 8px '+F; g.fillText(join?'Skann for å':'Skann for å',63,22); g.fillText(join?'koble til':'åpne oppsett',63,31);
      g.fillStyle=Dm; g.font='5.5px '+F; if(join){ g.fillText(SETUP_SSID,63,43); g.fillText('Passord '+SETUP_PW,63,51); g.fillText('eller bruk Skjold-appen',63,59); } else { g.fillText('IP 10.42.0.1',63,43); g.fillText('10.42.0.1/oppsett',63,51); } return true; }
    if(U.step>=1&&U.step<=6){ hdr('OPPSETT'); g.textAlign='right'; g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText('STEG '+U.step+' AV 6',124,8); g.textAlign='left'; g.fillStyle='#2a2a28'; g.fillRect(4,11,120,0.6);
      for(let i=0;i<6;i++){ g.fillStyle=i<U.step?W:'#2a2a28'; g.fillRect(4+i*20.4,58,18.4,2); }
      if(U.step===4&&now-U.testT<1600){ const L=U.testCh==='L'; spk(g,L?22:106,32,1.6,false,Math.min(1,(now-U.testT)/500),W); g.textAlign='center'; g.fillStyle=W; g.font='bold 11px '+F; g.fillText(L?'VENSTRE':'HØYRE',64,36); g.fillStyle=Dm; g.font='6px '+F; g.fillText('Spiller testlyd',64,47); g.textAlign='left'; return true; }
      g.fillStyle=W; g.font='bold 12px '+F; g.fillText(STEPN[U.step-1],4,30); g.fillStyle=Dm; g.font='6px '+F;
      const sub=U.step===2?(U.connecting?'Kobler til '+U.ssid+'…':'Velg nett på telefonen'):U.step===3?'Velg navn på telefonen':U.step===4?'Trykk V og H på telefonen':U.step===5?'Velg Lyrion-server':U.step===6?(U.upd>=100?'Siste versjon installert':'Installerer 1.4.2 · ikke slå av'):'Velg språk på telefonen';
      g.fillText(sub,4,41); if(U.step===6){ g.fillStyle='#2a2a28'; g.fillRect(4,47,120,2); g.fillStyle=W; g.fillRect(4,47,120*U.upd/100,2); }
      if(U.step===2&&U.connecting){ for(let k=0;k<3;k++){ g.globalAlpha=0.3+0.7*((Math.floor(now/250)+k)%3===0?1:0); g.fillStyle=W; g.beginPath(); g.arc(112+k*5,28,1.5,0,Math.PI*2); g.fill(); } g.globalAlpha=1; } return true; }
    if(U.step>=7){ g.textAlign='center'; g.strokeStyle=W; g.lineWidth=1.4; g.lineCap='round'; g.lineJoin='round'; g.beginPath(); g.moveTo(56,14); g.lineTo(62,20); g.lineTo(73,8); g.stroke();
      g.fillStyle=W; g.font='bold 10px '+F; g.fillText((U.name||devName())+' er klar',64,34); g.fillStyle=Dm; g.font='6px '+F; g.fillText('IP 192.168.1.42',64,46); g.fillText('http://'+(U.name||'skjold').toLowerCase().replace(/[^a-z0-9]+/g,'-')+'.local',64,55); g.textAlign='left'; return true; } }
  if(S.set.open&&now-S.set.t>20000) S.set.open=false;
  if(S.set.open&&S.set.page){ g.fillStyle='#000'; g.fillRect(0,0,128,64); g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px';
    if(S.set.page==='reset'){ if('letterSpacing' in g) g.letterSpacing='0px'; g.textAlign='center'; g.fillStyle=W; g.font='bold 9px '+F; g.fillText('Tilbakestilt',64,30); g.fillStyle=Dm; g.font='6px '+F; g.fillText('Alle innstillinger er satt til standard',64,41); g.fillText('Trykk for å gå tilbake',64,56); g.textAlign='left'; return true; }
    if(S.set.page==='bt'){ g.fillText('PAREDE ENHETER',4,8); if('letterSpacing' in g) g.letterSpacing='0px'; g.fillStyle='#2a2a28'; g.fillRect(4,11,120,0.6);
      if(!S.btDev.length){ g.textAlign='center'; g.fillStyle=Dm; g.font='7px '+F; g.fillText('Ingen parede enheter',64,32); g.font='6px '+F; g.fillText('Trykk BT-knappen for å pare',64,42); g.textAlign='left'; }
      S.btDev.forEach((d,i)=>{ const y=23+i*12; icoBT(g,8,y-2.5,0.42,W); g.fillStyle=W; g.font='bold 7px '+F; g.fillText(d,15,y); g.fillStyle=Dm; g.font='6px '+F; g.textAlign='right'; g.fillText(S.wl==='bt'&&i===0&&S.input===0?'Tilkoblet':'Paret',124,y); g.textAlign='left'; });
      g.fillStyle=Dm; g.font='6px '+F; g.fillText('Trykk for å gå tilbake',4,60); return true; }
    g.fillText('OM '+devName().toUpperCase(),4,8); if('letterSpacing' in g) g.letterSpacing='0px'; g.fillStyle='#2a2a28'; g.fillRect(4,11,120,0.6);
    [['Navn',devName()],['Programvare',SWVER],['IP-adresse','192.168.1.42'],['Lyrion',S.err===1?'Frakoblet':'Tilkoblet'],['Wi-Fi',S.err===2?'Ingen':'Hjemme · −52 dBm'],['Serienr.','SKJ-S1-0001']].forEach(([k,v],i)=>{ const y=19+i*8.4; g.fillStyle=Dm; g.font='6px '+F; g.fillText(k,4,y); g.fillStyle=W; g.font='bold 6px '+F; g.textAlign='right'; g.fillText(v,124,y); g.textAlign='left'; });
    return true; }
  if(S.set.open){ g.fillStyle='#000'; g.fillRect(0,0,128,64); const L=curList(), top=S.set.cat<0;
    g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText(top?'INNSTILLINGER':CATS[S.set.cat][1].toUpperCase(),4,8); if('letterSpacing' in g) g.letterSpacing='0px';
    if(!top){ g.textAlign='right'; g.fillText(S.set.idx?S.set.idx+'/'+(L.length-1):'',124,8); g.textAlign='left'; } g.fillStyle='#2a2a28'; g.fillRect(4,11,120,0.6);
    const vis=4, first=Math.max(0,Math.min(L.length-vis,S.set.idx-1));
    for(let r=0;r<vis;r++){ const i=first+r, it=L[i]; if(!it) break; const y=14+r*12.5, on=i===S.set.idx, ed=on&&S.set.edit;
      if(on&&!ed){ g.fillStyle=W; g.beginPath(); g.roundRect(2,y,118,11.5,2); g.fill(); g.fillStyle='#000'; } else if(ed){ g.strokeStyle=W; g.lineWidth=0.8; g.beginPath(); g.roundRect(2.4,y+0.4,117.2,10.7,2); g.stroke(); g.fillStyle=W; } else g.fillStyle=(it.back||it.n==='Lukk')?Dm:W;
      g.font=(on?'bold ':'')+'7px '+F; g.fillText(it.n,6,y+8.3); g.textAlign='right'; g.font=(it.cat?'':'bold ')+'7px '+F;
      const v=it.cat||it.back||it.n==='Lukk'?(it.v||''):setVal(it); g.fillText(ed?'‹ '+v+' ›':v,116,y+8.3); g.textAlign='left'; }
    if(L.length>vis){ const sh=50*vis/L.length; g.fillStyle='#2a2a28'; g.fillRect(123.5,14,1.5,50); g.fillStyle=W; g.fillRect(123.5,14+first*(50-sh)/(L.length-vis),1.5,sh); } return true; }
  if(S.knobHoldT&&now-S.knobHoldT>(S.holdWhat==='radio'?900:350)){ const HM=S.holdMs||3000, p=Math.min(1,(now-S.knobHoldT-350)/(HM-350)), K=S.holdWhat; g.fillStyle='#000'; g.fillRect(0,0,128,64);
    const cx=64, cy=26; g.strokeStyle='#2a2a28'; g.lineWidth=2; g.beginPath(); g.arc(cx,cy,11,0,Math.PI*2); g.stroke(); g.strokeStyle=W; g.lineCap='round'; g.beginPath(); g.arc(cx,cy,11,-Math.PI/2,-Math.PI/2+p*Math.PI*2); g.stroke();
    if(K==='power') pwrIcon(g,cx,cy,5,1.6,W); else if(K==='pair') btGlyph(g,cx,cy,0.15,1.4,W); else { g.save(); g.translate(cx,cy); g.rotate(p*Math.PI); g.fillStyle=W; for(let k=0;k<8;k++){ g.rotate(Math.PI/4); g.fillRect(-1.2,-6.2,2.4,2.6); } g.beginPath(); g.arc(0,0,4.6,0,Math.PI*2); g.fill(); g.fillStyle='#000'; g.beginPath(); g.arc(0,0,1.9,0,Math.PI*2); g.fill(); g.restore(); }
    const ht=holdText(now); g.textAlign='center'; g.fillStyle=W; g.font='bold 8px '+F; g.fillText(ht[0],64,50); g.fillStyle=Dm; g.font='6px '+F; g.fillText(ht[1],64,59); g.textAlign='left'; return true; }
  if(S.pairT){ const t=(now-S.pairT)/1000, found=t>=4; g.fillStyle='#000'; g.fillRect(0,0,128,64);
    g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText('BLÅTANN',4,8); if('letterSpacing' in g) g.letterSpacing='0px';
    if(!found){ const cx=22, cy=34; for(let i=0;i<3;i++){ const r=((t*1.2+i/3)%1)*20; g.strokeStyle='rgba(242,242,238,'+(1-r/20).toFixed(2)+')'; g.lineWidth=1; g.beginPath(); g.arc(cx,cy,r,0,Math.PI*2); g.stroke(); }
      const a=t*3.2; g.strokeStyle='rgba(242,242,238,.55)'; g.lineWidth=1.4; g.beginPath(); g.arc(cx,cy,16,a,a+0.9); g.stroke();
      btGlyph(g,cx,cy,4,1.6,W);
      g.fillStyle=W; g.font='bold 9px '+F; g.fillText('Søker'+'...'.slice(0,1+Math.floor(t*2)%3),44,28); g.fillStyle=Dm; g.font='6px '+F; g.fillText('Synlig som «'+devName()+'»',44,38); g.fillText('Trykk BT = avbryt',44,47); }
    else { const u=Math.min(1,(t-4)/0.45), e=1-Math.pow(1-u,3), px=104+24*(1-e);
      btGlyph(g,18,32,4,1.6,W);
      g.globalAlpha=e; g.strokeStyle=W; g.lineWidth=1.3; g.beginPath(); g.roundRect(px-5,22,10,18,2); g.stroke(); g.fillStyle=W; g.fillRect(px-1.5,37,3,1); g.globalAlpha=1;
      for(let i=0;i<7;i++){ const x=32+i*9.5, w=(Math.sin(t*9-i*0.9)+1)/2; g.fillStyle='rgba(242,242,238,'+(0.18+0.82*w*e).toFixed(2)+')'; g.beginPath(); g.arc(x,32,1.3,0,Math.PI*2); g.fill(); }
      g.textAlign='center'; g.fillStyle=W; g.font='bold 7px '+F; g.fillText((S.pairDev||'Sebastians iPhone'),64,50); g.fillStyle=Dm; g.font='6px '+F; g.fillText('Kobler til'+'...'.slice(0,1+Math.floor(t*3)%3),64,58); g.textAlign='left'; }
    g.fillStyle='#2a2a28'; g.fillRect(found?4:44,found?61:53,found?120:78,found?1.5:2.5); g.fillStyle=W; g.fillRect(found?4:44,found?61:53,(found?120:78)*Math.min(1,t/6),found?1.5:2.5); return true; }
  if(now-(S.pairCancelT||-1e9)<1500){ const t=(now-S.pairCancelT)/1000, sh=t<0.3?Math.sin(t*60)*2*(1-t/0.3):0; g.fillStyle='#000'; g.fillRect(0,0,128,64);
    g.globalAlpha=0.45; btGlyph(g,64+sh,24,5,1.8,W); g.globalAlpha=1; const u=Math.min(1,t/0.25); g.strokeStyle=W; g.lineWidth=1.8; g.lineCap='round'; g.beginPath(); g.moveTo(52+sh,12); g.lineTo(52+sh+24*u,12+24*u); g.stroke(); g.lineCap='butt';
    g.textAlign='center'; g.fillStyle=W; g.font='bold 9px '+F; g.fillText('Paring avbrutt',64,50); g.fillStyle=Dm; g.font='6px '+F; g.fillText('Trykk BT for å prøve igjen',64,59); g.textAlign='left'; return true; }
  if(S.power&&now-S.hpT<1800){ const u=Math.min(1,(now-S.hpT)/220), e=1-(1-u)*(1-u)*(1-u); g.fillStyle='#000'; g.fillRect(0,0,128,64); g.save(); g.translate(64,24); g.scale(0.8+0.2*e,0.8+0.2*e); g.globalAlpha=e;
    g.strokeStyle=W; g.fillStyle=W; g.lineWidth=2.4; g.lineCap='round'; g.beginPath(); g.arc(0,2,11,Math.PI*1.02,-Math.PI*0.02); g.stroke(); g.beginPath(); g.roundRect(-13.5,1,6,10,2); g.roundRect(7.5,1,6,10,2); g.fill();
    if(!S.hp){ g.strokeStyle='#000'; g.lineWidth=4.5; g.beginPath(); g.moveTo(-15,-11); g.lineTo(15,13); g.stroke(); g.strokeStyle=W; g.lineWidth=1.6; g.beginPath(); g.moveTo(-15,-11); g.lineTo(15,13); g.stroke(); }
    g.restore(); g.globalAlpha=1; g.textAlign='center'; g.fillStyle=W; g.font='bold 9px '+F; g.fillText(S.hp?'Hodetelefoner':'Høyttalere',64,49); g.fillStyle=Dm; g.font='6px '+F; g.fillText(S.hp?'Høyttalerutgang dempet':'Hodetelefoner frakoblet',64,58); g.textAlign='left'; return true; }
  if(S.power&&now-S.muteT<1600){ const t=now-S.muteT, u=Math.min(1,t/260), e=1-(1-u)*(1-u)*(1-u), fo=Math.min(1,(1600-t)/250); g.fillStyle='#000'; g.fillRect(0,0,128,64); g.globalAlpha=fo;
    spk(g,60,25,1.9*(0.85+0.15*e),S.muted,Math.min(1,t/420),W);
    g.textAlign='center'; g.fillStyle=W; g.font='bold 9px '+F; g.fillText(S.muted?'Lyd av':'Lyd på',64,50); g.fillStyle=Dm; g.font='6px '+F; g.fillText(S.muted?'Trykk volumknappen for å slå på':'Volum '+S.vol,64,59); g.textAlign='left'; g.globalAlpha=1; return true; }
  if(S.power&&S.input===0&&now-S.wlT<950){ const t=now-S.wlT, u=Math.min(1,t/230), e=u<0.5?4*u*u*u:1-Math.pow(-2*u+2,3)/2, fo=Math.min(1,(950-t)/180), bt=S.wl==='bt';
    g.fillStyle='#000'; g.fillRect(0,0,128,64); g.globalAlpha=fo;
    const pos=v=>64+v*34, A=bt?-e:1-e, Bp=bt?1-e:-e;
    const dA=1-Math.min(1,Math.abs(A)), dB=1-Math.min(1,Math.abs(Bp));
    g.globalAlpha=fo*(0.25+0.75*dA); icoAir(g,pos(A),25,1+0.5*dA,dA>0.5?W:Dm);
    g.globalAlpha=fo*(0.25+0.75*dB); icoBT(g,pos(Bp),25,0.9+0.5*dB,dB>0.5?W:Dm);
    g.globalAlpha=fo*Math.min(1,Math.max(0,(t-120)/120)); g.textAlign='center'; g.fillStyle=W; g.font='bold 9px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText(bt?'BLÅTANN':'AIRPLAY',64,50); if('letterSpacing' in g) g.letterSpacing='0px';
    g.fillStyle=Dm; g.font='6px '+F; g.fillText(bt?'Sebastians iPhone':'iPhone · via Wi-Fi',64,59); g.textAlign='left'; g.globalAlpha=1; return true; }
  if(S.power&&S.err&&now-S.errT<2600){ const [h,sub]=ERRS[S.err]; g.fillStyle='#000'; g.fillRect(0,0,128,64); g.strokeStyle=W; g.lineWidth=1.4; g.lineJoin='round'; g.beginPath(); g.moveTo(64,9); g.lineTo(75,28); g.lineTo(53,28); g.closePath(); g.stroke(); g.fillStyle=W; g.fillRect(63.3,15,1.4,7); g.fillRect(63.3,23.6,1.4,1.6);
    g.textAlign='center'; g.font='bold 9px '+F; g.fillText(h,64,43); g.fillStyle=Dm; g.font='6px '+F; g.fillText(sub,64,53); g.textAlign='left'; return true; }
  if(S.power&&now-S.actT<800){ const u=Math.min(1,(now-S.actT)/160), fo=Math.min(1,(800-(now-S.actT))/160); g.fillStyle='#000'; g.fillRect(0,0,128,64); g.globalAlpha=fo; g.fillStyle=W; g.save(); g.translate(64,26); g.scale(0.8+0.2*u,0.8+0.2*u);
    if(S.actK==='next'){ [[-9,0],[0,0]].forEach(([x])=>{ g.beginPath(); g.moveTo(x-1,-7); g.lineTo(x+8,0); g.lineTo(x-1,7); g.closePath(); g.fill(); }); g.fillRect(8,-7,2.4,14); } else if(S.actK==='pause'){ g.fillRect(-6,-8,4,16); g.fillRect(2,-8,4,16); } else { g.beginPath(); g.moveTo(-5,-8); g.lineTo(8,0); g.lineTo(-5,8); g.closePath(); g.fill(); }
    g.restore(); g.textAlign='center'; g.font='bold 8px '+F; g.fillText(S.actK==='next'?'Neste':S.actK==='pause'?'Pause':'Spiller',64,50); g.textAlign='left'; g.globalAlpha=1; return true; }
  if(S.power&&now-S.saveT<1600){ g.fillStyle='#000'; g.fillRect(0,0,128,64); g.strokeStyle=W; g.lineWidth=1.4; g.lineCap='round'; g.lineJoin='round'; g.beginPath(); g.moveTo(56,24); g.lineTo(62,30); g.lineTo(73,18); g.stroke();
    g.textAlign='center'; g.fillStyle=W; g.font='bold 8px '+F; g.fillText('Lagret på radioknappen',64,45); g.fillStyle=Dm; g.font='6px '+F; g.fillText('Hold for å spille '+PRESETS[S.set.hold][0],64,55); g.textAlign='left'; return true; }
  if(now-S.toastT<2200){ const t=(now-S.toastT)/1000; g.fillStyle='#000'; g.fillRect(0,0,128,64);
    const c=Math.min(1,t/0.35), k=Math.max(0,Math.min(1,(t-0.3)/0.3)), b=Math.max(0,Math.min(1,(t-0.3)/0.6));
    if(b>0&&b<1){ g.strokeStyle='rgba(242,242,238,'+(1-b).toFixed(2)+')'; g.lineWidth=1; g.beginPath(); g.arc(64,24,11+11*b,0,Math.PI*2); g.stroke(); }
    g.strokeStyle=W; g.lineWidth=1.6; g.beginPath(); g.arc(64,24,11,-Math.PI/2,-Math.PI/2+Math.PI*2*c); g.stroke();
    if(k>0){ g.lineCap='round'; g.lineJoin='round'; g.beginPath(); const p=[[58.5,24.5],[62.5,28.5],[70,20]]; g.moveTo(...p[0]); if(k<0.4){ const q=k/0.4; g.lineTo(p[0][0]+(p[1][0]-p[0][0])*q,p[0][1]+(p[1][1]-p[0][1])*q); } else { const q=(k-0.4)/0.6; g.lineTo(...p[1]); g.lineTo(p[1][0]+(p[2][0]-p[1][0])*q,p[1][1]+(p[2][1]-p[1][1])*q); } g.stroke(); g.lineCap='butt'; }
    const tu=Math.min(1,Math.max(0,(t-0.45)/0.3)); g.globalAlpha=tu; g.textAlign='center'; g.fillStyle=W; g.font='bold 9px '+F; g.fillText('Tilkoblet',64,48+3*(1-tu)); g.fillStyle=Dm; g.font='6px '+F; g.fillText(S.btDev[0]||'Sebastians iPhone',64,58+3*(1-tu)); g.textAlign='left'; g.globalAlpha=1; return true; }
  if((S.input===3||S.input===1)&&now-S.menuT<2600){ const SRC=S.input===3?USBSRC:AUXSRC, cur=S.input===3?S.usb:S.aux; g.fillStyle='#000'; g.fillRect(0,0,128,64);
    g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText(S.input===3?'USB-LYD':'AUX',4,8); g.textAlign='right'; g.fillText('KILDE',124,8); g.textAlign='left'; if('letterSpacing' in g) g.letterSpacing='0px'; g.fillStyle='#2a2a28'; g.fillRect(4,11,120,0.6);
    const u=Math.min(1,(now-S.menuT)/200), e=1-(1-u)*(1-u)*(1-u);
    SRC.forEach(([n,d],i)=>{ const y=14+i*18, on=i===cur; if(on){ g.globalAlpha=e; g.fillStyle=W; g.beginPath(); g.roundRect(2,y,124,16,2); g.fill(); g.globalAlpha=1; g.fillStyle='#000'; } else g.fillStyle=Dm;
      g.beginPath(); g.arc(9,y+8,2.4,0,Math.PI*2); on?g.fill():(g.lineWidth=0.8,g.strokeStyle=Dm,g.stroke());
      g.font=(on?'bold ':'')+'9px '+F; g.fillText(n,17,y+11); g.font='6px '+F; g.textAlign='right'; g.fillText(d.split(' · ')[0],122,y+11); g.textAlign='left'; });
    volBar(g,F,W,Dm); return true; }
  if(S.input===2&&now-S.menuT<2600){ g.fillStyle='#000'; g.fillRect(0,0,128,64);
    g.fillStyle=Dm; g.font='bold 6px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText('RADIO',4,8); if('letterSpacing' in g) g.letterSpacing='0px';
    g.textAlign='right'; g.fillText('FAVORITT '+(S.preset+1)+' AV 6',118,8); g.textAlign='left'; g.fillStyle='#2a2a28'; g.fillRect(4,11,114,0.6);
    const u=Math.min(1,(now-S.menuT)/220), off=(1-(1-u)*(1-u)*(1-u))*0+(1-u)*(1-u)*(1-u)*14;
    g.save(); g.beginPath(); g.rect(0,12,120,52); g.clip();
    [-1,1,2].forEach(i=>{ const p=S.preset+i; if(p<0||p>5) return; const y=(i<0?22:i===1?54:68)+off; g.fillStyle=Dm; g.font='7px '+F; g.fillText(String(p+1),6,y); g.fillText(PRESETS[p][0],16,y); });
    const y0=27+off; g.fillStyle=W; g.beginPath(); g.roundRect(2,y0,116,22,2); g.fill(); g.fillStyle='#000';
    g.font='bold 7px '+F; g.fillText(String(S.preset+1),6,y0+9); g.font='bold 10px '+F; g.fillText(PRESETS[S.preset][0],16,y0+10);
    g.font='6px '+F; g.fillText(PRESETS[S.preset][1],16,y0+18);
    g.restore();
    for(let i=0;i<6;i++){ g.fillStyle=i===S.preset?W:'#3a3a37'; g.fillRect(122,15+i*8,2.4,i===S.preset?6:3); }
    return true; }
  return false; }
function btGlyph(g,cx,cy,s,lw,col){ g.save(); g.strokeStyle=col; g.lineWidth=lw; g.lineJoin='round'; g.lineCap='round'; g.beginPath(); g.moveTo(cx-s,cy-s); g.lineTo(cx+s,cy+s); g.lineTo(cx,cy+2*s); g.lineTo(cx,cy-2*s); g.lineTo(cx+s,cy-s); g.lineTo(cx-s,cy+s); g.stroke(); g.restore(); }
function drawBarBT(g,F){ const now=performance.now(), W='#f6f3ee', Dm='rgba(246,243,238,.62)', BL='#3b82f6', X=652, TW=1212;
  const txt=(s,x,y,px,wt,c,al)=>{ g.font=(wt||'')+' '+px+'px '+F; g.fillStyle=c; g.textAlign=al||'left'; g.fillText(s,x,y); g.textAlign='left'; };
  const bg=g.createRadialGradient(320,320,0,320,320,900); bg.addColorStop(0,'rgba(59,130,246,.22)'); bg.addColorStop(1,'rgba(0,0,0,0)'); g.fillStyle=bg; g.fillRect(0,0,1920,640);
  const pill=(s)=>{ g.font='bold 30px '+F; const w=g.measureText(s).width; g.beginPath(); g.roundRect(X,66,w+48,52,26); g.fillStyle='rgba(59,130,246,.28)'; g.fill(); txt(s,X+24,103,30,'bold',W); };
  pill('BLUETOOTH');
  if(S.pairT){ const t=(now-S.pairT)/1000, found=t>=4, cx=320, cy=320;
    if(!found){ for(let i=0;i<4;i++){ const r=((t*0.8+i/4)%1)*290; g.strokeStyle='rgba(120,170,255,'+(0.9*(1-r/290)).toFixed(2)+')'; g.lineWidth=4; g.beginPath(); g.arc(cx,cy,r,0,Math.PI*2); g.stroke(); }
      const a=t*2.4; const sw=g.createConicGradient?g.createConicGradient(a,cx,cy):null; if(sw){ sw.addColorStop(0,'rgba(120,170,255,.35)'); sw.addColorStop(0.12,'rgba(120,170,255,0)'); sw.addColorStop(1,'rgba(120,170,255,0)'); g.fillStyle=sw; g.beginPath(); g.arc(cx,cy,270,0,Math.PI*2); g.fill(); }
      g.fillStyle=BL; g.beginPath(); g.arc(cx,cy,92+4*Math.sin(t*4),0,Math.PI*2); g.fill(); btGlyph(g,cx,cy,26,12,'#fff');
      txt('Søker etter enheter'+'...'.slice(0,1+Math.floor(t*2)%3),X-4,250,96,'bold',W);
      txt('Synlig som «'+devName()+'» · velg den i Bluetooth på telefonen',X,322,40,'',Dm);
      txt('Trykk BT igjen for å avbryte',X,430,30,'',Dm); }
    else { const u=Math.min(1,(t-4)/0.5), e=1-Math.pow(1-u,3), px=500+80*(1-e);
      g.fillStyle=BL; g.beginPath(); g.arc(150,cy,80,0,Math.PI*2); g.fill(); btGlyph(g,150,cy,22,10,'#fff');
      g.globalAlpha=e; g.strokeStyle=W; g.lineWidth=8; g.beginPath(); g.roundRect(px-46,cy-84,92,168,18); g.stroke(); g.fillStyle=W; g.beginPath(); g.roundRect(px-14,cy+62,28,6,3); g.fill(); g.globalAlpha=1;
      for(let i=0;i<7;i++){ const x=262+i*30, w=(Math.sin(t*8-i*0.9)+1)/2; g.fillStyle='rgba(160,195,255,'+(0.15+0.85*w*e).toFixed(2)+')'; g.beginPath(); g.arc(x,cy,8,0,Math.PI*2); g.fill(); }
      txt(S.pairDev||'Sebastians iPhone',X-4,250,96,'bold',W); txt('Kobler til'+'...'.slice(0,1+Math.floor(t*3)%3),X,322,40,'',Dm); }
    g.beginPath(); g.roundRect(X,520,TW,10,5); g.fillStyle='rgba(255,255,255,.16)'; g.fill(); g.beginPath(); g.roundRect(X,520,Math.max(10,TW*Math.min(1,t/6)),10,5); g.fillStyle=BL; g.fill();
    return; }
  if(now-S.toastT<2200){ const t=(now-S.toastT)/1000, cx=320, cy=320, c=Math.min(1,t/0.35), k=Math.max(0,Math.min(1,(t-0.3)/0.3)), b=Math.max(0,Math.min(1,(t-0.3)/0.7));
    if(b>0&&b<1){ g.strokeStyle='rgba(74,222,128,'+(1-b).toFixed(2)+')'; g.lineWidth=6; g.beginPath(); g.arc(cx,cy,150+130*b,0,Math.PI*2); g.stroke(); }
    g.fillStyle='rgba(34,197,94,'+(0.9*c).toFixed(2)+')'; g.beginPath(); g.arc(cx,cy,150*(0.8+0.2*c),0,Math.PI*2); g.fill();
    if(k>0){ g.strokeStyle='#fff'; g.lineWidth=22; g.lineCap='round'; g.lineJoin='round'; const p=[[cx-62,cy+4],[cx-18,cy+48],[cx+66,cy-46]]; g.beginPath(); g.moveTo(...p[0]); if(k<0.4){ const q=k/0.4; g.lineTo(p[0][0]+(p[1][0]-p[0][0])*q,p[0][1]+(p[1][1]-p[0][1])*q); } else { const q=(k-0.4)/0.6; g.lineTo(...p[1]); g.lineTo(p[1][0]+(p[2][0]-p[1][0])*q,p[1][1]+(p[2][1]-p[1][1])*q); } g.stroke(); g.lineCap='butt'; }
    const tu=Math.min(1,Math.max(0,(t-0.4)/0.35)); g.globalAlpha=tu; txt('Tilkoblet',X-4,250+20*(1-tu),104,'bold',W); txt((S.btDev[0]||'Sebastians iPhone')+' · klar til å spille',X,322+20*(1-tu),40,'',Dm); g.globalAlpha=1; return; }
  { const t=(now-S.pairCancelT)/1000, cx=320+(t<0.35?Math.sin(t*60)*14*(1-t/0.35):0), cy=320, u=Math.min(1,t/0.25);
    g.fillStyle='rgba(255,255,255,.10)'; g.beginPath(); g.arc(cx,cy,92,0,Math.PI*2); g.fill(); g.globalAlpha=0.5; btGlyph(g,cx,cy,26,12,W); g.globalAlpha=1;
    g.strokeStyle='#ef4444'; g.lineWidth=12; g.lineCap='round'; g.beginPath(); g.moveTo(cx-70,cy-70); g.lineTo(cx-70+140*u,cy-70+140*u); g.stroke(); g.lineCap='butt';
    txt('Paring avbrutt',X-4,250,96,'bold',W); txt('Trykk BT for å prøve igjen',X,322,40,'',Dm); } }
function pwrIcon(g,cx,cy,r,lw,col){ g.save(); g.strokeStyle=col; g.lineWidth=lw; g.lineCap='round'; g.beginPath(); g.arc(cx,cy,r,-Math.PI/2+0.75,-Math.PI/2-0.75+Math.PI*2); g.stroke(); g.beginPath(); g.moveTo(cx,cy-r*1.25); g.lineTo(cx,cy-r*0.15); g.stroke(); g.restore(); }
function holdText(now){ const K=S.holdWhat, sec=String((S.holdMs||3000)/1000).replace('.',','), early=now-S.knobHoldT<1000;
  if(K==='power') return ['Omstart', early?'Slipp = '+(S.power?'standby':'slå på'):'Hold i '+sec+' s for å starte Pi på nytt'];
  if(K==='pair') return ['Blåtann-paring', early?'Slipp = bytt AirPlay / Blåtann':'Hold i '+sec+' s for å starte paring'];
  if(K==='radio') return ['Lagre favoritt', early?'Slipp = spill favoritt':'Hold for å lagre kanalen'];
  return [S.set.open?'Lukk innstillinger':'Innstillinger', early?'Slipp = mute':'Hold i '+sec+' s']; }
function drawBarSys(g,F){ const now=performance.now(), W='#f6f3ee', Dm='rgba(246,243,238,.62)', X=652, TW=1212, cx=320, cy=320;
  const txt=(s,x,y,px,wt,c,al)=>{ g.font=(wt||'')+' '+px+'px '+F; g.fillStyle=c; g.textAlign=al||'left'; g.fillText(s,x,y); g.textAlign='left'; };
  const pill=(s,c)=>{ g.font='bold 30px '+F; const w=g.measureText(s).width; g.beginPath(); g.roundRect(X,66,w+48,52,26); g.fillStyle=c; g.fill(); txt(s,X+24,103,30,'bold',W); };
  const glow=(c)=>{ const bg=g.createRadialGradient(cx,cy,0,cx,cy,900); bg.addColorStop(0,c); bg.addColorStop(1,'rgba(0,0,0,0)'); g.fillStyle=bg; g.fillRect(0,0,1920,640); };
  if(S.rebootT){ const t=now-S.rebootT;
    if(t<380){ const u=t/380, h=Math.max(2,620*(1-u*u)), w=1900*(u<0.7?1:1-(u-0.7)/0.3); g.fillStyle=W; g.globalAlpha=0.9; g.fillRect(960-w/2,320-h/2,w,h); g.globalAlpha=1; return; }
    const T=t-380, fade=Math.max(0,Math.min(1,T/250,(3420-T)/300)), D=900, cur=Math.min(3,Math.floor(T/D)), ST=['Stopper lydtjenester','Starter Raspberry Pi','Kobler til Lyrion'];
    g.globalAlpha=fade; glow('rgba(245,158,11,.18)'); pill('OMSTART','rgba(245,158,11,.3)');
    g.strokeStyle='rgba(255,255,255,.12)'; g.lineWidth=14; g.beginPath(); g.arc(cx,cy,150,0,Math.PI*2); g.stroke();
    const a=now/260; g.strokeStyle='#f59e0b'; g.lineCap='round'; g.beginPath(); g.arc(cx,cy,150,a,a+1.6); g.stroke(); g.lineCap='butt';
    pwrIcon(g,cx,cy,58,16,W);
    txt('Starter på nytt',X-4,236,96,'bold',W);
    ST.forEach((l,i)=>{ const y=330+i*66, done=i<cur, act=i===cur;
      if(done){ g.strokeStyle='#4ade80'; g.lineWidth=7; g.lineCap='round'; g.lineJoin='round'; g.beginPath(); g.moveTo(X+2,y-14); g.lineTo(X+14,y-2); g.lineTo(X+34,y-28); g.stroke(); g.lineCap='butt'; }
      else if(act){ for(let k=0;k<10;k++){ const an=k/10*Math.PI*2+now/140; g.fillStyle='rgba(246,243,238,'+(0.2+0.8*((k/10+now/1400)%1)).toFixed(2)+')'; g.beginPath(); g.arc(X+18+Math.cos(an)*14,y-14+Math.sin(an)*14,3.4,0,Math.PI*2); g.fill(); } }
      else { g.fillStyle='rgba(255,255,255,.2)'; g.beginPath(); g.arc(X+18,y-14,6,0,Math.PI*2); g.fill(); }
      txt(l,X+60,y,40,act?'bold':'',done||act?W:'rgba(246,243,238,.35)'); });
    const p=Math.min(1,T/(3*D)); g.beginPath(); g.roundRect(X,560,TW,10,5); g.fillStyle='rgba(255,255,255,.16)'; g.fill(); g.beginPath(); g.roundRect(X,560,Math.max(10,TW*(1-Math.pow(1-p,2))),10,5); g.fillStyle='#f59e0b'; g.fill(); g.globalAlpha=1; return; }
  if(S.knobHoldT){ const HM=S.holdMs||3000, p=Math.max(0,Math.min(1,(now-S.knobHoldT-350)/(HM-350))), K=S.holdWhat, C=K==='power'?'#f59e0b':K==='radio'?'#e5483b':'#3b82f6';
    glow(K==='power'?'rgba(245,158,11,.16)':K==='radio'?'rgba(229,72,59,.16)':'rgba(59,130,246,.16)'); pill(K==='power'?'POWER':K==='radio'?'RADIO':K==='pair'?'BT · AIRPLAY':'VOLUMHJUL','rgba(255,255,255,.14)');
    g.strokeStyle='rgba(255,255,255,.12)'; g.lineWidth=16; g.beginPath(); g.arc(cx,cy,150,0,Math.PI*2); g.stroke(); g.strokeStyle=C; g.lineCap='round'; g.beginPath(); g.arc(cx,cy,150,-Math.PI/2,-Math.PI/2+Math.max(0.01,p)*Math.PI*2); g.stroke(); g.lineCap='butt';
    if(K==='power') pwrIcon(g,cx,cy,58,16,W); else if(K==='pair') btGlyph(g,cx,cy,1.6,14,W); else { g.save(); g.translate(cx,cy); g.rotate(p*Math.PI); g.fillStyle=W; for(let k=0;k<8;k++){ g.rotate(Math.PI/4); g.fillRect(-14,-74,28,30); } g.beginPath(); g.arc(0,0,54,0,Math.PI*2); g.fill(); g.fillStyle='#000'; g.beginPath(); g.arc(0,0,22,0,Math.PI*2); g.fill(); g.restore(); }
    const ht=holdText(now); txt(ht[0],X-4,250,104,'bold',W); txt(ht[1],X,322,40,'',Dm);
    txt(String(Math.max(0,Math.ceil((HM-(now-S.knobHoldT))/100)/10).toFixed(1)).replace('.',',')+' s',X+TW,250,64,'300',W,'right'); return; }
  { const t=now-S.muteT, u=Math.min(1,t/260), e=1-Math.pow(1-u,3), fo=Math.max(0,Math.min(1,(1600-t)/250)), M=S.muted;
    g.globalAlpha=fo; glow(M?'rgba(239,68,68,.2)':'rgba(255,255,255,.08)'); pill(M?'DEMPET':'LYD',M?'rgba(239,68,68,.35)':'rgba(255,255,255,.14)');
    const r=150*(0.85+0.15*e); g.fillStyle=M?'#ef4444':'rgba(255,255,255,.12)'; g.beginPath(); g.arc(cx,cy,r,0,Math.PI*2); g.fill();
    if(!M&&u<1){ g.strokeStyle='rgba(255,255,255,'+(1-u).toFixed(2)+')'; g.lineWidth=6; g.beginPath(); g.arc(cx,cy,150+90*u,0,Math.PI*2); g.stroke(); }
    spk(g,cx-8,cy,11*(0.85+0.15*e),M,Math.min(1,t/420),'#fff');
    txt(M?'Lyd av':'Lyd på',X-4,250,104,'bold',W); txt(M?'Trykk volumknappen for å slå på':(S.hp?'Hodetelefoner':'Høyttalere')+' · volum '+volShown(),X,322,40,'',Dm);
    const v=M?0:volShown(); g.beginPath(); g.roundRect(X,470,TW,14,7); g.fillStyle='rgba(255,255,255,.16)'; g.fill(); g.beginPath(); g.roundRect(X,470,Math.max(14,TW*(M?S.vol:v)/100),14,7); g.fillStyle=M?'rgba(255,255,255,.3)':W; g.fill();
    g.globalAlpha=1; } }
function holdReboot(){ if(!S.main) return; S.power=true; S.pairT=0; S.rebootT=performance.now(); press(pwrBtn); animate(); }
function prevTrack(){ if(!S.power) return; if(S.input===2){ S.preset=(S.preset+PRESETS.length-1)%PRESETS.length; S.menuT=-1e9; syncInputs(); return; } const el=(performance.now()-S.playT)/1000; if(el>3||!TRACKS[S.wl]){ S.playT=performance.now(); S.pausedAt=S.playT; } else { const L=TRACKS[S.wl].length; S.trk[S.wl]=(S.trk[S.wl]+L-1)%L; S.playT=performance.now(); S.pausedAt=S.playT; } syncInputs(); }
function holdPair(){ if(!S.power) return; S.input=0; S.wl='bt'; S.pairT=performance.now(); clearTimeout(S.pairTO); S.pairTO=setTimeout(()=>{ if(!S.pairT) return; S.pairT=0; S.btPaired=true; if(!S.btDev.includes('Sebastians iPhone')) S.btDev.unshift('Sebastians iPhone'); S.toastT=performance.now(); syncInputs(); animate(); },6000); syncInputs(); press(inBtns[0]); animate(); }
function syncInputs(){ Object.assign(INPUTS[0],WL[S.wl]); { const tr=TRACKS[S.wl][S.trk[S.wl]]; INPUTS[0].t=tr[0]; INPUTS[0].s=tr[1]; INPUTS[0].dur=tr[2]; } INPUTS[0].st=(S.wl==='air'?'AirPlay · iPhone':'Blåtann · Sebastians iPhone'); INPUTS[2].st=PRESETS[S.preset][0]+' · '+PRESETS[S.preset][1]; INPUTS[2].t=NOWP[S.preset][0]; INPUTS[2].s=NOWP[S.preset][1]; INPUTS[1].t=AUXSRC[S.aux][0]; INPUTS[1].s=AUXSRC[S.aux][1]; INPUTS[3].t=USBSRC[S.usb][0]; INPUTS[3].s=USBSRC[S.usb][1]; }
const LANGS=[['Norsk','nb-NO'],['English','en-GB'],['Svenska','sv-SE'],['Dansk','da-DK']], VV=['Lav','Middels','Høy'];
const SAY={air:['AirPlay','AirPlay','AirPlay','AirPlay'],bt:['Blåtann','Bluetooth','Blåtand','Bluetooth'],aux:['AUX','AUX','AUX','AUX'],radio:['Radio','Radio','Radio','Radio'],usb:['USB','USB','USB','USB']};
const SDEF={clockStyle:0,name:0,lvlAux:0,lvlUsb:0,led:0,voice:false,lang:0,vv:1,hold:2,bass:0,treb:0,bal:0,vstart:0,vmax:0,perIn:true,hpOwn:true,dim:1,off:1,clock:true,auto:1,wake:true};
let SWVER='1.4.2'; const NAMES=['Skjold S1','Stue','Kontor','Soverom'], ERRS=[null,['Lyrion ikke tilgjengelig','Prøver igjen om 10 s'],['Ingen Wi-Fi','Radio og AirPlay er utilgjengelig'],['Overoppheting','Volum redusert til 60']];
const devName=()=>NAMES[S.set.name];
const VMAX=[100,90,80,70], VST=[0,20,30,40], DIMMS=[0,30000,60000], OFFMS=[0,120000,300000], AUTOMS=[0,1.2e6,3.6e6];
const SETS=[{s:'LYD',n:'Bass',num:['bass',-6,6]},{s:'LYD',n:'Diskant',num:['treb',-6,6]},{s:'LYD',n:'Balanse',num:['bal',-5,5]},
 {s:'LYD',n:'Startvolum',o:['vstart',['Sist brukt','20','30','40']]},{s:'LYD',n:'Maksvolum',o:['vmax',['100','90','80','70']]},{s:'LYD',n:'Volum per inngang',b:'perIn'},{s:'LYD',n:'Eget volum hodetlf.',b:'hpOwn'},
 {s:'STEMME',n:'Talebeskjed ved bytte',b:'voice'},{s:'STEMME',n:'Språk',o:['lang',LANGS.map(l=>l[0])]},{s:'STEMME',n:'Stemmevolum',o:['vv',VV]},{s:'STEMME',n:'Test stemme',act:()=>announce(true),v:'▶'},
 {s:'SKJERM',n:'Dimme etter',o:['dim',['Av','30 s','1 min']]},{s:'SKJERM',n:'Slukk etter',o:['off',['Av','2 min','5 min']]},{s:'SKJERM',n:'Klokke i standby',b:'clock'},{s:'SKJERM',n:'Klokkestil',o:['clockStyle',window.SKJOLD&&window.SKJOLD.CLOCKS?window.SKJOLD.CLOCKS.slice():['Tynn','Stor','Analog','Ord','Linje','Dato','VU-metre','Radioskala','Glasspanel','Klokke og vær','Bare tid','Døgnstripe','Klokka i ord','Fotoramme','Nattlys','Analog og kalender']]},
 {s:'STRØM',n:'Auto-standby',o:['auto',['Av','20 min','60 min']]},{s:'STRØM',n:'Slå på ved signal',b:'wake'},
 {s:'LYD',n:'Nivå AUX',num:['lvlAux',-6,6]},{s:'LYD',n:'Nivå USB',num:['lvlUsb',-6,6]},
 {s:'SKJERM',n:'LED-ringer',o:['led',['Høy','Middels','Lav','Av']]},
 {s:'RADIO',n:'Hold radioknapp',o:['hold',PRESETS.map(p=>p[0])]},
 {s:'TILKOBLING',n:'Enhetsnavn',o:['name',NAMES]},{s:'TILKOBLING',n:'Parede enheter',act:()=>{S.set.page='bt';},v:()=>S.btDev.length+' ›'},{s:'TILKOBLING',n:'Glem alle enheter',act:()=>{ if(S.set.confirm){ S.btDev=[]; S.btPaired=false; if(S.wl==='bt'){ S.wl='air'; syncInputs(); } S.set.confirm=0; } else S.set.confirm=1; },v:()=>S.set.confirm?'Trykk igjen':''},
 {s:'SYSTEM',n:'Demo: feilmelding',o:['__err',['Ingen','Lyrion','Wi-Fi','Overoppheting']]},
 {s:'SYSTEM',n:'Kjør oppsett på nytt',act:()=>startSetup(),v:'›'},{s:'SYSTEM',n:'Om Skjold S1',act:()=>{S.set.page='om';},v:'›'},{s:'SYSTEM',n:'Fabrikkinnstillinger',act:()=>{ if(S.set.confirm){ Object.assign(S.set,SDEF); LEDK=1; S.set.confirm=0; S.set.page=''; setTimeout(startSetup,0); } else S.set.confirm=1; },v:()=>S.set.confirm?'Trykk igjen':'›'},
 {s:'SYSTEM',n:'Lukk',act:()=>toggleSettings(),v:''}];
SETS.splice(SETS.findIndex(x=>x.n==='Lukk'),1);
const CATS=[['LYD','Lyd'],['TILKOBLING','Tilkobling'],['RADIO','Radio'],['STEMME','Stemme'],['SKJERM','Skjerm og lys'],['STRØM','Strøm'],['SYSTEM','System']];
function curList(){ if(S.set.cat<0) return [...CATS.map((c,i)=>({n:c[1],v:'›',cat:true,act:()=>{ S.set.cat=i; S.set.idx=1; }})),{n:'Lukk',v:'',act:()=>toggleSettings()}];
  return [{n:'‹ Tilbake',v:'',back:true,act:()=>{ S.set.idx=S.set.cat; S.set.cat=-1; }},...SETS.filter(x=>x.s===CATS[S.set.cat][0])]; }
const fmtNum=(k,v)=>k==='bal'?(v===0?'Midt':(v<0?'V ':'H ')+Math.abs(v)):(v>0?'+':v<0?'−':'')+Math.abs(v)+' dB';
const setVal=it=>it.o&&it.o[0]==='__err'?it.o[1][S.err]:it.num?fmtNum(it.num[0],S.set[it.num[0]]):it.o?it.o[1][S.set[it.o[0]]]:it.b?(S.set[it.b]?'På':'Av'):(typeof it.v==='function'?it.v():it.v);
const maxVol=()=>S.err===3?Math.min(60,VMAX[S.set.vmax]):VMAX[S.set.vmax];
function say(t){ if(!('speechSynthesis' in window)) return; speechSynthesis.cancel(); const u=new SpeechSynthesisUtterance(t), L=LANGS[S.set.lang][1]; u.lang=L; const v=speechSynthesis.getVoices().find(x=>x.lang&&x.lang.replace('_','-').toLowerCase().startsWith(L.slice(0,2))); if(v) u.voice=v; u.volume=[0.35,0.7,1][S.set.vv]; u.rate=1.05; speechSynthesis.speak(u); }
function announce(force){ if(!force&&!S.set.voice) return; const l=S.set.lang; let t;
  if(S.input===0) t=SAY[S.wl][l]; else if(S.input===1) t='AUX '+(S.aux+1); else if(S.input===2) t=SAY.radio[l]+', '+PRESETS[S.preset][0]; else t='USB, '+USBSRC[S.usb][0]; say(t); }
const playPos=()=>{ const d=INPUTS[0].dur||240; return ((S.paused?S.pausedAt:performance.now())-S.playT)/1000%d; };
function togglePause(){ if(!S.power) return; if(S.paused){ S.playT+=performance.now()-S.pausedAt; S.paused=false; S.actK='play'; } else { S.pausedAt=performance.now(); S.paused=true; S.actK='pause'; } S.actT=performance.now(); refresh(); animate(); }
function nextTrack(){ if(!S.power) return; if(S.input===0){ S.trk[S.wl]=(S.trk[S.wl]+1)%TRACKS[S.wl].length; S.playT=performance.now(); S.pausedAt=S.playT; } else if(S.input===2){ S.preset=Math.min(5,S.preset+1); } else return; S.actK='next'; S.actT=performance.now(); syncInputs(); refresh(); animate(); }
function saveRadio(){ if(!S.power) return; S.input=2; S.set.hold=S.preset; S.saveT=performance.now(); syncInputs(); press(inBtns[2]); refresh(); animate(); }
function holdRadio(){ if(!S.power) return; S.input=2; S.preset=S.set.hold; S.menuT=performance.now(); syncInputs(); press(inBtns[2]); announce(); refresh(); animate(); }
function toggleSettings(){ if(!S.power) return; S.set.open=!S.set.open; S.set.idx=0; S.set.cat=-1; S.set.edit=false; S.set.page=''; S.set.confirm=0; S.set.t=performance.now(); S.menuT=-1e9; refresh(); animate(); }
function setAct(){ const it=curList()[S.set.idx]; S.set.t=performance.now();
  if(S.set.page){ S.set.page=''; } else if(it.num) S.set.edit=!S.set.edit; else if(it.o&&it.o[0]==='__err'){ S.err=(S.err+1)%4; S.errT=performance.now(); if(S.err===3&&S.vol>60) S.vol=60; } else if(it.o) S.set[it.o[0]]=(S.set[it.o[0]]+1)%it.o[1].length; else if(it.b) S.set[it.b]=!S.set[it.b]; else if(it.act) it.act();
  if(it.n!=='Fabrikkinnstillinger'&&it.n!=='Glem alle enheter') S.set.confirm=0; LEDK=[1,0.55,0.22,0][S.set.led]; if(S.vol>maxVol()) S.vol=maxVol(); refresh(); animate(); }
const menuOpen=()=>S.power&&(S.input>=1&&S.input<=3)&&performance.now()-S.menuT<(REVB.bar?5000:2600);
const volVis=()=>S.input<=1||performance.now()-S.volT<2200;
function spk(g,x,y,k,muted,p,col){ g.save(); g.translate(x,y); g.scale(k,k); g.fillStyle=col; g.strokeStyle=col; g.lineCap='round'; g.lineJoin='round';
  g.beginPath(); g.moveTo(-6,-2.5); g.lineTo(-3,-2.5); g.lineTo(1.5,-6.5); g.lineTo(1.5,6.5); g.lineTo(-3,2.5); g.lineTo(-6,2.5); g.closePath(); g.fill();
  g.lineWidth=1.3; if(muted){ const a=Math.min(1,p*2), b=Math.max(0,Math.min(1,p*2-1)); g.beginPath(); g.moveTo(4,-3); g.lineTo(4+6*a,-3+6*a); if(b>0){ g.moveTo(10,-3); g.lineTo(10-6*b,-3+6*b); } g.stroke(); }
  else [3.5,6.5,9.5].forEach((r,i)=>{ const q=Math.max(0,Math.min(1,p*3-i)); if(!q) return; g.globalAlpha=q; g.beginPath(); g.arc(1.5,0,r,-0.75*q,0.75*q); g.stroke(); }); g.restore(); }
function icoAir(g,x,y,k,col){ g.save(); g.translate(x,y); g.scale(k,k); g.strokeStyle=col; g.fillStyle=col; g.lineWidth=1.2; g.lineJoin='round'; g.lineCap='round';
  g.beginPath(); g.moveTo(-3,4); g.lineTo(-7,4); g.quadraticCurveTo(-8,4,-8,3); g.lineTo(-8,-6); g.quadraticCurveTo(-8,-7,-7,-7); g.lineTo(7,-7); g.quadraticCurveTo(8,-7,8,-6); g.lineTo(8,3); g.quadraticCurveTo(8,4,7,4); g.lineTo(3,4); g.stroke();
  g.beginPath(); g.moveTo(0,1); g.lineTo(5,8); g.lineTo(-5,8); g.closePath(); g.fill(); g.restore(); }
function icoBT(g,x,y,k,col){ g.save(); g.translate(x,y); g.scale(k,k); g.strokeStyle=col; g.lineWidth=1.3; g.lineJoin='round'; g.lineCap='round';
  g.beginPath(); g.moveTo(-4,-4); g.lineTo(4,4); g.lineTo(0,8); g.lineTo(0,-8); g.lineTo(4,-4); g.lineTo(-4,4); g.stroke(); g.restore(); }
let QRLIB=(window.qrcode||null);
const qrCache={}; function drawQR(g,x,y,size,text){ g.fillStyle='#f2f2ee'; g.fillRect(x,y,size,size); if(!QRLIB){ g.fillStyle='#000'; g.font='5px sans-serif'; g.textAlign='center'; g.fillText('QR',x+size/2,y+size/2+2); g.textAlign='left'; return; }
  let q=qrCache[text]; if(!q){ q=QRLIB(0,'M'); q.addData(text); q.make(); qrCache[text]=q; } const n=q.getModuleCount(), m=size/(n+2); g.fillStyle='#000'; for(let r=0;r<n;r++) for(let c=0;c<n;c++) if(q.isDark(r,c)) g.fillRect(x+(c+1)*m,y+(r+1)*m,m+0.02,m+0.02); }
const SETUP_SSID='Skjold-Oppsett-0001', SETUP_PW='k7m2q9xd', STEPN=['Språk','Wi-Fi','Navn og rom','Høyttalertest','Lyrion','Programvare'];
function startSetup(){ S.setup={on:true,step:-1,ssid:'',name:'',upd:0,connecting:false,testCh:'',testT:-1e9}; S.set.open=false; refresh(); animate(); }
function volBar(g,F,W,Dm){ if(!volVis()) return; if(S.muted) spk(g,7,55.5,0.6,true,1,W); else { g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText('VOL',2,58); } const on=S.muted?0:Math.round(volShown()/100*24);
  for(let i=0;i<24;i++){g.fillStyle=i<on?W:'#2a2a28'; g.fillRect(20+i*3.6,52,2.6,7);} g.fillStyle=W; g.font='bold 8px '+F; g.textAlign='right'; g.fillText(S.muted?'—':String(volShown()),126,59); g.textAlign='left'; }
function screenDim(){ const idle=performance.now()-S.lastAct, o=OFFMS[S.set.off], d=DIMMS[S.set.dim]; return o&&idle>o?1:d&&idle>d?0.7:0; }
if(!window.SKJOLD_WELCOME){ const sw=document.createElement('script'); sw.src='./skjold_welcome.js'; document.head.appendChild(sw); }
if(!window.SKJOLD){ const sc=document.createElement('script'); sc.src='./skjold_settings.js'; sc.onload=()=>{ drawOLED(); drawTFT(); }; document.head.appendChild(sc); }
function drawClock(g,w,h,k){ if(window.SKJOLD&&window.SKJOLD.drawClock){ window.SKJOLD.drawClock(g,w,h,S.set.clockStyle||0,new Date()); return; } const d=new Date(), t=String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0'), m=d.getMinutes(); g.fillStyle='#3a3a37'; g.font='300 '+(18*k)+'px "Helvetica Neue",Arial,sans-serif'; g.textAlign='center'; g.fillText(t,w/2+((m%5)-2)*2*k,h/2+6*k+((m%3)-1)*2*k); g.textAlign='left'; }
function drawOLED(){ drawOLED0(); const g=cvs.getContext('2d'); g.setTransform(4,0,0,4,0,0); if(!S.power){ if(S.main&&S.set.clock&&!S.rebootT){ drawClock(g,128,64,1); texO.needsUpdate=true; } return; } const a=screenDim(); if(a){ g.fillStyle='rgba(0,0,0,'+a+')'; g.fillRect(0,0,128,64); texO.needsUpdate=true; } }
function drawOLED0(){ const g=cvs.getContext('2d'); g.setTransform(4,0,0,4,0,0); g.fillStyle='#000'; g.fillRect(0,0,128,64);
  if(!S.power){ texO.needsUpdate=true; return; }
  if(booting()){ drawSplash(g,128,64,2); texO.needsUpdate=true; return; }
  if(S.welcome&&S.power&&!booting()&&window.SKJOLD_WELCOME){ window.SKJOLD_WELCOME.draw(g,128,64,performance.now()-bootT-BOOT,{mono:true,hint:'Trykk en knapp'}); texO.needsUpdate=true; return; }
  if(overlay(g)){ texO.needsUpdate=true; return; }
  const it=INPUTS[S.input], F='"Helvetica Neue",Arial,sans-serif', W='#f2f2ee', Dm='#8b8b86';
  g.fillStyle=W; g.font='bold 7px '+F; let x=2; INPUTS.forEach((t,i)=>{const w=g.measureText(t.k).width+6; if(i===S.input){g.fillRect(x,1,w,9); g.fillStyle='#000';} else g.fillStyle=Dm; g.fillText(t.k,x+3,8); g.fillStyle=W; x+=w+3;});
  if(S.err){ const ex=S.hp?(S.muted?96:106):(S.muted?110:120); g.fillStyle=W; g.beginPath(); g.moveTo(ex,1.5); g.lineTo(ex+4.5,9.5); g.lineTo(ex-4.5,9.5); g.closePath(); g.fill(); g.fillStyle='#000'; g.fillRect(ex-0.5,4,1,3); g.fillRect(ex-0.5,7.8,1,1); }
  if(S.muted) spk(g,S.hp?106:120,5.5,0.55,true,1,W);
  if(S.hp){ g.save(); g.strokeStyle=W; g.fillStyle=W; g.lineWidth=1.1; g.lineCap='round'; g.beginPath(); g.arc(121,6.2,4,Math.PI,0); g.stroke(); g.beginPath(); g.roundRect(116.2,5.6,2.4,3.6,0.8); g.roundRect(123.4,5.6,2.4,3.6,0.8); g.fill(); g.restore(); }
  const fit=(t,w)=>{ if(g.measureText(t).width<=w) return t; while(t.length>1&&g.measureText(t+'…').width>w) t=t.slice(0,-1); return t+'…'; };
  if(!volVis()&&S.input===2){ const tn=performance.now();
    g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText(fit(PRESETS[S.preset][0].toUpperCase()+' · '+PRESETS[S.preset][1].toUpperCase(),100),2,20);
    g.textAlign='right'; g.fillText((S.preset+1)+'/6',126,20); g.textAlign='left';
    g.fillStyle=W; g.font='bold 13px '+F; g.fillText(fit(it.t,124),2,36); g.fillStyle=Dm; g.font='8px '+F; g.fillText(fit(it.s,124),2,47);
    g.fillStyle='#2a2a28'; g.fillRect(2,52,124,0.6); g.fillStyle=Math.floor(tn/700)%2?W:'#e05a4a'; g.beginPath(); g.arc(4.5,59,1.8,0,Math.PI*2); g.fill();
    g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText(S.muted?'MUTE':'DIREKTE',9,61); g.textAlign='right'; g.fillText('LYRION · 320 KBPS',126,61); g.textAlign='left'; texO.needsUpdate=true; return; }
  if(!volVis()&&S.input===3){ const tn=performance.now()/1000;
    g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText('USB-LYD · '+(S.usb?'PC 2':'PC 1')+'-PORT',2,20);
    g.fillStyle=W; g.font='bold 16px '+F; g.fillText(it.t,2,38); g.fillStyle=Dm; g.font='7px '+F; g.textAlign='right'; g.fillText(S.usb?'48 kHz · 16 bit':'48 kHz · 24 bit',126,38); g.textAlign='left';
    ['L','R'].forEach((c,i)=>{ const y=47+i*8, v=S.muted?0:0.45+0.4*Math.abs(Math.sin(tn*2.3+i*0.9)*Math.sin(tn*0.9+i)), n=Math.round(v*30);
      g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText(c,2,y+5); for(let k=0;k<30;k++){ g.fillStyle=k<n?(k>25?'#e05a4a':W):'#2a2a28'; g.fillRect(10+k*3.9,y,2.9,5); } });
    texO.needsUpdate=true; return; }
  const sigI=S.input===1?S.aux:S.input===3?2+S.usb:-1;
  if(sigI>=0&&!S.sig[sigI]){ g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText((S.input===1?'AUX':'USB-LYD')+' · '+it.t.toUpperCase(),2,19);
    g.strokeStyle=Dm; g.lineWidth=1; g.beginPath(); g.moveTo(2,31); for(let x=0;x<=22;x++) g.lineTo(2+x,31); g.stroke(); g.fillStyle=W; g.font='bold 11px '+F; g.fillText('Ingen signal',28,35); g.fillStyle=Dm; g.font='6px '+F; g.fillText(S.input===1?'Sjekk kabelen til '+it.t:'Sjekk at '+it.t+' sender lyd',2,45); volBar(g,F,W,Dm); texO.needsUpdate=true; return; }
  if(it.st){ g.fillStyle=Dm; g.font='bold 6px '+F; g.fillText(fit(it.st.toUpperCase(),116),2,19); if(S.paused){ g.fillStyle=W; g.fillRect(119,14.5,2,5.5); g.fillRect(123,14.5,2,5.5); } else for(let i=0;i<3;i++){ const h=1.5+3.5*Math.abs(Math.sin(performance.now()/260+i*1.3)); g.fillStyle=S.muted?'#3a3a37':W; g.fillRect(118+i*3,20-h,2,h); }
    g.fillStyle=W; g.font='bold 11px '+F; g.fillText(fit(it.t,124),2,31);
    if(S.input===0){ const p=playPos(), d=it.dur, tm=x=>Math.floor(x/60)+':'+String(Math.floor(x%60)).padStart(2,'0'), ts=tm(p)+' / '+tm(d); g.font='6px '+F; const tw=g.measureText(ts).width; g.fillStyle=Dm; g.font='7px '+F; g.fillText(fit(it.s,120-tw),2,41); g.font='6px '+F; g.textAlign='right'; g.fillText(ts,126,41); g.textAlign='left'; g.fillStyle='#2a2a28'; g.fillRect(2,44.5,124,1); g.fillStyle=W; g.fillRect(2,44.5,124*p/d,1); }
    else { g.fillStyle=Dm; g.font='7px '+F; g.fillText(fit(it.s,124),2,41); } }
  else { g.fillStyle=W; g.font='bold 12px '+F; g.fillText(it.t,2,27); g.fillStyle=Dm; g.font='7px '+F; g.fillText(it.s,2,37); }
  volBar(g,F,W,Dm);
  texO.needsUpdate=true; }
function drawTFT(){ drawTFT1(); if(REVB.bar) drawBar(); }
// 2b bar screen 960×320 (drawn at 2× = 1920×640): button-driven, no touch. Menus/boot/off fall back to the 4:3 UI centred.
function barNow(){ const i=S.input, k=INPUTS[i];
  if(i===2){ const p=PRESETS[S.preset]; return {src:'RADIO',t:p[0],s:p[1],live:true}; }
  if(i===1){ const a=AUXSRC[S.aux]; return {src:'AUX',t:a[0],s:a[1],live:true}; }
  if(i===3){ const u=USBSRC[S.usb]; return {src:'USB',t:u[0],s:u[1],live:true}; }
  return {src:S.wl==='bt'?'BLUETOOTH':'AIRPLAY',t:k.t,s:k.s,live:false}; }
function bdayOn(){ if(S.bdayDemo) return true; try{ return localStorage.getItem('s1_bday_once')==='armed'; }catch(e){ return false; } }
const CONF=Array.from({length:90},(_,i)=>({x:Math.random()*1920,y:Math.random()*640,v:40+Math.random()*90,w:6+Math.random()*10,h:12+Math.random()*16,r:Math.random()*6,s:(Math.random()-.5)*4,c:['#ff5a7a','#ffc94a','#5ad1ff','#8a7dff','#5be3a0','#ffffff'][i%6]}));
function drawBday(g,F){ const t=performance.now()/1000; const bg=g.createLinearGradient(0,0,1920,640); bg.addColorStop(0,'#2a0b3d'); bg.addColorStop(0.55,'#5a1248'); bg.addColorStop(1,'#1d1240'); g.fillStyle=bg; g.fillRect(0,0,1920,640);
  CONF.forEach(p=>{ const y=(p.y+t*p.v)%700-30, x=p.x+Math.sin(t*1.3+p.r)*24; g.save(); g.translate(x,y); g.rotate(p.r+t*p.s); g.fillStyle=p.c; g.globalAlpha=.85; g.fillRect(-p.w/2,-p.h/2,p.w,p.h); g.restore(); });
  [[110,0.0,'#ff5a7a'],[250,1.7,'#ffc94a'],[1670,0.8,'#5ad1ff'],[1810,2.4,'#8a7dff']].forEach(([x,ph,c])=>{ const y=250+Math.sin(t*1.1+ph)*18; g.strokeStyle='rgba(255,255,255,.45)'; g.lineWidth=3; g.beginPath(); g.moveTo(x,y+92); g.quadraticCurveTo(x+20,y+190,x-6,y+300); g.stroke();
    const gr=g.createRadialGradient(x-22,y-30,8,x,y,96); gr.addColorStop(0,'#fff'); gr.addColorStop(0.18,c); gr.addColorStop(1,c); g.fillStyle=gr; g.beginPath(); g.ellipse(x,y,72,90,0,0,Math.PI*2); g.fill(); g.beginPath(); g.moveTo(x-10,y+98); g.lineTo(x+10,y+98); g.lineTo(x,y+86); g.fill(); });
  let name='Pappa'; try{ name=localStorage.getItem('s1_bday_name')||'Pappa'; }catch(e){}
  g.textAlign='center'; g.fillStyle='#ffc94a'; g.font='bold 40px '+F; g.fillText('HIPP HIPP HURRA',960,170);
  g.fillStyle='#fff'; let px=124; g.font='bold '+px+'px '+F; const l1='Gratulerer med dagen'+(name?',':'!'); while(g.measureText(l1).width>1000&&px>60){ px-=6; g.font='bold '+px+'px '+F; } g.fillText(l1,960,320);
  if(name){ let p2=150; g.font='bold '+p2+'px '+F; while(g.measureText(name+'!').width>1000&&p2>60){ p2-=6; g.font='bold '+p2+'px '+F; } const gw=g.createLinearGradient(560,0,1360,0); gw.addColorStop(0,'#ffc94a'); gw.addColorStop(0.5,'#ff7aa8'); gw.addColorStop(1,'#8fd8ff'); g.fillStyle=gw; g.fillText(name+'!',960,480); }
  g.fillStyle='rgba(255,255,255,.7)'; g.font='32px '+F; g.fillText('Trykk en knapp for å lukke',960,590); g.textAlign='left'; }
function drawBarSettings(g){ const F='"Helvetica Neue",Arial,sans-serif', W='#f6f3ee', Dm='rgba(246,243,238,.62)', Lo='rgba(246,243,238,.38)', A='#f59e0b', L=curList(), top=S.set.cat<0, idx=S.set.idx, it=L[idx]||L[0], ed=!!S.set.edit;
  const txt=(t,x,y,px,wt,c,al)=>{ g.font=(wt||'')+' '+px+'px '+F; g.fillStyle=c; g.textAlign=al||'left'; g.fillText(t,x,y); g.textAlign='left'; };
  const sp=(t,x,y,px,c,al)=>{ if('letterSpacing' in g) g.letterSpacing=(px*0.12)+'px'; txt(t,x,y,px,'',c,al); if('letterSpacing' in g) g.letterSpacing='0px'; };
  const CW=680, vis=5, first=Math.max(0,Math.min(L.length-vis,idx-2)); g.textBaseline='middle';
  for(let r=0;r<vis;r++){ const i=first+r, o=L[i]; if(!o) break; const y=60+r*104+44, on=i===idx, edge=(r===0&&first>0)||(r===vis-1&&first+vis<L.length);
    if(on&&!ed){ g.beginPath(); g.roundRect(48,y-46,CW-48+2,92,[24,0,0,24]); g.fillStyle=W; g.fill(); txt(o.n,88,y+2,56,'bold','#000'); }
    else if(on&&ed){ g.strokeStyle=A; g.lineWidth=4; g.beginPath(); g.moveTo(CW+2,y-44); g.lineTo(72,y-44); g.arcTo(50,y-44,50,y,22); g.arcTo(50,y+44,72,y+44,22); g.lineTo(CW+2,y+44); g.stroke(); txt(o.n,88,y+2,56,'bold',W); }
    else txt(o.n,88,y+2,48,'',edge||o.back||o.n==='Lukk'?Lo:Dm); }
  g.fillStyle='rgba(255,255,255,.1)'; g.fillRect(CW,52,2,536);
  if(L.length>vis){ const h=536*vis/L.length; g.fillStyle='rgba(255,255,255,.1)'; g.fillRect(20,52,4,536); g.fillStyle=Dm; g.fillRect(20,52+first*(536-h)/(L.length-vis),4,h); }
  const X=CW+88, RX=1920-88;
  if(top){ if(it.cat){ const c=CATS[idx]; sp(c[1].toUpperCase(),X,92,30,Dm); const items=SETS.filter(x=>x.s===c[0]);
      items.slice(0,4).forEach((o,k)=>{ const y=180+k*92; txt(o.n,X,y,50,'',W); txt(o.act?'›':String(setVal(o)),RX,y,50,'bold',W,'right'); });
      if(items.length>4) txt('+ '+(items.length-4)+' til',X,180+4*92,40,'',Dm); }
    else { sp('INNSTILLINGER',X,92,30,Dm); txt('Trykk for å lukke',X,300,72,'bold',W); txt('Lukker også av seg selv etter 20 s',X,380,40,'',Dm); } }
  else { const c=CATS[S.set.cat]; sp(c[1].toUpperCase()+(it.back?'':'  ›  '+it.n.toUpperCase()),X,92,30,Dm); txt(idx+' / '+(L.length-1),RX,92,30,'',Dm,'right');
    if(it.back){ txt('Tilbake til kategoriene',X,320,64,'bold',W); }
    else if(it.num){ const [k,mn,mx]=it.num, v=S.set[k], n=mx-mn+1, gap=12, bw=(RX-X-gap*(n-1))/n; txt(fmtNum(k,v),X,250,190,'300',W);
      for(let j=0;j<n;j++){ const val=mn+j, x=X+j*(bw+gap), on=(v>0&&val>0&&val<=v)||(v<0&&val<0&&val>=v); g.beginPath(); g.roundRect(x,400,bw,28,6); g.fillStyle=val===0?'rgba(246,243,238,.7)':on?A:'rgba(255,255,255,.14)'; g.fill(); }
      txt(String(mn),X,470,30,'',Lo); txt(String(mx>0?'+'+mx:mx),RX,470,30,'',Lo,'right'); txt(ed?'Vri for å endre · trykk for å lagre':'Trykk for å endre',X,560,36,'',ed?A:Dm); }
    else { const v=String(setVal(it)); txt(it.act&&(v===''||v==='›')?it.n:v,X,280,v.length>12?96:150,'300',W); txt(it.act?'Trykk for å utføre':it.b?'Trykk for å slå av/på':'Trykk for neste valg',X,470,36,'',Dm); } }
  g.textBaseline='alphabetic'; }
function drawSaver(g,st){ if(window.SKJOLD&&SKJOLD.drawWide){ SKJOLD.drawWide(g,1920,640,st,new Date(),{name:devName(),last:(WL[S.wl]||{}).t?(WL[S.wl].t+' · '+WL[S.wl].s):''}); } }
function drawBar(){ const g=cvb.getContext('2d'); g.setTransform(0.5,0,0,0.5,0,0); g.fillStyle='#000'; g.fillRect(0,0,1920,640);
  { const nt=performance.now()-(S.nightT||-1e9), ND=900+((S.nightSteps||[]).length)*450+1600; if(nt<ND&&!S.rebootT){ drawNight(g,Math.min(1,nt/180,(ND-nt)/400),nt); texB.needsUpdate=true; return; } }
  { const st=S.set.clockStyle|0, prev=performance.now()-(S.clockPrevT||-1e9)<4000; if(st>=6&&!S.rebootT&&(prev||(!S.power&&S.main&&S.set.clock))){ drawSaver(g,st); texB.needsUpdate=true; return; } }
  { const nw=performance.now(); if(S.rebootT||(S.knobHoldT&&nw-S.knobHoldT>(S.holdWhat==='radio'?900:350))||(S.power&&!S.set.open&&nw-S.muteT<1600)){ drawBarSys(g,'"Helvetica Neue",Arial,sans-serif'); texB.needsUpdate=true; return; } }
  const full=S.power&&!booting()&&!S.rebootT&&!S.set.open&&!S.setup.on;
  if(S.power&&booting()&&!S.rebootT){ drawSplash(g,1920,640,0,true); texB.needsUpdate=true; return; }
  if(S.power&&S.set.open&&!S.set.page&&!S.setup.on&&!S.rebootT&&performance.now()-S.set.t<=20000){ drawBarSettings(g); texB.needsUpdate=true; return; }
  if(!full){ g.drawImage(cvt,0,0,640,480,533,0,853,640); texB.needsUpdate=true; return; }
  const F='"Helvetica Neue",Arial,sans-serif', W='#f6f3ee', Dm='rgba(246,243,238,.62)', Lo='rgba(246,243,238,.38)', n=barNow(), now=performance.now(); g.textBaseline='alphabetic'; g.textAlign='left';
  if(S.pairT||now-S.toastT<2200||now-(S.pairCancelT||-1e9)<1500){ drawBarBT(g,F); const a=screenDim(); if(a){ g.fillStyle='rgba(0,0,0,'+a+')'; g.fillRect(0,0,1920,640); } texB.needsUpdate=true; return; }
  if(bdayOn()&&!S.bdayHide){ drawBday(g,F); const a=screenDim(); if(a){ g.fillStyle='rgba(0,0,0,'+a+')'; g.fillRect(0,0,1920,640); } texB.needsUpdate=true; return; }
  { const key=S.input+'|'+S.preset+'|'+S.usb+'|'+S.aux+'|'+n.t; if(!drawBar.amb||drawBar.ambK!==key){ const sm=document.createElement('canvas'); sm.width=sm.height=24; drawArt(sm.getContext('2d'),0,0,24,n); drawBar.amb=sm; drawBar.ambK=key; }
    g.save(); g.imageSmoothingEnabled=true; g.imageSmoothingQuality='high'; g.drawImage(drawBar.amb,0,0,24,24,-200,-640,2320,1920); g.restore(); }
  g.fillStyle='rgba(0,0,0,.56)'; g.fillRect(0,0,1920,640);
  const rr=(x,y,w,h,r)=>{ g.beginPath(); g.roundRect(x,y,w,h,r); };
  const txt=(s,x,y,px,wt,c,al)=>{ g.font=(wt||'')+' '+px+'px '+F; g.fillStyle=c; g.textAlign=al||'left'; g.fillText(s,x,y); g.textAlign='left'; };
  const fitT=(s,max,px,wt,min)=>{ let p=px; g.font=wt+' '+p+'px '+F; while(g.measureText(s).width>max&&p>(min||40)){ p-=4; g.font=wt+' '+p+'px '+F; } return p; };
  const clip=(s,max)=>{ let o=s; while(g.measureText(o).width>max&&o.length>3) o=o.slice(0,-2); return o===s?s:o+'…'; };
  const art=(x,y,s,patch)=>{ const sv={p:S.preset,u:S.usb,a:S.aux}; if(patch) Object.assign(S,patch); g.save(); rr(x,y,s,s,Math.round(s*0.045)); g.clip(); drawArt(g,x,y,s,barNow()); g.restore(); S.preset=sv.p; S.usb=sv.u; S.aux=sv.a; g.textBaseline='alphabetic'; g.textAlign='left'; };
  const clock=()=>{ const d=new Date(); txt(String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0'),1864,110,'56','500',W,'right'); if(S.night){ g.fillStyle='#c9d4f5'; g.beginPath(); g.arc(1700,92,20,0,7); g.fill(); g.fillStyle='#000'; g.beginPath(); g.arc(1710,84,18,0,7); g.fill(); } };
  const volOverlay=()=>{ if(!(now-S.volT<2200||S.muted)) return false; const v=S.muted?0:volShown(), X=652, TW=1212;
    txt(S.hp?'HODETELEFON':'VOLUM',X,436,28,'bold',Dm); rr(X,470,TW-190,14,7); g.fillStyle='rgba(255,255,255,.18)'; g.fill(); rr(X,470,Math.max(14,(TW-190)*v/100),14,7); g.fillStyle=S.muted?'#777':W; g.fill();
    txt(S.muted?'DEMPET':String(v),X+TW,500,72,'bold',W,'right'); return true; };
  const srcRow=()=>{ ['AIR','AUX','RADIO','USB'].forEach((k,i)=>{ const on=i===S.input, x=652+i*160, l=k==='AIR'?(S.wl==='bt'?'BT':'AIRPLAY'):k; txt(l,x,604,26,on?'bold':'',on?W:Lo); if(on){ g.fillStyle=W; g.fillRect(x,616,g.measureText(l).width,4); } }); };
  const pill=(s,x,y,live)=>{ g.font='bold 30px '+F; const w=g.measureText(s).width; rr(x,y,w+(live?96:48),52,26); g.fillStyle='rgba(255,255,255,.16)'; g.fill(); txt(s,x+24,y+37,30,'bold',W); if(live){ g.fillStyle='rgba(255,77,77,'+(0.55+0.45*Math.sin(now/350))+')'; g.beginPath(); g.arc(x+w+58,y+26,9,0,Math.PI*2); g.fill(); } return w+(live?96:48); };
  const meter=(x,y,w,h)=>{ const N=48, bw=(w-(N-1)*6)/N; for(let i=0;i<N;i++){ const t=now/1000, lv=S.muted?0.04:Math.max(0.05,Math.min(1,0.45+0.32*Math.sin(t*5.1+i*0.55)+0.22*Math.sin(t*11.7+i*1.9)+0.12*Math.sin(t*2.3-i*0.3))*(1-Math.abs(i-N/2)/N*0.9)); const bh=Math.max(6,h*lv); rr(x+i*(bw+6),y+h-bh,bw,bh,3); g.fillStyle=i/N<lv?W:'rgba(255,255,255,.35)'; g.globalAlpha=0.35+0.65*lv; g.fill(); g.globalAlpha=1; } };
  const dim=()=>{ const a=screenDim(); if(a){ g.fillStyle='rgba(0,0,0,'+a+')'; g.fillRect(0,0,1920,640); } texB.needsUpdate=true; };

  // ---- source browser (opened by the source button, browse with the volume knob, press knob = choose) ----
  if(menuOpen()&&S.input>=1&&S.input<=3){
    const R2=S.input===2, list=R2?PRESETS:S.input===3?USBSRC:AUXSRC, cur=R2?S.preset:S.input===3?S.usb:S.aux;
    txt(R2?'VELG STASJON':S.input===3?'VELG USB-KILDE':'VELG AUX-INNGANG',56,92,30,'bold',W);
    txt('Vri volum for å bla · trykk for å velge  ·  '+list[cur][1],56,138,28,'',Dm); clock();
    const T=R2?248:300, GAP=R2?40:72, tot=list.length*T+(list.length-1)*GAP, x0=Math.max(56,(1920-tot)/2);
    list.forEach((it,i)=>{ const on=i===cur, s=on?T+24:T, x=x0+i*(T+GAP)-(on?12:0), y=on?184:196;
      if(on){ rr(x-8,y-8,s+16,s+16,20); g.fillStyle=W; g.fill(); }
      art(x,y,s,R2?{preset:i}:S.input===3?{usb:i}:{aux:i}); if(!on){ rr(x,y,s,s,12); g.fillStyle='rgba(0,0,0,.35)'; g.fill(); }
      if(R2){ rr(x+14,y+14,52,44,10); g.fillStyle='rgba(0,0,0,.6)'; g.fill(); txt(String(i+1),x+40,y+48,30,'bold',W,'center'); }
      g.font=(on?'bold ':'')+'32px '+F; txt(clip(it[0],T+30),x+s/2,y+s+56,32,on?'bold':'',on?W:Dm,'center'); });
    
    rr(56,606,1808,6,3); g.fillStyle='rgba(255,255,255,.14)'; g.fill(); const left=Math.max(0,1-(now-S.menuT)/5000); rr(56,606,1808*left,6,3); g.fillStyle=W; g.fill();
    dim(); return; }

  // ---- now playing (6a: glasspanel med kildebrikker) ----
  g.fillStyle='rgba(0,0,0,.35)'; rr(60,72,528,528,28); g.fill(); art(56,56,528);
  const PX=632, PY=56, PW=1232, PH=528, X=680, XR=1816, TW=XR-X;
  rr(PX,PY,PW,PH,36); g.fillStyle='rgba(255,255,255,.08)'; g.fill(); g.strokeStyle='rgba(255,255,255,.12)'; g.lineWidth=2; g.stroke();
  { let x=X; ['AIR','AUX','RADIO','USB'].forEach((k,i)=>{ const on=i===S.input, l=k==='AIR'?(S.wl==='bt'?'BLÅTANN':'AIRPLAY'):k, live=on&&i===2; g.font='bold 26px '+F; const w=g.measureText(l).width+48+(live?28:0);
      rr(x,96,w,52,26); g.fillStyle=on?W:'rgba(255,255,255,.08)'; g.fill(); txt(l,x+24,132,26,'bold',on?'#111':Lo);
      if(live){ g.fillStyle='rgba(229,49,43,'+(0.6+0.4*Math.sin(now/350))+')'; g.beginPath(); g.arc(x+w-30,122,8,0,7); g.fill(); } x+=w+16; }); }
  { const d=new Date(); txt(String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0'),XR,140,52,'bold',W,'right');
    if(S.night){ g.fillStyle='#c9d4f5'; g.beginPath(); g.arc(XR-180,122,18,0,7); g.fill(); g.fillStyle='#1a1424'; g.beginPath(); g.arc(XR-171,115,16,0,7); g.fill(); } }
  const head=(t,sub)=>{ fitT(t,TW,104,'bold'); g.fillStyle=W; g.fillText(t,X-4,312); g.font='44px '+F; txt(clip(sub,TW),X,372,44,'',Dm); };
  const vol6=()=>{ if(!(now-S.volT<2200||S.muted)) return false; const v=S.muted?0:volShown(), w=TW-220;
    txt(S.hp?'HODETELEFON':'VOLUM',X,466,26,'bold',Dm); rr(X,500,w,12,6); g.fillStyle='rgba(255,255,255,.18)'; g.fill(); rr(X,500,Math.max(12,w*v/100),12,6); g.fillStyle=S.muted?'#777':W; g.fill();
    txt(S.muted?'DEMPET':String(v),XR,530,72,'bold',W,'right'); return true; };
  if(S.input===2){ const p=PRESETS[S.preset], np=NOWP[S.preset]||['',''];
    head(p[0],'Nå: '+np[0]+(np[1]?' · '+np[1]:''));
    if(!vol6()){ const cw=(TW-5*16)/6; PRESETS.forEach((q,i)=>{ const on=i===S.preset, x=X+i*(cw+16); rr(x,448,cw,88,14); g.fillStyle=on?W:'rgba(255,255,255,.08)'; g.fill();
        txt(String(i+1),x+18,476,20,'',on?'#111':Lo); g.font=(on?'bold ':'')+'26px '+F; let t=q[0]; if(g.measureText(t).width>cw-36){ while(g.measureText(t+'…').width>cw-36&&t.length>3) t=t.slice(0,-1); t+='…'; } txt(t,x+18,514,26,on?'bold':'',on?'#111':W); }); }
    dim(); return; }
  if(S.input===3||S.input===1){ const U=S.input===3, it=U?USBSRC[S.usb]:AUXSRC[S.aux], list=U?USBSRC:AUXSRC, cur=U?S.usb:S.aux;
    head(it[0],it[1]);
    if(!vol6()){ g.font='bold 26px '+F; const ws=list.map(q=>g.measureText(q[0]).width+48), tot=ws.reduce((a,b)=>a+b,0)+16*(list.length-1); let x=XR-tot;
      list.forEach((q,i)=>{ const on=i===cur; rr(x,484,ws[i],52,26); g.fillStyle=on?W:'rgba(255,255,255,.08)'; g.fill(); txt(q[0],x+24,520,26,'bold',on?'#111':W); x+=ws[i]+16; });
      meter(X,456,TW-tot-40,80); }
    dim(); return; }
  head(n.t,n.s);
  if(!vol6()){ const el=((S.paused?S.pausedAt:now)-S.playT)/1000, dur=244, p=Math.min(1,(el%dur)/dur), m=t=>Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0');
    rr(X,488,TW,8,4); g.fillStyle='rgba(255,255,255,.18)'; g.fill(); rr(X,488,Math.max(8,TW*p),8,4); g.fillStyle=W; g.fill();
    txt(m(el%dur),X,540,28,'',Dm); txt('−'+m(dur-el%dur),XR,540,28,'',Dm,'right');
    if(S.paused){ g.fillStyle=W; g.fillRect(X+TW/2-14,512,10,32); g.fillRect(X+TW/2+4,512,10,32); } }
  dim(); }
function drawTFT1(){ drawTFT0(); const g=cvt.getContext('2d'); g.setTransform(2,0,0,2,0,0); if(!S.power){ if(S.main&&S.set.clock&&!S.rebootT){ drawClock(g,320,240,3); texT.needsUpdate=true; } return; } const a=screenDim(); if(a){ g.fillStyle='rgba(0,0,0,'+a+')'; g.fillRect(0,0,320,240); texT.needsUpdate=true; } }
function drawTFT0(){ const g=cvt.getContext('2d'); g.setTransform(2,0,0,2,0,0); g.fillStyle='#000'; g.fillRect(0,0,320,240);
  if(!S.power){ texT.needsUpdate=true; return; }
  if(booting()){ drawSplash(g,320,240,4.4,true); texT.needsUpdate=true; return; }
  if(S.welcome&&S.power&&!booting()&&window.SKJOLD_WELCOME){ window.SKJOLD_WELCOME.draw(g,320,240,performance.now()-bootT-BOOT); texT.needsUpdate=true; return; }
  { g.save(); g.translate(0,40); g.scale(2.5,2.5); const o=overlay(g); g.restore(); if(o){ texT.needsUpdate=true; return; } }
  const it=INPUTS[S.input], F='"Helvetica Neue",Arial,sans-serif', W='#f4f1ea', Dm='#9a968c', A='#d9a441', now=(performance.now()-T0)/1000;
  g.font='bold 11px '+F; g.textBaseline='middle'; let x=12; INPUTS.forEach((t,i)=>{const w=g.measureText(t.k).width+16; g.beginPath(); g.roundRect(x,8,w,18,9); if(i===S.input){g.fillStyle=W; g.fill(); g.fillStyle='#000';} else {g.strokeStyle='#55524c'; g.stroke(); g.fillStyle=Dm;} g.fillText(t.k,x+8,17.5); x+=w+6;});
  drawArt(g,12,36,128,it);
  g.fillStyle=W; g.font='bold 18px '+F; g.fillText(it.t,154,54); g.fillStyle=Dm; g.font='13px '+F; g.fillText(it.s,154,76); g.fillStyle=A; g.font='bold 10px '+F; g.fillText(('LYRION · '+it.n).toUpperCase(),154,98);
  for(let i=0;i<26;i++){const v=0.35+0.65*Math.abs(Math.sin(now*3.1+i*0.7)*Math.sin(now*1.7+i*0.31)), h=S.muted?2:4+v*44; g.fillStyle='hsl('+(28+i*9)+' 90% 60%)'; g.fillRect(154+i*6,164-h,4,h);}
  if(volVis()){ g.fillStyle=Dm; g.font='bold 10px '+F; g.fillText(S.muted?'MUTE':'VOL',12,222); const on=S.muted?0:Math.round(volShown()/100*32);
  for(let i=0;i<32;i++){g.fillStyle=i<on?W:'#2c2b29'; g.fillRect(44+i*6.875,216,5.4,12);} g.fillStyle=W; g.font='bold 16px '+F; g.textAlign='right'; g.fillText(S.muted?'—':String(volShown()),308,222); g.textAlign='left'; }
  texT.needsUpdate=true; }
// colour artwork for the TFT: album covers (AirPlay/BT), station logos (radio), source tiles (AUX/USB)
const ART_PAL={'Midnight City':['#ff3d7f','#7a2cff','#0b0730'],'Intro':['#f4f4f4','#d8d8d8','#101010'],'Breathe':['#3fe0d0','#2a6cff','#081a3a'],'Teardrop':['#ffb03a','#e0352b','#1a0606'],'Angel':['#c9b6ff','#5a3fd1','#0c0a24'],'Unfinished Sympathy':['#ff7a3d','#ffd23f','#2a0f05']};
const RADIO_ART={'NRK P1':['#0a5bd8','#03245e','P1'],'NRK P2':['#7b3fe4','#2a0f5c','P2'],'NRK P3':['#ff2f6e','#12b38a','P3'],'P4 Norge':['#e3141b','#5c0306','P4'],'Radio Norge':['#ff8a00','#c2185b','RN'],'NRK Klassisk':['#d6a64a','#3b2a0c','K']};
function hashS(s){ let h=7; for(const c of s) h=(h*31+c.charCodeAt(0))>>>0; return h; }
function drawArt(g,x,y,s,it){ g.save(); g.beginPath(); g.roundRect(x,y,s,s,6); g.clip(); const F='"Helvetica Neue",Arial,sans-serif';
  if(S.input===2){ const st=PRESETS[S.preset][0], R=RADIO_ART[st]||['#2a6cff','#081a3a','FM']; const gr=g.createLinearGradient(x,y,x+s,y+s); gr.addColorStop(0,R[0]); gr.addColorStop(1,R[1]); g.fillStyle=gr; g.fillRect(x,y,s,s);
    g.strokeStyle='rgba(255,255,255,.16)'; g.lineWidth=2; for(let i=1;i<=4;i++){ g.beginPath(); g.arc(x+s*0.82,y+s*0.18,i*16,0,Math.PI*2); g.stroke(); }
    g.fillStyle='#fff'; g.textAlign='center'; g.textBaseline='middle'; g.font='bold '+(R[2].length>1?44:56)+'px '+F; g.fillText(R[2],x+s/2,y+s/2+2);
    g.font='bold 9px '+F; if('letterSpacing' in g) g.letterSpacing='1.5px'; g.fillText(st.startsWith('NRK')?'NRK':st.toUpperCase(),x+s/2,y+s-16); if('letterSpacing' in g) g.letterSpacing='0px'; }
  else if(S.input===0){ const P=ART_PAL[it.t]||(()=>{ const h=hashS(it.t)%360; return ['hsl('+h+' 85% 60%)','hsl('+((h+70)%360)+' 75% 45%)','hsl('+((h+200)%360)+' 60% 10%)']; })(), hs=hashS(it.t);
    const gr=g.createLinearGradient(x,y+s,x+s,y); gr.addColorStop(0,P[2]); gr.addColorStop(0.55,P[1]); gr.addColorStop(1,P[0]); g.fillStyle=gr; g.fillRect(x,y,s,s);
    const rg=g.createRadialGradient(x+s*(0.3+(hs%5)/10),y+s*0.35,4,x+s*0.4,y+s*0.4,s*0.6); rg.addColorStop(0,P[0]); rg.addColorStop(1,'rgba(0,0,0,0)'); g.globalAlpha=0.85; g.fillStyle=rg; g.fillRect(x,y,s,s); g.globalAlpha=1;
    g.fillStyle='rgba(255,255,255,.9)'; g.beginPath(); g.arc(x+s*0.68,y+s*0.66,s*(0.12+(hs%4)/40),0,Math.PI*2); g.fill();
    g.fillStyle='rgba(0,0,0,.35)'; g.fillRect(x,y+s-26,s,26); g.fillStyle='#fff'; g.textAlign='left'; g.textBaseline='middle'; g.font='bold 9px '+F; if('letterSpacing' in g) g.letterSpacing='1px'; g.fillText(it.s.split(' · ')[0].toUpperCase().slice(0,18),x+8,y+s-13); if('letterSpacing' in g) g.letterSpacing='0px'; }
  else { const aux=S.input===1, gr=g.createLinearGradient(x,y,x+s,y+s); gr.addColorStop(0,aux?'#ffb547':'#3fa9ff'); gr.addColorStop(1,aux?'#c2410c':'#1e3a8a'); g.fillStyle=gr; g.fillRect(x,y,s,s);
    g.fillStyle='#fff'; g.textAlign='center'; g.textBaseline='middle'; g.font='bold 30px '+F; g.fillText(aux?'AUX':'USB',x+s/2,y+s/2-6); g.font='bold 11px '+F; g.fillText(aux?(AUXSRC[S.aux]||[''])[0]:(USBSRC[S.usb]||[''])[0],x+s/2,y+s/2+22); }
  g.restore(); g.textAlign='left'; g.textBaseline='middle'; }
function refresh(){}
